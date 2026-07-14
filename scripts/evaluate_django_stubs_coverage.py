#!/usr/bin/env python3
"""Verify django-ty's vendored Django static API and semantic coverage map."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "compatibility" / "django-stubs-6.0.6.toml"
DOCUMENT_PATH = ROOT / "docs" / "DJANGO-STUBS-COVERAGE.md"
RESULT_PATH = ROOT / "compatibility" / "differential-conformance.json"
TYPE_ALIAS_TYPES = (getattr(ast, "TypeAlias"),) if hasattr(ast, "TypeAlias") else ()
TEMPLATES_SETTING_IMPORT = "from django_stubs_ext.settings import TemplatesSetting\n"
TEMPLATES_SETTING_CLASS = """@type_check_only
class TemplatesSetting(TypedDict):
    BACKEND: str
    NAME: NotRequired[str]
    DIRS: NotRequired[list[str | _Path]]
    APP_DIRS: NotRequired[bool]
    OPTIONS: NotRequired[dict[str, Any]]
"""


def load_map() -> dict[str, Any]:
    with MAP_PATH.open("rb") as file:
        return tomllib.load(file)


def module_name(stub_root: Path, path: Path) -> str:
    relative = path.relative_to(stub_root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) or "django"


def assignment_names(statement: ast.stmt) -> list[str]:
    if isinstance(statement, (ast.Assign, ast.AnnAssign) + TYPE_ALIAS_TYPES):
        targets = (
            statement.targets
            if isinstance(statement, ast.Assign)
            else [statement.target]
        )
        return [target.id for target in targets if isinstance(target, ast.Name)]
    return []


def collect_symbols(node: ast.AST, prefix: str, symbols: set[str]) -> None:
    for statement in getattr(node, "body", []):
        names: list[str] = []
        if isinstance(statement, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            names = [statement.name]
        elif isinstance(statement, (ast.Import, ast.ImportFrom)):
            names = [
                alias.asname or alias.name.split(".")[0] for alias in statement.names
            ]
        else:
            names = assignment_names(statement)

        for name in names:
            if not name.startswith("_"):
                symbols.add(f"{prefix}.{name}")

        if isinstance(statement, ast.ClassDef) and not statement.name.startswith("_"):
            collect_symbols(statement, f"{prefix}.{statement.name}", symbols)


def inventory(stub_root: Path) -> tuple[int, int]:
    paths = sorted(stub_root.rglob("*.pyi"))
    symbols: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        collect_symbols(tree, module_name(stub_root, path), symbols)
    return len(paths), len(symbols)


def normalize_global_settings(source: str) -> str:
    if TEMPLATES_SETTING_IMPORT not in source:
        return source
    source = source.replace(
        "from collections.abc import Collection, Mapping, Sequence\n",
        "from collections.abc import Collection, Mapping, Sequence\nfrom pathlib import Path as _Path\n",
        1,
    )
    return source.replace(TEMPLATES_SETTING_IMPORT, TEMPLATES_SETTING_CLASS, 1)


def static_tree_fingerprint(stub_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(stub_root.rglob("*.pyi")) + sorted(stub_root.rglob("py.typed")):
        digest.update(f"django/{path.relative_to(stub_root).as_posix()}\0".encode())
        content = path.read_text(encoding="utf-8")
        if path.relative_to(stub_root).as_posix() == "conf/global_settings.pyi":
            content = normalize_global_settings(content)
        digest.update(content.encode())
        digest.update(b"\0")
    return digest.hexdigest()


def git_commit(repository_root: Path) -> str | None:
    if not (repository_root / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def resolve_upstream(
    path: str, baseline: dict[str, Any]
) -> tuple[Path, str, str | None]:
    repository_root = Path(path).resolve()
    stub_root = repository_root / baseline["upstream_stub_root"]
    if not stub_root.is_dir():
        raise ValueError(f"{repository_root} does not contain the pinned source layout")
    with (repository_root / "pyproject.toml").open("rb") as file:
        version = tomllib.load(file)["project"]["version"]
    return stub_root, version, git_commit(repository_root)


def mapped_transformers(features: list[dict[str, Any]]) -> set[str]:
    return {
        Path(reference.split(":", 1)[0]).stem
        for feature in features
        for reference in feature["upstream"]
        if reference.startswith("mypy_django_plugin/transformers/")
    }


def check_transformer_coverage(
    baseline: dict[str, Any], features: list[dict[str, Any]], upstream_root: Path | None
) -> list[str]:
    expected = set(baseline["expected_transformers"])
    errors = [
        f"upstream transformer is not classified: {name}"
        for name in sorted(expected - mapped_transformers(features))
    ]
    if upstream_root:
        actual = {
            path.stem
            for path in (upstream_root / "mypy_django_plugin" / "transformers").glob(
                "*.py"
            )
            if path.stem != "__init__"
        }
        if actual != expected:
            errors.append(
                "pinned source transformer inventory changed: "
                f"expected {sorted(expected)}, found {sorted(actual)}"
            )
    return errors


def load_result() -> dict[str, Any]:
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def check_result(
    result: dict[str, Any],
    baseline: dict[str, Any],
    conformance: dict[str, Any],
    features: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    expected = {
        feature["id"] for feature in features if feature["surface"] == "dynamic"
    }
    actual = {feature["id"] for feature in result.get("features", [])}
    if actual != expected:
        errors.append(
            f"differential feature inventory differs: expected {sorted(expected)}, found {sorted(actual)}"
        )
    reference = result.get("reference", {})
    if reference.get("django_stubs") != baseline["version"]:
        errors.append("differential result uses the wrong django-stubs version")
    if reference.get("django_stubs_commit") != baseline["commit"]:
        errors.append("differential result uses the wrong django-stubs commit")
    if reference.get("django") != conformance["django"]:
        errors.append("differential result uses the wrong reference Django version")
    candidate = result.get("candidate", {})
    for key in ("django", "django_ty", "ty_extended", "ty_extended_commit"):
        expected = conformance[key]
        if candidate.get(key) != expected:
            errors.append(f"differential result uses the wrong candidate {key}")
    scores = result.get("scores", {})
    total = sum(feature.get("cases", 0) for feature in result.get("features", []))
    matched = sum(feature.get("matched", 0) for feature in result.get("features", []))
    if total != scores.get("total_assertions") or matched != scores.get(
        "matched_assertions"
    ):
        errors.append("differential score totals do not match feature results")
    return errors


def document(
    baseline: dict[str, Any],
    stub_files: int,
    public_symbols: int,
    fingerprint: str,
    result: dict[str, Any],
    target_percent: float,
) -> str:
    scores = result["scores"]
    counts = Counter(feature["status"] for feature in result["features"])
    lines = [
        "# Django Compatibility Map",
        "",
        f"Static declaration baseline: [`{baseline['upstream_name']}` {baseline['version']}]({baseline['repository']}/tree/{baseline['commit']}) at `{baseline['commit']}`.",
        "",
        "`django-ty` vendors the pinned declaration tree inside its wheel. It neither installs nor executes the upstream mypy plugin.",
        "",
        "## Measured Surface",
        "",
        f"- Static API: **100% available**: {stub_files} `.pyi` modules and {public_symbols} public symbols are packaged in the wheel.",
        f"- Vendored static-tree SHA-256: `{fingerprint}`.",
        f"- Dynamic feature-balanced parity: **{scores['feature_balanced_percent']:.1f}%** across {result['corpus']['features']} reference capabilities ({counts['supported']} supported, {counts['partial']} partial, {counts['unsupported']} unsupported).",
        f"- Assertion conformance: **{scores['assertion_conformance_percent']:.1f}%** ({scores['matched_assertions']} of {scores['total_assertions']} reference outcomes matched).",
        f"- Candidate host: `django-ty` {result['candidate']['django_ty']} on `ty-extended` {result['candidate']['ty_extended']} at `{result['candidate']['ty_extended_commit']}`.",
        f"- Target: **{target_percent}%** dynamic semantic parity. The static score is deliberately separate and does not hide semantic gaps.",
        "",
        "Auxiliary `django-stubs-ext` utilities such as `WithAnnotations` are outside this Django-behavior inventory. The candidate wheel must not install or package `django-stubs`, `django-stubs-ext`, or mypy; generic `Annotated` transport remains a library-neutral ty-extended plugin capability.",
        "",
        "## Methodology",
        "",
        "The inventory maps every transformer module in the pinned django-stubs plugin to reviewed capabilities. Each capability has at least two line-level assertions in one shared Django project.",
        "",
        "Pinned mypy plus django-stubs is the reference oracle. Every assertion declares whether the reference must accept or reject it; disagreement invalidates the corpus. ty then checks the identical files. A match means both checkers made the same accept/reject decision on that assertion line. Diagnostics on unmarked lines invalidate the run instead of affecting the score indirectly.",
        "",
        "Feature-balanced parity gives every capability equal weight. Assertion conformance reports the raw matched assertions. Diagnostic wording is retained as evidence but is not compared, because the checkers use different rule names and messages.",
        "",
        "## Dynamic Coverage",
        "",
        "| Area | Capabilities | Feature-balanced parity |",
        "| --- | ---: | ---: |",
    ]
    for area in result["areas"]:
        lines.append(
            f"| {area['area']} | {area['features']} | {area['percent']:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Feature Matrix",
            "",
            "| Area | Capability | Cases matched | Parity | Status | Upstream reference |",
            "| --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for feature in result["features"]:
        upstream = "<br>".join(feature["upstream"])
        lines.append(
            f"| {feature['area']} | `{feature['id']}` | {feature['matched']}/{feature['cases']} | {feature['percent']:.1f}% | {feature['status']} | `{upstream}` |"
        )
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```sh",
            "bash scripts/differential-conformance.sh --check",
            "uv run --no-project --python 3.11 python scripts/evaluate_django_stubs_coverage.py --check",
            "```",
            "",
            "To additionally verify the vendored files against the pinned source checkout:",
            "",
            "```sh",
            "uv run --no-project --python 3.11 python scripts/evaluate_django_stubs_coverage.py --upstream-root /path/to/django-stubs-6.0.6 --check",
            "```",
            "",
            "The differential runner builds both environments, validates every declared reference outcome, rejects diagnostics outside assertion markers, and compares accept/reject behavior line by line. The documentation check verifies the vendored static tree, source inventory, checked result, and generated report.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--upstream-root", help="pinned source checkout for provenance verification"
    )
    parser.add_argument(
        "--write", action="store_true", help="regenerate docs/DJANGO-STUBS-COVERAGE.md"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify inventory, provenance, evidence, and generated docs",
    )
    parser.add_argument(
        "--enforce-target",
        action="store_true",
        help="fail unless semantic coverage reaches the configured target",
    )
    parser.add_argument(
        "--print-fingerprint",
        action="store_true",
        help="print the current vendored static-tree SHA-256",
    )
    args = parser.parse_args()

    compatibility_map = load_map()
    baseline = compatibility_map["baseline"]
    conformance = compatibility_map["conformance"]
    features = compatibility_map["feature"]
    stub_root = ROOT / baseline["vendored_stub_root"]
    stub_files, public_symbols = inventory(stub_root)
    fingerprint = static_tree_fingerprint(stub_root)
    if args.print_fingerprint:
        print(fingerprint)
        return 0

    errors: list[str] = []
    for feature in features:
        if feature.get("surface") not in {"static", "dynamic"}:
            errors.append(f"{feature.get('id', '<unknown>')}: invalid surface")
        if not feature.get("upstream"):
            errors.append(
                f"{feature.get('id', '<unknown>')}: missing upstream reference"
            )

    result: dict[str, Any] = {}
    if not RESULT_PATH.is_file():
        errors.append(
            "differential result is missing; run scripts/differential-conformance.sh --write"
        )
    else:
        try:
            result = load_result()
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            errors.append(f"invalid differential result: {error}")
        else:
            errors.extend(check_result(result, baseline, conformance, features))

    if not stub_root.is_dir():
        errors.append("vendored static API directory is missing")
    if (ROOT / "python" / "django_ty" / "stubs" / "django_stubs_ext").exists():
        errors.append("django_stubs_ext must not be vendored")
    if (ROOT / "python" / "django_ty" / "stubs" / "mypy_django_plugin").exists():
        errors.append("the upstream mypy plugin must not be vendored")
    if stub_files != baseline["expected_stub_files"]:
        errors.append(
            f"stub file inventory {stub_files} does not match {baseline['expected_stub_files']}"
        )
    if public_symbols != baseline["expected_public_symbols"]:
        errors.append(
            f"public symbol inventory {public_symbols} does not match {baseline['expected_public_symbols']}"
        )
    expected_fingerprint = baseline.get("expected_static_tree_sha256")
    if not expected_fingerprint:
        errors.append("baseline is missing expected_static_tree_sha256")
    elif fingerprint != expected_fingerprint:
        errors.append("vendored static-tree SHA-256 does not match the pinned baseline")

    upstream_root: Path | None = None
    if args.upstream_root:
        try:
            upstream_stub_root, version, commit = resolve_upstream(
                args.upstream_root, baseline
            )
        except ValueError as error:
            errors.append(str(error))
        else:
            upstream_root = Path(args.upstream_root).resolve()
            if version != baseline["version"]:
                errors.append(
                    f"source version {version} does not match pinned {baseline['version']}"
                )
            if commit != baseline["commit"]:
                errors.append(
                    f"source commit {commit} does not match pinned {baseline['commit']}"
                )
            if static_tree_fingerprint(upstream_stub_root) != fingerprint:
                errors.append(
                    "vendored static tree does not match the pinned source checkout"
                )

    errors.extend(check_transformer_coverage(baseline, features, upstream_root))
    semantic_percent = result.get("scores", {}).get("feature_balanced_percent", 0.0)
    output = ""
    if result:
        output = document(
            baseline,
            stub_files,
            public_symbols,
            fingerprint,
            result,
            compatibility_map["scoring"]["semantic_target_percent"],
        )
    if args.write and output:
        DOCUMENT_PATH.parent.mkdir(exist_ok=True)
        DOCUMENT_PATH.write_text(output, encoding="utf-8")
    if args.check:
        if (
            not output
            or not DOCUMENT_PATH.is_file()
            or DOCUMENT_PATH.read_text(encoding="utf-8") != output
        ):
            errors.append(
                "docs/DJANGO-STUBS-COVERAGE.md is out of date; rerun with --write"
            )
    if (
        args.enforce_target
        and semantic_percent < compatibility_map["scoring"]["semantic_target_percent"]
    ):
        errors.append(
            f"semantic coverage {semantic_percent:.1f}% is below {compatibility_map['scoring']['semantic_target_percent']}%"
        )

    if errors:
        print("Django compatibility map failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        output
        if not args.check
        else f"Django compatibility map passed: {semantic_percent:.1f}% semantic parity"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
