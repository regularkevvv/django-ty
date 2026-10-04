#!/usr/bin/env python3
"""Probe the shared corpus and runtime behavior on supported Django/Python pairs."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "compatibility/django-versions.toml"
MAP_PATH = ROOT / "compatibility/django-stubs-6.1.1.toml"
RESULTS_PATH = ROOT / "compatibility/django-versions.json"
DOCUMENT_PATH = ROOT / "docs/DJANGO-VERSIONS.md"
PYPROJECT_PATH = ROOT / "pyproject.toml"


def run(command: list[str], **kwargs: Any) -> str:
    result = subprocess.run(command, capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise RuntimeError(
            f"command failed: {' '.join(command)}\n{result.stdout}\n{result.stderr}"
        )
    return result.stdout


def load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text())


def declared_django_requirement() -> str:
    return next(
        dep.removeprefix("Django")
        for dep in load_toml(PYPROJECT_PATH)["project"]["dependencies"]
        if dep.startswith("Django")
    )


def check_declared_flags(probes: list[dict[str, Any]], requirement: str) -> None:
    bounds = dict(re.findall(r"(>=|<)\s*([0-9.]+)", requirement))
    version = lambda text: tuple(int(part) for part in text.split("."))
    for probe in probes:
        if (
            version(bounds[">="]) <= version(probe["django"]) < version(bounds["<"])
        ) != probe["declared"]:
            raise RuntimeError(
                f"matrix declaration for {probe['django']} disagrees with Django{requirement}"
            )


def ensure_wheel(args: argparse.Namespace) -> Path:
    if args.wheel:
        wheel = args.wheel.resolve()
        if not wheel.is_file():
            raise RuntimeError(f"missing wheel: {wheel}")
        return wheel
    dist = args.work_dir / "dist"
    run(
        ["bash", str(ROOT / "scripts/build-wheel.sh")],
        env={
            **os.environ,
            "DIST_DIR": str(dist),
            "CARGO_TARGET_DIR": str(args.build_dir / "django-ty-target"),
        },
    )
    return next(dist.glob("django_ty-*.whl"))


def run_probe(
    probe: dict[str, Any], args: argparse.Namespace, wheel: Path, pinned: dict[str, Any]
) -> dict[str, Any]:
    minor = ".".join(probe["django"].split(".")[:2])
    python = probe["python"]
    reference = args.work_dir / "envs" / f"reference-{minor}-py{python}"
    candidate = args.work_dir / "envs" / f"candidate-{minor}-py{python}"
    for environment in (reference, candidate):
        if not args.reuse:
            shutil.rmtree(environment, ignore_errors=True)
        if not (environment / "bin/python").is_file():
            run(["uv", "venv", "--python", python, str(environment)])
    run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(reference / "bin/python"),
            f"Django=={probe['django']}",
            f"django-stubs=={probe['django_stubs']}",
            f"django-stubs-ext=={probe['django_stubs']}",
            f"mypy=={probe['mypy']}",
        ]
    )
    run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(candidate / "bin/python"),
            f"Django=={probe['django']}",
            f"ty-extended=={pinned['conformance']['ty_extended']}",
            "types-PyYAML>=6.0.12",
            "typing-extensions>=4.11.0",
        ]
    )
    install = [
        "uv",
        "pip",
        "install",
        "--reinstall-package",
        "django-ty",
        "--python",
        str(candidate / "bin/python"),
    ]
    if not probe["declared"]:
        install.append("--no-deps")
    run([*install, str(wheel)])
    output = args.work_dir / "results" / f"{minor}-py{python}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            sys.executable,
            str(ROOT / "scripts/evaluate_differential_conformance.py"),
            "--mypy-bin",
            str(reference / "bin/mypy"),
            "--ty-bin",
            str(candidate / "bin/ty"),
            "--ty-python",
            str(candidate),
            "--probe",
            "--django-stubs-commit",
            probe["django_stubs_commit"],
            "--write",
            "--result-path",
            str(output),
        ]
    )
    result = json.loads(output.read_text())
    if (
        result["reference"]["python"] != python
        or result["candidate"]["django"] != probe["django"]
        or result["candidate"]["ty_extended"] != pinned["conformance"]["ty_extended"]
    ):
        raise RuntimeError(
            f"wrong environment for Django {probe['django']} / Python {python}"
        )
    if (
        result["scores"]["contract_matched_assertions"]
        != result["scores"]["total_assertions"]
        or result["unowned_diagnostics"].get("ty")
        or result["unparsed_output"]
    ):
        raise RuntimeError(
            f"candidate failed conformance on Django {probe['django']} / Python {python}: {result['scores']}"
        )
    result["querydict_runtime"] = json.loads(
        run(
            [
                str(candidate / "bin/python"),
                str(ROOT / "scripts/check_querydict_runtime.py"),
                str(candidate),
            ]
        )
    )
    print(
        f"Django {probe['django']} / Python {python}: {result['scores']['contract_matched_assertions']}/{result['scores']['total_assertions']} contract assertions and 7 runtime cases passed",
        file=sys.stderr,
        flush=True,
    )
    return result


def aggregate(
    matrix: dict[str, Any],
    probes: list[dict[str, Any]],
    results: list[dict[str, Any]],
    pinned: dict[str, Any],
    requirement: str,
) -> dict[str, Any]:
    feature_keys = (
        "id",
        "area",
        "cases",
        "matched",
        "percent",
        "status",
        "contract_matched",
        "contract_percent",
    )
    return {
        "schema_version": 2,
        "matrix_python": matrix["python"],
        "declared_range": requirement,
        "candidate": {
            key: pinned["conformance"][key]
            for key in ("django_ty", "ty_extended", "ty_extended_commit")
        },
        "corpus": results[0]["corpus"],
        "probes": [
            {
                "django": probe["django"],
                "declared": probe["declared"],
                "note": probe["note"],
                **{
                    key: result[key]
                    for key in (
                        "reference",
                        "candidate",
                        "scores",
                        "reference_drift",
                        "unowned_diagnostics",
                        "unparsed_output",
                        "querydict_runtime",
                    )
                },
                "features": [
                    {key: feature[key] for key in feature_keys}
                    for feature in result["features"]
                ],
            }
            for probe, result in zip(probes, results, strict=True)
        ],
    }


def render_document(results: dict[str, Any]) -> str:
    candidate = results["candidate"]
    lines = [
        "# Django Version Compatibility",
        "",
        "Generated by `scripts/probe_django_versions.py` from `compatibility/django-versions.toml`. Do not edit by hand.",
        "",
        f"Candidate: `django-ty` {candidate['django_ty']} on `ty-extended` {candidate['ty_extended']} (`{candidate['ty_extended_commit']}`).",
        f"Declared install range: `Django{results['declared_range']}`, Python `>=3.10`.",
        "",
        "Each row checks the shared corpus against the version-matched mypy/django-stubs oracle and the installed wheel. Python combinations follow [Django's compatibility table](https://docs.djangoproject.com/en/6.1/faq/install/#what-python-version-can-i-use-with-django). Seven QueryDict assignment cases are also compared independently with each installed Django runtime.",
        "",
        "The wheel serves one reviewed django-stubs 6.1.1 static tree. These results cover the listed corpus and runtime cases, not every version-specific API addition or removal.",
        "",
        "## Matrix",
        "",
        "| Django | Python | Reference oracle | In declared range | Contract parity | Oracle parity | Runtime cases | Stray diagnostics |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for probe in results["probes"]:
        scores = probe["scores"]
        reference = probe["reference"]
        stray = sum(len(items) for items in probe["unowned_diagnostics"].values())
        lines.append(
            f"| {probe['django']} | {reference['python']} | django-stubs {reference['django_stubs']} + {reference['checker']} | {'yes' if probe['declared'] else 'no'} | {scores['contract_feature_balanced_percent']:.1f}% ({scores['contract_matched_assertions']}/{scores['total_assertions']}) | {scores['feature_balanced_percent']:.1f}% ({scores['matched_assertions']}/{scores['total_assertions']}) | {len(probe['querydict_runtime'])}/7 | {stray} |"
        )
    lines += [
        "",
        "Contract parity compares the candidate with the corpus expectations. Oracle parity compares it with the version-matched reference. Older oracles may accept invalid code or reject valid code. The findings below record the exact differences; unreachable code and candidate diagnostics outside assertions fail the run.",
        "",
        "## Capability Grid",
        "",
    ]
    minors = list(
        dict.fromkeys(".".join(p["django"].split(".")[:2]) for p in results["probes"])
    )
    lines += [
        "| Capability | " + " | ".join(minors) + " |",
        "| --- |" + " ---: |" * len(minors),
    ]
    for feature in results["probes"][0]["features"]:
        cells = []
        for minor in minors:
            matching = [
                p for p in results["probes"] if p["django"].startswith(minor + ".")
            ]
            rate = min(
                next(
                    f["contract_percent"]
                    for f in p["features"]
                    if f["id"] == feature["id"]
                )
                for p in matching
            )
            cells.append(f"{rate:.1f}%")
        lines.append(f"| `{feature['id']}` | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Cells show the lowest contract score across the tested Python versions for each Django line.",
        "",
        "## Findings",
        "",
    ]
    for minor in minors:
        matching = [p for p in results["probes"] if p["django"].startswith(minor + ".")]
        lines.append(f"- **Django {minor}**: {matching[0]['note']}")
        seen = set()
        for probe in matching:
            for drift in probe["reference_drift"]:
                identity = (drift["feature"], drift["case"], drift["reference"])
                if identity in seen:
                    continue
                seen.add(identity)
                lines.append(
                    f"  - `{drift['path']}:{drift['line']}` `{drift['feature']}/{drift['case']}`: contract expects {drift['expect']}, oracle {drift['reference']}s; candidate matches the contract"
                )
            for checker, diagnostics in probe["unowned_diagnostics"].items():
                for diagnostic in diagnostics:
                    identity = (
                        checker,
                        diagnostic["path"],
                        diagnostic["line"],
                        diagnostic["code"],
                    )
                    if identity not in seen:
                        seen.add(identity)
                        lines.append(
                            f"  - {checker}: `{diagnostic['path']}:{diagnostic['line']}` `{diagnostic['code']}` outside assertions: {diagnostic['message']}"
                        )
    lines += [
        "",
        "## Reproduce",
        "",
        "```sh",
        "uv run --no-project --python 3.11 python scripts/probe_django_versions.py --write",
        "```",
        "",
        "`--check` repeats all pairs and compares the generated artifacts. `--only 5.2` previews one Django line. `--reuse` keeps environments but reinstalls the current wheel. Python patch versions and mypy compilation mode are omitted from the comparison so the same minor-version matrix is reproducible across platforms.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--work-dir", type=Path, default=Path("/tmp/django-ty-version-probes")
    )
    parser.add_argument(
        "--build-dir", type=Path, default=Path("/tmp/django-ty-build-cache")
    )
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--reuse", action="store_true")
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--jobs", type=int, default=2)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.jobs < 1 or (args.check and args.only):
        parser.error("--jobs must be positive and --check must cover the full matrix")
    matrix = load_toml(MATRIX_PATH)["matrix"]
    requirement = declared_django_requirement()
    check_declared_flags(matrix["probe"], requirement)
    probes = [
        {**probe, "python": python}
        for probe in matrix["probe"]
        for python in probe["python"]
    ]
    if args.only:
        probes = [
            probe
            for probe in probes
            if any(version in probe["django"] for version in args.only)
        ]
    if not probes:
        parser.error("no matching probes")
    pinned = load_toml(MAP_PATH)
    wheel = ensure_wheel(args)
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        results = list(
            executor.map(lambda probe: run_probe(probe, args, wheel, pinned), probes)
        )
    if args.only:
        print("Preview passed; a full run is required to update committed artifacts")
        return 0
    result = aggregate(matrix, probes, results, pinned, requirement)
    outputs = {
        RESULTS_PATH: json.dumps(result, indent=2) + "\n",
        DOCUMENT_PATH: render_document(result),
    }
    for path, content in outputs.items():
        if args.write:
            path.write_text(content)
        elif not path.is_file() or path.read_text() != content:
            raise RuntimeError(
                f"{path.relative_to(ROOT)} is out of date; rerun --write"
            )
    print(f"Django/Python compatibility matrix passed: {len(probes)} pairs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
