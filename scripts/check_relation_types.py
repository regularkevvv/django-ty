"""Check custom relation keys through the real companion in both projection modes."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

from evaluate_differential_conformance import MARKER_RE

ROOT = Path(__file__).resolve().parents[1]


def snapshot(root: Path) -> dict:
    return {
        str(path.relative_to(root)): (
            hashlib.sha256(path.read_bytes()).hexdigest(),
            path.stat().st_mtime_ns,
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--companion", type=Path, required=True)
    parser.add_argument("--ty", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--mypy", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"passed": False, "runs": []}
    package = ROOT / "python/django_ty"
    provider = snapshot(package / "stubs")
    report["plugin_sha256"] = hashlib.sha256(
        (package / "monty.py").read_bytes()
    ).hexdigest()
    report["companion_sha256"] = hashlib.sha256(args.companion.read_bytes()).hexdigest()
    try:
        with tempfile.TemporaryDirectory(prefix="django-relation-types-") as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(ROOT / "tests/fixtures/relation_keys", project)
            project = project.resolve()
            original = snapshot(project)
            statements = ast.parse((project / "checks.py").read_text()).body
            markers = {
                line: match["expect"] == "fail"
                for line, text in enumerate(
                    (project / "checks.py").read_text().splitlines(), 1
                )
                if (match := MARKER_RE.search(text))
            }
            assert len(markers) == 52
            ranges = {
                marker: next(
                    (statement.lineno, statement.end_lineno)
                    for statement in statements
                    if statement.lineno <= marker <= statement.end_lineno
                )
                for marker in markers
            }
            config = Path(temporary) / "companion.toml"
            config.write_text(
                "[environment]\npython-version='3.13'\n"
                "[plugins]\nenabled=true\nauto-discover=false\n"
                "[[plugins.plugin]]\nid='django-ty'\nruntime='monty'\ntrusted=true\n"
                + "\n".join(
                    f"{key}={json.dumps(str(package / name))}"
                    for key, name in (
                        ("path", "monty.py"),
                        ("manifest-path", "ty-plugin.json"),
                        ("stub-overlay-path", "stubs"),
                    )
                )
                + "\n[plugins.plugin.config]\ndjango-settings-module='settings'\n"
                "companion-native-call-returns=['get']\n"
                "companion-call-signature-methods=['from_queryset']\n"
            )
            for mode in ["disk", "memory"] + (["mypy"] if args.mypy else []):
                env = {
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "TY_COMPANION_NATIVE_FIELDS": "1",
                    "TY_COMPANION_MEMORY_PROJECTION": "1" if mode == "memory" else "0",
                    "TY_COMPANION_NATIVE_WARMUP": "1",
                    "TY_COMPANION_BORROW_OVERLAYS": "1",
                }
                command = [
                    str(args.companion.resolve()),
                    "check",
                    "--project",
                    str(project),
                    "--python",
                    str(args.python.resolve()),
                    "--python-version",
                    "3.13",
                    "--ty",
                    str(args.ty.resolve()),
                    "--config-file",
                    str(config),
                    "--output-format",
                    "gitlab",
                    "--no-progress",
                    "--color",
                    "never",
                    str(project),
                ]
                if mode == "mypy":
                    command = [
                        str(args.mypy.resolve()),
                        "--config-file",
                        str(project / "mypy.ini"),
                        "--output",
                        "json",
                        "--no-incremental",
                        "--cache-dir",
                        os.devnull,
                        str(project),
                    ]
                result = subprocess.run(
                    command,
                    cwd=project,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                (args.output / f"{mode}.stdout").write_text(result.stdout)
                (args.output / f"{mode}.stderr").write_text(result.stderr)
                assert result.returncode in [0, 1], (mode, result.stderr)
                diagnostics = (
                    [
                        json.loads(line)
                        for line in result.stdout.splitlines()
                        if line.strip()
                    ]
                    if mode == "mypy"
                    else json.loads(result.stdout)
                )
                grouped = defaultdict(list)
                unmarked = []
                for diagnostic in diagnostics:
                    path, line = (
                        (diagnostic["file"], diagnostic["line"])
                        if mode == "mypy"
                        else (
                            diagnostic["location"]["path"],
                            diagnostic["location"]["positions"]["begin"]["line"],
                        )
                    )
                    path = Path(path)
                    if not path.is_absolute():
                        path = project / path
                    matches = [
                        marker
                        for marker, (start, end) in ranges.items()
                        if start <= line <= end
                    ]
                    if path.resolve() == project / "checks.py" and len(matches) == 1:
                        grouped[matches[0]].append(diagnostic)
                    else:
                        unmarked.append(diagnostic)
                cases = [
                    {
                        "line": line,
                        "matched": bool(grouped[line]) == fail,
                        "diagnostics": grouped[line],
                    }
                    for line, fail in markers.items()
                ]
                row = {
                    "mode": mode,
                    "exit": result.returncode,
                    "matched": sum(case["matched"] for case in cases),
                    "total": len(cases),
                    "cases": cases,
                    "unmarked": unmarked,
                }
                report["runs"].append(row)
                assert snapshot(project) == original, "Fixture bytes or mtimes changed"
                assert not unmarked, row
                if mode != "mypy":
                    assert row["matched"] == row["total"], row
        report["project_cleaned"] = not project.exists()
        report["provider_preserved"] = snapshot(package / "stubs") == provider
        assert report["project_cleaned"] and report["provider_preserved"]
        report["passed"] = True
    finally:
        (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "passed": True,
                "matched": {r["mode"]: r["matched"] for r in report["runs"]},
            }
        )
    )


if __name__ == "__main__":
    main()
