#!/usr/bin/env python3
"""Compare django-ty with a pinned mypy plus django-stubs reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT / "conformance"
MAP_PATH = ROOT / "compatibility" / "django-stubs-6.0.6.toml"
RESULT_PATH = ROOT / "compatibility" / "differential-conformance.json"
CHECK_PATHS = ("conformance_project", "conformance_models", "cases")
MARKER_RE = re.compile(
    r"#\s*conformance:\s*(?P<feature>[a-z0-9.-]+)/(?P<case>[a-z0-9.-]+)\s+"
    r"expect=(?P<expect>pass|fail)\s*$"
)
MYPY_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):(?P<column>\d+): error: "
    r"(?P<message>.*?)(?:  \[(?P<code>[^]]+)\])?$"
)
TY_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):(?P<column>\d+): error"
    r"\[(?P<code>[^]]+)\] (?P<message>.*)$"
)


@dataclass(frozen=True)
class Marker:
    feature: str
    case: str
    path: str
    line: int
    expect: str

    @property
    def key(self) -> tuple[str, int]:
        return self.path, self.line


@dataclass(frozen=True)
class Diagnostic:
    path: str
    line: int
    column: int
    code: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "code": self.code,
            "message": self.message,
        }


class ConformanceError(Exception):
    pass


def load_map() -> dict[str, Any]:
    with MAP_PATH.open("rb") as file:
        return tomllib.load(file)


def normalized_path(value: str, project_root: Path) -> str:
    path = Path(value)
    if path.is_absolute():
        try:
            path = path.relative_to(project_root)
        except ValueError as error:
            raise ConformanceError(
                f"diagnostic is outside the conformance project: {value}"
            ) from error
    return path.as_posix().removeprefix("./")


def collect_markers(project_root: Path) -> list[Marker]:
    markers: list[Marker] = []
    for directory in ("cases", "conformance_models"):
        for path in sorted((project_root / directory).rglob("*.py")):
            relative = path.relative_to(project_root).as_posix()
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                match = MARKER_RE.search(line)
                if match:
                    markers.append(
                        Marker(
                            feature=match["feature"],
                            case=match["case"],
                            path=relative,
                            line=line_number,
                            expect=match["expect"],
                        )
                    )

    identities: set[tuple[str, str]] = set()
    locations: set[tuple[str, int]] = set()
    for marker in markers:
        identity = marker.feature, marker.case
        if identity in identities:
            raise ConformanceError(f"duplicate case id: {marker.feature}/{marker.case}")
        if marker.key in locations:
            raise ConformanceError(f"multiple markers on {marker.path}:{marker.line}")
        identities.add(identity)
        locations.add(marker.key)
    if not markers:
        raise ConformanceError("the conformance corpus has no markers")
    return markers


def run(command: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(
        command, cwd=cwd, check=False, capture_output=True, text=True
    )
    return result.returncode, "\n".join(
        part for part in (result.stdout, result.stderr) if part
    ).strip()


def parse_diagnostics(
    output: str, checker: str, project_root: Path
) -> list[Diagnostic]:
    pattern = MYPY_RE if checker == "mypy" else TY_RE
    diagnostics: list[Diagnostic] = []
    unparsed: list[str] = []
    for line in output.splitlines():
        match = pattern.match(line)
        if match:
            diagnostics.append(
                Diagnostic(
                    path=normalized_path(match["path"], project_root),
                    line=int(match["line"]),
                    column=int(match["column"]),
                    code=match["code"] or "error",
                    message=match["message"],
                )
            )
        elif checker == "mypy" and ": note:" in line:
            continue
        elif checker == "ty" and re.fullmatch(r"Found \d+ diagnostics?", line):
            continue
        elif line.strip():
            unparsed.append(line)
    if unparsed:
        preview = "\n".join(unparsed[:10])
        raise ConformanceError(f"could not parse {checker} output:\n{preview}")
    return diagnostics


def checker_version(executable: Path) -> str:
    return_code, output = run([str(executable), "--version"], ROOT)
    if return_code != 0 or not output:
        raise ConformanceError(f"could not read version from {executable}")
    return output.splitlines()[0].strip()


def normalize_ty_checker_version(
    reported: str, expected_version: str, expected_commit: str
) -> str:
    parts = reported.split()
    version = parts[1] if len(parts) >= 2 and parts[0] == "ty" else ""
    if version != expected_version and not version.startswith(f"{expected_version}+"):
        raise ConformanceError(
            f"candidate ty executable reports {reported!r}; expected ty {expected_version}"
        )

    # Release wheels may omit VCS metadata; validate it whenever it is present.
    commit_match = re.search(r"\(([0-9a-f]{9,40})(?:\s|\))", reported)
    if commit_match and not expected_commit.startswith(commit_match.group(1)):
        raise ConformanceError(
            "candidate ty executable reports commit "
            f"{commit_match.group(1)}; expected {expected_commit}"
        )
    return f"ty {expected_version}"


def python_executable(environment: Path) -> Path:
    return environment / "bin" / "python" if environment.is_dir() else environment


def distribution_version(environment: Path, distribution: str) -> str:
    executable = python_executable(environment)
    code = (
        "import importlib.metadata as metadata; "
        f"print(metadata.version({distribution!r}))"
    )
    return_code, output = run([str(executable), "-c", code], ROOT)
    if return_code != 0 or not output:
        raise ConformanceError(
            f"could not read {distribution} version from {environment}"
        )
    return output.strip()


def require_distribution_absent(environment: Path, distribution: str) -> None:
    executable = python_executable(environment)
    code = (
        "import importlib.metadata as metadata; "
        f"name = {distribution!r}; "
        "installed = True; "
        "\ntry: metadata.version(name)"
        "\nexcept metadata.PackageNotFoundError: installed = False"
        "\nraise SystemExit(installed)"
    )
    return_code, _ = run([str(executable), "-c", code], ROOT)
    if return_code != 0:
        raise ConformanceError(f"candidate environment must not install {distribution}")


def python_version(environment: Path) -> str:
    return_code, output = run([str(python_executable(environment)), "--version"], ROOT)
    if return_code != 0 or not output.startswith("Python "):
        raise ConformanceError(f"could not read Python version from {environment}")
    return output.removeprefix("Python ").strip()


def verify_environment(
    name: str,
    environment: Path,
    expected_python: str,
    expected_distributions: dict[str, str],
) -> dict[str, str]:
    actual_python = python_version(environment)
    if not actual_python.startswith(f"{expected_python}."):
        raise ConformanceError(
            f"{name} uses Python {actual_python}; expected Python {expected_python}.x"
        )
    actual: dict[str, str] = {}
    for distribution, expected in expected_distributions.items():
        actual[distribution] = distribution_version(environment, distribution)
        if actual[distribution] != expected:
            raise ConformanceError(
                f"{name} has {distribution} {actual[distribution]}; expected {expected}"
            )
    return actual


def corpus_digest(project_root: Path) -> str:
    digest = hashlib.sha256()
    paths = sorted(project_root.rglob("*.py")) + [
        project_root / "mypy.ini",
        project_root / "pyproject.toml",
    ]
    for path in paths:
        digest.update(path.relative_to(project_root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def percentage(numerator: int | float, denominator: int | float) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def status(percent: float) -> str:
    if percent == 100.0:
        return "supported"
    if percent == 0.0:
        return "unsupported"
    return "partial"


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    compatibility_map = load_map()
    baseline = compatibility_map["baseline"]
    conformance = compatibility_map["conformance"]
    feature_rows = {
        feature["id"]: feature
        for feature in compatibility_map["feature"]
        if feature["surface"] == "dynamic"
    }
    markers = collect_markers(PROJECT_ROOT)
    marker_features = {marker.feature for marker in markers}
    missing = sorted(set(feature_rows) - marker_features)
    unknown = sorted(marker_features - set(feature_rows))
    if missing:
        raise ConformanceError(f"dynamic features without cases: {', '.join(missing)}")
    if unknown:
        raise ConformanceError(
            f"cases reference unknown features: {', '.join(unknown)}"
        )

    feature_case_counts: dict[str, int] = defaultdict(int)
    for marker in markers:
        feature_case_counts[marker.feature] += 1
    minimum_cases = conformance["minimum_cases_per_feature"]
    under_sampled = sorted(
        feature
        for feature, count in feature_case_counts.items()
        if count < minimum_cases
    )
    if under_sampled:
        raise ConformanceError(
            f"dynamic features need at least {minimum_cases} cases: {', '.join(under_sampled)}"
        )

    reference_environment = args.mypy_bin.resolve().parent.parent
    reference_versions = verify_environment(
        "reference environment",
        reference_environment,
        conformance["python"],
        {
            "Django": conformance["django"],
            "django-stubs": baseline["version"],
            "mypy": conformance["mypy"],
        },
    )
    candidate_versions = verify_environment(
        "candidate environment",
        args.ty_python,
        conformance["python"],
        {
            "Django": conformance["django"],
            "django-ty": conformance["django_ty"],
            "ty-extended": conformance["ty_extended"],
        },
    )
    for forbidden_distribution in ("django-stubs", "django-stubs-ext", "mypy"):
        require_distribution_absent(args.ty_python, forbidden_distribution)
    ty_version = normalize_ty_checker_version(
        checker_version(args.ty_bin),
        conformance["ty_extended"],
        conformance["ty_extended_commit"],
    )

    with tempfile.TemporaryDirectory(prefix="django-ty-mypy-cache-") as cache_dir:
        mypy_command = [
            str(args.mypy_bin),
            "--config-file",
            "mypy.ini",
            "--cache-dir",
            cache_dir,
            "--no-error-summary",
            *CHECK_PATHS,
        ]
        mypy_status, mypy_output = run(mypy_command, PROJECT_ROOT)
    if mypy_status not in {0, 1}:
        raise ConformanceError(
            f"mypy failed with exit code {mypy_status}:\n{mypy_output}"
        )

    ty_command = [
        str(args.ty_bin),
        "check",
        *CHECK_PATHS,
        "--project",
        ".",
        "--python",
        str(args.ty_python),
        "--output-format",
        "concise",
        "--color",
        "never",
        "--no-progress",
    ]
    ty_status, ty_output = run(ty_command, PROJECT_ROOT)
    if ty_status not in {0, 1}:
        raise ConformanceError(f"ty failed with exit code {ty_status}:\n{ty_output}")

    reference = parse_diagnostics(mypy_output, "mypy", PROJECT_ROOT)
    candidate = parse_diagnostics(ty_output, "ty", PROJECT_ROOT)
    marker_by_location = {marker.key: marker for marker in markers}
    for checker, diagnostics in (("mypy", reference), ("ty", candidate)):
        unowned = [
            diagnostic
            for diagnostic in diagnostics
            if (diagnostic.path, diagnostic.line) not in marker_by_location
        ]
        if unowned:
            rendered = "\n".join(
                f"{diagnostic.path}:{diagnostic.line}:{diagnostic.column}: {diagnostic.message}"
                for diagnostic in unowned
            )
            raise ConformanceError(
                f"{checker} emitted diagnostics outside assertion markers:\n{rendered}"
            )

    reference_by_location: dict[tuple[str, int], list[Diagnostic]] = defaultdict(list)
    candidate_by_location: dict[tuple[str, int], list[Diagnostic]] = defaultdict(list)
    for diagnostic in reference:
        reference_by_location[(diagnostic.path, diagnostic.line)].append(diagnostic)
    for diagnostic in candidate:
        candidate_by_location[(diagnostic.path, diagnostic.line)].append(diagnostic)

    baseline_drift: list[str] = []
    assertions_by_feature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for marker in markers:
        reference_rejected = bool(reference_by_location[marker.key])
        expected_rejected = marker.expect == "fail"
        if reference_rejected != expected_rejected:
            baseline_drift.append(
                f"{marker.path}:{marker.line} {marker.feature}/{marker.case}: "
                f"expected {marker.expect}, mypy {'failed' if reference_rejected else 'passed'}"
            )
        candidate_rejected = bool(candidate_by_location[marker.key])
        assertions_by_feature[marker.feature].append(
            {
                "case": marker.case,
                "path": marker.path,
                "line": marker.line,
                "reference": "reject" if reference_rejected else "accept",
                "candidate": "reject" if candidate_rejected else "accept",
                "matches": reference_rejected == candidate_rejected,
                "reference_diagnostics": [
                    diagnostic.as_dict()
                    for diagnostic in reference_by_location[marker.key]
                ],
                "candidate_diagnostics": [
                    diagnostic.as_dict()
                    for diagnostic in candidate_by_location[marker.key]
                ],
            }
        )
    if baseline_drift:
        raise ConformanceError(
            "reference outcomes do not match the corpus contract:\n"
            + "\n".join(baseline_drift)
        )

    feature_results: list[dict[str, Any]] = []
    area_rates: dict[str, list[float]] = defaultdict(list)
    matched_assertions = 0
    for feature_id, feature in feature_rows.items():
        assertions = sorted(
            assertions_by_feature[feature_id], key=lambda item: item["case"]
        )
        matched = sum(assertion["matches"] for assertion in assertions)
        matched_assertions += matched
        rate = percentage(matched, len(assertions))
        area_rates[feature["area"]].append(rate)
        feature_results.append(
            {
                "id": feature_id,
                "area": feature["area"],
                "upstream": feature["upstream"],
                "cases": len(assertions),
                "matched": matched,
                "percent": rate,
                "status": status(rate),
                "assertions": assertions,
            }
        )

    feature_balanced = round(
        sum(feature["percent"] for feature in feature_results) / len(feature_results), 1
    )
    area_results = [
        {
            "area": area,
            "features": len(rates),
            "percent": round(sum(rates) / len(rates), 1),
        }
        for area, rates in sorted(area_rates.items())
    ]
    return {
        "schema_version": 1,
        "reference": {
            "checker": checker_version(args.mypy_bin),
            "django_stubs": reference_versions["django-stubs"],
            "django_stubs_commit": baseline["commit"],
            "django": reference_versions["Django"],
            "python": conformance["python"],
        },
        "candidate": {
            "checker": ty_version,
            "django_ty": candidate_versions["django-ty"],
            "django": candidate_versions["Django"],
            "ty_extended": candidate_versions["ty-extended"],
            "ty_extended_commit": conformance["ty_extended_commit"],
        },
        "corpus": {
            "sha256": corpus_digest(PROJECT_ROOT),
            "features": len(feature_results),
            "assertions": len(markers),
        },
        "scores": {
            "feature_balanced_percent": feature_balanced,
            "assertion_conformance_percent": percentage(
                matched_assertions, len(markers)
            ),
            "matched_assertions": matched_assertions,
            "total_assertions": len(markers),
        },
        "areas": area_results,
        "features": feature_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mypy-bin", type=Path, required=True)
    parser.add_argument("--ty-bin", type=Path, required=True)
    parser.add_argument("--ty-python", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write", action="store_true", help="write the checked-in result"
    )
    mode.add_argument(
        "--check", action="store_true", help="verify the checked-in result"
    )
    args = parser.parse_args()

    try:
        result = evaluate(args)
    except ConformanceError as error:
        print(f"Differential conformance failed:\n{error}", file=sys.stderr)
        return 1

    rendered = json.dumps(result, indent=2, sort_keys=False) + "\n"
    if args.write:
        RESULT_PATH.write_text(rendered, encoding="utf-8")
    elif (
        not RESULT_PATH.is_file() or RESULT_PATH.read_text(encoding="utf-8") != rendered
    ):
        print(
            "Differential conformance result is out of date; rerun the pinned suite with --write.",
            file=sys.stderr,
        )
        return 1

    scores = result["scores"]
    print(
        "Differential conformance passed: "
        f"{scores['feature_balanced_percent']:.1f}% feature-balanced, "
        f"{scores['assertion_conformance_percent']:.1f}% assertions"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
