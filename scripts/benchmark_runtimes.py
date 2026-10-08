"""Benchmark both backends in one installed environment, with generated stress cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from .runtime_config import checker_options
except ImportError:
    from runtime_config import checker_options

PATHS = [
    "accounts",
    "library",
    "commerce",
    "auditlog",
    "typechecks/positive.py",
    "typechecks/static_api.py",
]


def stress_source(models: int, fields: int, queries: int, relations: str) -> str:
    lines = ["from django.db import models", "from typing import assert_type", ""]
    for index in range(models):
        lines += [f"class Model{index}(models.Model):"]
        lines += [
            f"    field{field} = models.CharField(max_length=100)"
            for field in range(fields)
        ]
        lines += ["    amount = models.IntegerField()"]
        if index and relations != "none":
            target = f"Model{index - 1}" if relations == "chain" else "Model0"
            related = "" if relations == "chain" else ', related_name="+"'
            lines += [
                f'    parent = models.ForeignKey("{target}", on_delete=models.CASCADE{related})'
            ]
        body = [f"obj{index} = Model{index}()", f"assert_type(obj{index}.id, None)"]
        body += [f"obj{index}.save()", f"assert_type(obj{index}.id, int)"]
        for query in range(queries):
            body += [
                f"loaded{index}_{query} = Model{index}.objects.get(pk={query + 1})",
                f"assert_type(loaded{index}_{query}.id, int)",
                f'Model{index}.objects.filter(amount__gte={query}).values("field0", "amount")',
            ]
        body += [
            f"alias{index} = obj{index}",
            f"alias{index}.delete()",
            f"assert_type(obj{index}.pk, None)",
        ]
        lines += ["", f"def exercise_model{index}() -> None:"]
        lines += ["    " + line for line in body]
        lines += [""]
    return "\n".join(lines)


def measure(
    command: list[str], project: Path, timeout: float, env: dict[str, str] | None = None
) -> dict:
    # wait4 reports this child's peak RSS, rather than a cumulative high-water mark
    # from earlier runs. Redirect output to a file so a full pipe cannot deadlock.
    with tempfile.TemporaryFile() as output:
        start = time.perf_counter()
        child = subprocess.Popen(
            command,
            cwd=project,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env,
        )
        timed_out = False
        while True:
            pid, status, usage = os.wait4(child.pid, os.WNOHANG)
            if pid:
                break
            if time.perf_counter() - start >= timeout:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                _, status, usage = os.wait4(child.pid, 0)
                timed_out = True
                break
            time.sleep(0.01)
        elapsed = time.perf_counter() - start
        child.returncode = os.waitstatus_to_exitcode(status)
        output.seek(0)
        text = output.read().decode(errors="replace")
    rss_bytes = usage.ru_maxrss * (1 if sys.platform == "darwin" else 1024)
    return {
        "seconds": elapsed,
        "cpu_seconds": usage.ru_utime + usage.ru_stime,
        "peak_rss_bytes": rss_bytes,
        "exit_code": child.returncode,
        "timed_out": timed_out,
        "output": text.strip(),
    }


def cache_counts(output: str) -> dict[str, int]:
    """Read the host's per-module counters; timings alone cannot prove a cache hit."""
    events = [
        line for line in output.splitlines() if "Loaded WASM plugin module" in line
    ]
    return {
        key: sum(
            int(value)
            for line in events
            for value in re.findall(rf"\b{key}=(\d+)", line)
        )
        for key in ("cache_hits", "cache_misses")
    }


def check_cache_mode(mode: str, sample: dict) -> None:
    counts = cache_counts(sample["output"])
    sample.update(counts)
    if mode == "wasm-cold" and counts["cache_misses"] < 1:
        raise RuntimeError(f"Cold WASM run did not confirm compilation: {sample}")
    if mode == "wasm-cached" and (
        counts["cache_hits"] < 1 or counts["cache_misses"] != 0
    ):
        raise RuntimeError(
            f"Cached WASM run did not confirm native-code reuse: {sample}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project",
        type=Path,
        required=True,
        help="Installed wheel E2E directory containing .venv",
    )
    parser.add_argument("--runs", type=int, default=7)
    parser.add_argument(
        "--ty-bin", type=Path, help="Use an experimental checker binary"
    )
    parser.add_argument(
        "--wasm-cache",
        action="store_true",
        help="Compare empty WASM cache, verified compiled-cache hits and Monty; requires a cache-enabled checker",
    )
    parser.add_argument("--models", type=int, nargs="+", default=[0, 5, 25])
    parser.add_argument("--fields", type=int, default=8)
    parser.add_argument("--queries", type=int, default=3)
    parser.add_argument(
        "--relations",
        choices=("shallow", "chain", "none"),
        default="shallow",
        help="Chain includes reverse relations and stresses recursive type graphs",
    )
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Keep failure evidence and return success during limit exploration",
    )
    args = parser.parse_args()
    if (
        args.runs < 1
        or args.fields < 1
        or args.queries < 1
        or min(args.models) < 0
        or args.timeout <= 0
    ):
        parser.error(
            "runs, fields, queries and timeout must be positive; models must be nonnegative"
        )
    if not hasattr(os, "wait4"):
        parser.error("peak RSS measurement requires macOS or Linux")
    project = args.project.resolve()
    environment = project / ".venv"
    checker = (args.ty_bin or environment / "bin/ty").resolve()
    if not checker.is_file():
        parser.error(f"checker does not exist: {checker}")
    code = """import hashlib, json, sys
from importlib import metadata
from pathlib import Path
import django_ty
root = Path(django_ty.__file__).parent
files = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}
print(json.dumps({"python": sys.version, "python_minor": f"{sys.version_info.major}.{sys.version_info.minor}", "Django": metadata.version("Django"), "ty-extended": metadata.version("ty-extended"), "django-ty": metadata.version("django-ty"), "package_payload_sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(), "artifact_sha256": {name: files[name] for name in ("django_ty.wasm", "monty.py", "ty-plugin.json", "ty-plugin-monty.json")}}))"""
    versions = json.loads(
        subprocess.check_output(
            [str(environment / "bin/python"), "-c", code], text=True
        )
    )
    options = {
        runtime: checker_options(
            environment, runtime, settings_module="config.settings"
        )
        for runtime in ("wasm", "monty")
    }
    result = {
        "method": {
            "measured_at": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "logical_cpus": os.cpu_count(),
            "ty_max_parallelism": os.environ.get("TY_MAX_PARALLELISM"),
            "runs": args.runs,
            "order": "rotating backend order; fresh checker processes; shared installed wheel and environment; OS caches uncontrolled",
            "wasm_cache": "separate empty caches per cold sample; one primed cache for cached samples; verified host counters"
            if args.wasm_cache
            else "not controlled",
            "memory": "peak RSS of checker process, including embedded plugin runtime; not incremental plugin memory",
            "relations": args.relations,
            "fields_per_model": args.fields,
            "queries_per_model": args.queries,
            "timeout_seconds": args.timeout,
        },
        "environment": versions,
        "checker": {
            "path": str(checker),
            "sha256": hashlib.sha256(checker.read_bytes()).hexdigest(),
            "version": subprocess.check_output(
                [str(checker), "--version"], text=True
            ).strip(),
        },
        "workloads": [],
    }
    failed = False
    with tempfile.TemporaryDirectory(prefix="django-ty-benchmark-") as temporary:
        fixture = Path(temporary).resolve()
        for name in [
            "accounts",
            "library",
            "commerce",
            "auditlog",
            "typechecks",
            "config",
        ]:
            shutil.copytree(
                project / name,
                fixture / name,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        shutil.copyfile(project / "pyproject.toml", fixture / "pyproject.toml")
        settings = fixture / "config/settings.py"
        settings.write_text(
            settings.read_text()
            + '\nINSTALLED_APPS = [*INSTALLED_APPS, "benchmark_app"]\n'
        )
        app = fixture / "benchmark_app"
        app.mkdir()
        (app / "__init__.py").write_text("")
        modes = (
            ["wasm-cold", "wasm-cached", "monty"]
            if args.wasm_cache
            else ["wasm", "monty"]
        )
        cached_directory = fixture / "compiled-cache"
        primed = False
        for models in args.models:
            (app / "models.py").write_text(
                stress_source(models, args.fields, args.queries, args.relations)
            )
            sources = {
                str(p.relative_to(fixture)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(fixture.rglob("*.py"))
            }
            workload = {
                "models": models,
                "source_hashes": sources,
                "runtimes": {mode: {"samples": []} for mode in modes},
            }
            paths = PATHS + (["benchmark_app"] if models else [])
            for iteration in range(args.runs):
                offset = iteration % len(modes)
                for mode in modes[offset:] + modes[:offset]:
                    runtime = "monty" if mode == "monty" else "wasm"
                    command = [
                        str(checker),
                        "check",
                        *paths,
                        "--project",
                        str(fixture),
                        "--python",
                        str(environment),
                        "--python-version",
                        versions["python_minor"],
                        "--color",
                        "never",
                        "--no-progress",
                        "--error-on-warning",
                        *options[runtime],
                    ]
                    env = None
                    if args.wasm_cache:
                        env = {**os.environ, "TY_LOG": "ty_plugin_host::wasm=debug"}
                        cache_directory = (
                            cached_directory
                            if mode == "wasm-cached"
                            else fixture / f"cache-{mode}-{models}-{iteration}"
                        )
                        env["XDG_CACHE_HOME"] = str(cache_directory)
                        if mode == "wasm-cached" and not primed:
                            prime = measure(command, fixture, args.timeout, env)
                            if prime["exit_code"] != 0:
                                raise RuntimeError(f"Cache priming failed: {prime}")
                            check_cache_mode("wasm-cold", prime)
                            result["cache_priming"] = prime
                            primed = True
                    sample = measure(command, fixture, args.timeout, env)
                    if (
                        args.wasm_cache
                        and runtime == "wasm"
                        and sample["exit_code"] == 0
                    ):
                        check_cache_mode(mode, sample)
                    workload["runtimes"][mode]["samples"].append(sample)
                    failed |= sample["exit_code"] != 0
                    print(
                        f"{models} models / {mode}: {sample['seconds']:.3f}s, {sample['peak_rss_bytes'] / 1048576:.1f} MiB, exit {sample['exit_code']}",
                        file=sys.stderr,
                        flush=True,
                    )
            for stats in workload["runtimes"].values():
                samples = stats["samples"]
                stats["successful_runs"] = sum(s["exit_code"] == 0 for s in samples)
                for key in ("seconds", "cpu_seconds", "peak_rss_bytes"):
                    stats[f"median_{key}"] = statistics.median(s[key] for s in samples)
            workload["all_runs_passed"] = all(
                stats["successful_runs"] == args.runs
                for stats in workload["runtimes"].values()
            )
            if workload["all_runs_passed"]:
                for mode in modes:
                    if mode != "monty":
                        workload[mode.replace("-", "_") + "_over_monty_wall_time"] = (
                            workload["runtimes"][mode]["median_seconds"]
                            / workload["runtimes"]["monty"]["median_seconds"]
                        )
            result["workloads"].append(workload)
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")
    return int(failed and not args.allow_failures)


if __name__ == "__main__":
    raise SystemExit(main())
