#!/usr/bin/env python3
"""Probe django-ty conformance across Django versions and render the matrix.

Each matrix row in compatibility/django-versions.toml spins up two
environments: a reference oracle (mypy plus the django-stubs release paired
with that Django line) and the candidate (the django-ty wheel on ty-extended,
which always evaluates the vendored django-stubs 6.1.1 static tree). The
shared differential conformance corpus then runs under both checkers and the
accept/reject outcomes are compared assertion by assertion.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "compatibility" / "django-versions.toml"
RESULTS_PATH = ROOT / "compatibility" / "django-versions.json"
DOCUMENT_PATH = ROOT / "docs" / "DJANGO-VERSIONS.md"
MAP_PATH = ROOT / "compatibility" / "django-stubs-6.1.1.toml"
PYPROJECT_PATH = ROOT / "pyproject.toml"
EVALUATOR = ROOT / "scripts" / "evaluate_differential_conformance.py"
DEFAULT_WORK_DIR = Path("/tmp/django-ty-version-probes")
DEFAULT_BUILD_DIR = Path("/tmp/django-ty-build-cache")


def run(command: list[str], **kwargs: Any) -> str:
    result = subprocess.run(
        command, check=False, capture_output=True, text=True, **kwargs
    )
    if result.returncode != 0:
        output = "\n".join(
            part for part in (result.stdout, result.stderr) if part
        ).strip()
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{output}"
        )
    return result.stdout


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as file:
        return tomllib.load(file)


def declared_django_requirement() -> str:
    for dependency in load_toml(PYPROJECT_PATH)["project"]["dependencies"]:
        if dependency.startswith("Django"):
            return dependency.removeprefix("Django")
    raise RuntimeError("pyproject.toml is missing the Django dependency")


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def check_declared_flags(probes: list[dict[str, Any]], requirement: str) -> None:
    bounds = dict(
        re.findall(r"(>=|<)\s*([0-9.]+)", requirement)
    )
    lower = version_tuple(bounds[">="])
    upper = version_tuple(bounds["<"])
    for probe in probes:
        version = version_tuple(probe["django"])
        in_range = version >= lower and version < upper
        if in_range != probe["declared"]:
            raise RuntimeError(
                f"matrix row {probe['django']} declares {probe['declared']} but "
                f"{'satisfies' if in_range else 'does not satisfy'} Django{requirement}"
            )


def ensure_wheel(args: argparse.Namespace) -> Path:
    if args.wheel:
        wheel = Path(args.wheel).resolve()
        if not wheel.is_file():
            raise RuntimeError(f"--wheel does not exist: {wheel}")
        return wheel
    dist_dir = args.work_dir / "dist"
    if args.reuse and dist_dir.is_dir():
        wheels = sorted(dist_dir.glob("django_ty-*.whl"))
        if wheels:
            return wheels[-1]
    dist_dir.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "DIST_DIR": str(dist_dir),
        "CARGO_TARGET_DIR": str(args.build_dir / "django-ty-target"),
    }
    run(["bash", str(ROOT / "scripts" / "build-wheel.sh")], env=env)
    wheels = sorted(dist_dir.glob("django_ty-*.whl"))
    if not wheels:
        raise RuntimeError("build-wheel.sh produced no wheel")
    return wheels[-1]


def install_reference(probe: dict[str, Any], environment: Path, python: str) -> None:
    run(["uv", "venv", "--python", python, str(environment)])
    requirements = [
        f"Django=={probe['django']}",
        f"django-stubs[compatible-mypy]=={probe['django_stubs']}",
        f"django-stubs-ext=={probe['django_stubs']}",
    ]
    if probe.get("mypy"):
        requirements.append(f"mypy=={probe['mypy']}")
    run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(environment / "bin" / "python"),
            *requirements,
        ]
    )


def install_candidate(
    probe: dict[str, Any],
    environment: Path,
    python: str,
    ty_extended: str,
    wheel: Path,
) -> None:
    interpreter = environment / "bin" / "python"
    run(["uv", "venv", "--python", python, str(environment)])
    run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(interpreter),
            f"Django=={probe['django']}",
            f"ty-extended=={ty_extended}",
            "types-PyYAML>=6.0.12",
            "typing-extensions>=4.11.0",
        ]
    )
    install = ["uv", "pip", "install", "--python", str(interpreter)]
    if not probe["declared"]:
        install.append("--no-deps")
    run([*install, str(wheel)])


def run_probe(
    probe: dict[str, Any],
    work_dir: Path,
    wheel: Path,
    python: str,
    ty_extended: str,
    reuse: bool,
) -> dict[str, Any]:
    minor = ".".join(probe["django"].split(".")[:2])
    reference = work_dir / "envs" / f"reference-{minor}"
    candidate = work_dir / "envs" / f"candidate-{minor}"
    if not reuse:
        shutil.rmtree(reference, ignore_errors=True)
        shutil.rmtree(candidate, ignore_errors=True)
    if not (reuse and (reference / "bin" / "mypy").is_file()):
        install_reference(probe, reference, python)
    if not (reuse and (candidate / "bin" / "ty").is_file()):
        install_candidate(probe, candidate, python, ty_extended, wheel)

    result_path = work_dir / "results" / f"probe-{minor}.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            sys.executable,
            str(EVALUATOR),
            "--mypy-bin",
            str(reference / "bin" / "mypy"),
            "--ty-bin",
            str(candidate / "bin" / "ty"),
            "--ty-python",
            str(candidate),
            "--probe",
            "--django-stubs-commit",
            probe["django_stubs_commit"],
            "--write",
            "--result-path",
            str(result_path),
        ]
    )
    return json.loads(result_path.read_text(encoding="utf-8"))


def slim_feature(feature: dict[str, Any]) -> dict[str, Any]:
    keys = ("id", "area", "cases", "matched", "percent", "status",
            "contract_matched", "contract_percent")
    return {key: feature[key] for key in keys if key in feature}


def render_document(results: dict[str, Any]) -> str:
    probes = results["probes"]
    columns = [".".join(probe["django"].split(".")[:2]) for probe in probes]
    candidate = results["candidate"]
    lines = [
        "# Django Version Compatibility",
        "",
        "Generated by `scripts/probe_django_versions.py` from `compatibility/django-versions.toml`. Do not edit by hand.",
        "",
        f"Candidate: `django-ty` {candidate['django_ty']} on `ty-extended` {candidate['ty_extended']} (`{candidate['ty_extended_commit']}`).",
        f"Declared install range: `Django{results['declared_range']}`, Python `>=3.10` (probes run on {results['matrix_python']}.x).",
        "",
        "Each row runs the differential conformance corpus "
        f"({results['corpus']['features']} capabilities, {results['corpus']['assertions']} assertions) twice: "
        "once with the version-appropriate reference oracle (mypy plus the django-stubs release paired with that Django line) "
        "and once with the candidate, which evaluates against the vendored django-stubs 6.1.1 static tree packaged in the wheel regardless of the installed Django version.",
        "",
        "## Matrix",
        "",
        "| Django | Reference oracle | Python | In declared range | Contract parity | Oracle parity | Reference drift | Stray diagnostics |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for probe, minor in zip(probes, columns):
        reference = probe["reference"]
        scores = probe["scores"]
        drift = len(probe["reference_drift"])
        strays = sum(
            len(items) for items in probe["unowned_diagnostics"].values()
        )
        declared = "yes" if probe["declared"] else "no"
        lines.append(
            f"| {probe['django']} | django-stubs {reference['django_stubs']} + {reference['checker']} "
            f"| {reference['python']} | {declared} "
            f"| {scores['contract_feature_balanced_percent']:.1f}% ({scores['contract_matched_assertions']}/{scores['total_assertions']}) "
            f"| {scores['feature_balanced_percent']:.1f}% ({scores['matched_assertions']}/{scores['total_assertions']}) "
            f"| {drift} | {strays} |"
        )
    lines.extend(
        [
            "",
            "**Contract parity** measures the candidate against the corpus contract (the accept/reject "
            "outcome each assertion declares). **Oracle parity** measures the candidate against the "
            "version-matched mypy + django-stubs oracle on the same corpus. They diverge only on "
            "*reference drift*: cases where the oracle itself disagrees with the corpus contract on "
            "that Django version, for example validations that older django-stubs releases did not "
            "perform yet (the candidate still rejects them) or stub semantics that changed upstream "
            "(see Findings). Stray diagnostics counts checker errors outside assertion markers.",
            "",
            "## Capability Grid",
            "",
            "| Capability | " + " | ".join(columns) + " |",
            "| --- |" + " ---: |" * len(columns),
        ]
    )
    feature_ids = [feature["id"] for feature in probes[-1]["features"]]
    for feature_id in feature_ids:
        cells = []
        for probe in probes:
            feature = next(
                item for item in probe["features"] if item["id"] == feature_id
            )
            cells.append(f"{feature['contract_percent']:.1f}%")
        lines.append(f"| `{feature_id}` | " + " | ".join(cells) + " |")
    lines.extend(
        [
            "",
            "Cells show contract parity per capability; oracle-only differences appear under Findings.",
            "",
            "## Findings",
            "",
        ]
    )
    for probe, minor in zip(probes, columns):
        lines.append(f"- **Django {minor}**: {probe['note']}")
        for drift in probe["reference_drift"]:
            if drift["expect"] == "fail":
                direction = (
                    "the oracle does not reject it (the validation was added "
                    "to django-stubs later); the candidate still rejects it"
                )
            else:
                direction = (
                    "the oracle rejects it; the candidate accepts it per the contract"
                )
            lines.append(
                f"  - `{drift['path']}:{drift['line']}` `{drift['feature']}/{drift['case']}`: "
                f"corpus expects {drift['expect']}, {direction}"
            )
        for checker, items in probe["unowned_diagnostics"].items():
            lines.append(
                f"  - {checker} emitted {len(items)} diagnostic(s) outside assertion markers"
            )
        for checker, items in probe.get("unparsed_output", {}).items():
            lines.append(f"  - {checker} emitted {len(items)} unparsed line(s)")
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```sh",
            "uv run --no-project --python 3.11 python scripts/probe_django_versions.py --write",
            "```",
            "",
            "Rebuilds the wheel, provisions per-version oracle and candidate environments under the work directory, "
            "runs the corpus under both checkers, and rewrites `compatibility/django-versions.json` and this document. "
            "`--check` repeats the probes and fails if the committed artifacts differ; `--only 5.2` limits a run to matching rows.",
            "",
        ]
    )
    return "\n".join(lines)


def aggregate(
    matrix: dict[str, Any],
    probes: list[dict[str, Any]],
    probe_results: list[dict[str, Any]],
    pinned: dict[str, Any],
    declared_range: str,
) -> dict[str, Any]:
    conformance = pinned["conformance"]
    return {
        "schema_version": 1,
        "matrix_python": matrix["python"],
        "declared_range": declared_range,
        "candidate": {
            "django_ty": conformance["django_ty"],
            "ty_extended": conformance["ty_extended"],
            "ty_extended_commit": conformance["ty_extended_commit"],
        },
        "corpus": probe_results[0]["corpus"],
        "probes": [
            {
                "django": probe["django"],
                "declared": probe["declared"],
                "note": probe["note"],
                "reference": result["reference"],
                "candidate": result["candidate"],
                "scores": result["scores"],
                "features": [slim_feature(f) for f in result["features"]],
                "reference_drift": result.get("reference_drift", []),
                "unowned_diagnostics": result.get("unowned_diagnostics", {}),
                "unparsed_output": result.get("unparsed_output", {}),
            }
            for probe, result in zip(probes, probe_results)
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--work-dir", type=Path, default=DEFAULT_WORK_DIR, help="probe scratch root"
    )
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=DEFAULT_BUILD_DIR,
        help="cargo build cache root",
    )
    parser.add_argument("--wheel", help="reuse a prebuilt django-ty wheel")
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="reuse environments and a wheel already in the work directory",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="limit probes to Django versions containing the substring",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write committed artifacts")
    mode.add_argument("--check", action="store_true", help="verify committed artifacts")
    args = parser.parse_args()

    if args.check and args.only:
        parser.error("--check covers the full matrix; drop --only")

    matrix = load_toml(MATRIX_PATH)["matrix"]
    probes = matrix["probe"]
    declared_range = declared_django_requirement()
    check_declared_flags(probes, declared_range)
    if args.only:
        probes = [
            probe
            for probe in probes
            if any(only in probe["django"] for only in args.only)
        ]
        if not probes:
            print("no matrix rows match --only", file=sys.stderr)
            return 2
    pinned = load_toml(MAP_PATH)
    ty_extended = pinned["conformance"]["ty_extended"]

    wheel = ensure_wheel(args)
    print(f"wheel: {wheel}", file=sys.stderr)
    probe_results = []
    for probe in probes:
        minor = ".".join(probe["django"].split(".")[:2])
        print(f"probing Django {probe['django']} ...", file=sys.stderr)
        probe_results.append(
            run_probe(
                probe,
                args.work_dir,
                wheel,
                matrix["python"],
                ty_extended,
                args.reuse,
            )
        )
        scores = probe_results[-1]["scores"]
        print(
            f"  {minor}: {scores['feature_balanced_percent']:.1f}% feature-balanced, "
            f"{scores['matched_assertions']}/{scores['total_assertions']} assertions",
            file=sys.stderr,
        )

    if args.only:
        print("--only is a preview; committed artifacts need a full run", file=sys.stderr)
        return 0

    rendered_results = aggregate(matrix, probes, probe_results, pinned, declared_range)
    rendered = json.dumps(rendered_results, indent=2, sort_keys=False) + "\n"
    document = render_document(rendered_results)
    if args.write:
        RESULTS_PATH.write_text(rendered, encoding="utf-8")
        DOCUMENT_PATH.write_text(document, encoding="utf-8")
        print(f"wrote {RESULTS_PATH.relative_to(ROOT)} and {DOCUMENT_PATH.relative_to(ROOT)}")
        return 0
    errors = []
    if not RESULTS_PATH.is_file() or RESULTS_PATH.read_text(encoding="utf-8") != rendered:
        errors.append("compatibility/django-versions.json is out of date")
    if not DOCUMENT_PATH.is_file() or DOCUMENT_PATH.read_text(encoding="utf-8") != document:
        errors.append("docs/DJANGO-VERSIONS.md is out of date")
    if errors:
        for error in errors:
            print(f"- {error}; rerun scripts/probe_django_versions.py --write", file=sys.stderr)
        return 1
    print("Django version compatibility matrix passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
