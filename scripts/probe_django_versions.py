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

    def version(text: str) -> tuple[int, ...]:
        return tuple(int(part) for part in text.split("."))

    for probe in probes:
        if (
            version(bounds[">="]) <= version(probe["django"]) < version(bounds["<"])
        ) != probe["declared"]:
            raise RuntimeError(
                f"matrix declaration for {probe['django']} disagrees with Django{requirement}"
            )


def check_reference_support(
    probes: list[dict[str, Any]], support: dict[str, Any]
) -> None:
    def version(text: str) -> tuple[int, ...]:
        return tuple(int(part) for part in text.split("."))

    for probe in probes:
        minor = ".".join(probe["django"].split(".")[:2])
        declared = support["reference"].get(probe["django_stubs"])
        if declared is None or probe["django_stubs_commit"] != declared["commit"]:
            raise RuntimeError("unreviewed comparator release or source commit")
        for python in probe["python"]:
            if python not in support["django_python"].get(minor, []):
                raise RuntimeError(
                    f"unsupported Django/Python pair: {probe['django']} / {python}"
                )
            if python not in declared["python"]:
                raise RuntimeError(
                    f"unsupported comparator Python version: {probe['django_stubs']} / {python}"
                )
        if version(probe["mypy"]) < version(declared["mypy_min"]) or (
            declared.get("mypy_max_exclusive")
            and version(probe["mypy"]) >= version(declared["mypy_max_exclusive"])
        ):
            raise RuntimeError(
                f"unsupported mypy/comparator pair: {probe['mypy']} / {probe['django_stubs']}"
            )
        if minor not in declared["django_full"] + declared["django_partial"]:
            raise RuntimeError(
                "comparator does not declare support for this Django line"
            )


def ensure_wheel(args: argparse.Namespace) -> Path:
    if args.wheel or os.environ.get("DJANGO_TY_WHEEL"):
        wheel = Path(args.wheel or os.environ["DJANGO_TY_WHEEL"]).resolve()
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
    support = load_toml(ROOT / "compatibility/reference-support.toml")["reference"][
        probe["django_stubs"]
    ]
    result["reference"]["django_support"] = (
        "full" if minor in support["django_full"] else "partial"
    )
    result["reference"]["support_source"] = support["source"]
    if (
        result["reference"]["python"] != python
        or result["reference"]["django"] != probe["django"]
        or result["reference"]["django_stubs"] != probe["django_stubs"]
        or result["reference"]["checker"] != f"mypy {probe['mypy']}"
        or result["candidate"]["django_ty"] != pinned["conformance"]["django_ty"]
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
        f"Django {probe['django']} / Python {python}: {result['scores']['contract_matched_assertions']}/{result['scores']['total_assertions']} contract assertions and independent Django runtime proofs passed",
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
    if not results or len(results) != len(probes):
        raise RuntimeError("each matrix pair must have a completed result")
    if any(result["corpus"] != results[0]["corpus"] for result in results[1:]):
        raise RuntimeError(
            "matrix results use different corpus or runtime proof revisions"
        )
    if any(result["authority"] != results[0]["authority"] for result in results[1:]):
        raise RuntimeError("matrix results use different semantic authorities")
    feature_keys = (
        "id",
        "area",
        "cases",
        "matched",
        "percent",
        "status",
        "documentation",
        "contract_matched",
        "contract_percent",
    )
    return {
        "schema_version": 3,
        "authority": results[0]["authority"],
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
                        "django_runtime",
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
        "Each row checks the installed wheel against expectations reviewed from Django's official documentation. The mypy/django-stubs run uses reviewed supported combinations as a comparison, and every reviewed disagreement must have a successful independent Django runtime proof. Python combinations follow [Django's compatibility table](https://docs.djangoproject.com/en/6.1/faq/install/#what-python-version-can-i-use-with-django). Nine QueryDict assignment cases are also compared independently with each installed Django runtime.",
        "",
        "The wheel serves one reviewed django-stubs 6.1.1 static tree. These results cover the listed corpus and runtime cases, not every version-specific API addition or removal.",
        "",
        "## Matrix",
        "",
        "| Django | Python | Mypy comparison | In declared range | Contract parity | Mypy agreement | Django runtime proofs | Stray diagnostics |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for probe in results["probes"]:
        scores = probe["scores"]
        reference = probe["reference"]
        stray = sum(len(items) for items in probe["unowned_diagnostics"].values())
        lines.append(
            f"| {probe['django']} | {reference['python']} | django-stubs {reference['django_stubs']} + {reference['checker']} ({reference['django_support']} Django support) | {'yes' if probe['declared'] else 'no'} | {scores['contract_feature_balanced_percent']:.1f}% ({scores['contract_matched_assertions']}/{scores['total_assertions']}) | {scores['feature_balanced_percent']:.1f}% ({scores['matched_assertions']}/{scores['total_assertions']}) | {len(probe['django_runtime']['cases'])} + {len(probe['querydict_runtime'])} QueryDict | {stray} |"
        )
    lines += [
        "",
        "Contract parity measures agreement with the documented expectations. Mypy agreement measures checker-to-checker similarity. Differences can reflect deliberate typing policies, inference gaps, value-content limits, or validation defects. Partial support is identified according to the pinned upstream release README. The findings below link each reviewed difference to version-specific official documentation and an executed runtime proof. New unexplained differences, missing proofs, unreachable assertions, and candidate diagnostics outside assertions fail the run.",
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
                    f"  - `{drift['path']}:{drift['line']}` `{drift['feature']}/{drift['case']}`: contract expects {drift['expect']}, mypy {drift['reference']}s ({drift['classification']}); [official Django documentation]({drift['documentation']}), runtime proof `{drift['runtime_proof']}`"
                    + (
                        f", [Django source]({drift['django_source']})"
                        if "django_source" in drift
                        else ""
                    )
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
    check_reference_support(
        matrix["probe"], load_toml(ROOT / "compatibility/reference-support.toml")
    )
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
