#!/usr/bin/env python3
"""Qualify native declaration adapters against real Django (POSIX source check).

This explicitly enables the experimental projection and loads this checkout's
plugin. Installed-wheel acceptance remains scripts/check_companion_install.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from check_companion_scalability import check

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment", type=Path)
    parser.add_argument("--ty-bin", required=True, type=Path)
    parser.add_argument("--official-ty", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    project = out / "project"
    fixture = ROOT / "tests/fixtures/native_api"
    shutil.copytree(fixture, project, ignore=shutil.ignore_patterns("runtime_probe.py"))
    python = args.environment.resolve() / "bin/python"
    python_version = subprocess.check_output(
        [python, "-c", "import sys;print(str(sys.version_info.major)+'.'+str(sys.version_info.minor))"], text=True
    ).strip()
    package = ROOT / "python/django_ty"
    (project / "ty.toml").write_text(
        '[environment]\npython-version=' + json.dumps(python_version) + '\n[plugins]\nenabled=true\nauto-discover=false\n'
        '[[plugins.plugin]]\nid="django-ty"\nruntime="monty"\ntrusted=true\n'
        + "path=" + json.dumps(str(package / "monty.py")) + "\n"
        + "manifest-path=" + json.dumps(str(package / "ty-plugin.json")) + "\n"
        + "stub-overlay-path=" + json.dumps(str(package / "stubs")) + "\n"
        + '[plugins.plugin.config]\ndjango-settings-module="settings"\n'
    )
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in project.iterdir()}
    expected = {
        i + 1: line.split("# control:", 1)[1].strip()
        for i, line in enumerate((project / "checks.py").read_text().splitlines())
        if "# control:" in line
    }
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "DJANGO_SETTINGS_MODULE": "settings"}
    report = {
        "passed": False,
        "scope": "Experimental checkout source; installed artifacts not qualified",
        "candidate_sha256": hashlib.sha256(args.ty_bin.read_bytes()).hexdigest(),
        "plugin_sha256": hashlib.sha256((package / "monty.py").read_bytes()).hexdigest(),
        "native_version": subprocess.check_output([args.official_ty, "--version"], text=True).strip(),
        "runs": [],
    }
    try:
        result = subprocess.run(
            [python, "-c", (fixture / "runtime_probe.py").read_text()],
            cwd=project, env=env, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr
        facts = json.loads(result.stdout)
        assert facts == {"implicit_id": "BigAutoField", "explicit_id": "AutoField", "acheck_password": True, "aget_user": True, "alogout": True, "aupdate_session_auth_hash": True, "password_none_is_false": True, "pk_rejected": True, "custom_id_rejected": True}, facts
        report["runtime"] = facts
        for mode in ["0", "1"]:
            run_out = out / ("memory" if mode == "1" else "disk")
            run_out.mkdir()
            previous = {key: os.environ.get(key) for key in ["TY_COMPANION_NATIVE_FIELDS", "TY_COMPANION_MEMORY_PROJECTION", "PYTHONDONTWRITEBYTECODE"]}
            try:
                os.environ.update({"TY_COMPANION_NATIVE_FIELDS": "1", "TY_COMPANION_MEMORY_PROJECTION": mode, "PYTHONDONTWRITEBYTECODE": "1"})
                run = check(
                    [str(args.ty_bin.resolve()), "check", "--ty", str(args.official_ty.resolve()), "--python", str(python), "--config-file", str(project / "ty.toml"), "--output-format", "gitlab", "--no-progress", "--color", "never", str(project)],
                    project, run_out, timeout=90, max_mib=4096,
                )
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
            diagnostics = json.loads((run_out / "stdout.json").read_text())
            assert run["exit"] == 1 and not run["stopped"] and run["source_preserved"], run
            assert len(diagnostics) == len(expected), diagnostics
            actual = {}
            for diagnostic in diagnostics:
                assert Path(diagnostic["location"]["path"]).name == "checks.py", diagnostic
                line = diagnostic["location"]["positions"]["begin"]["line"]
                assert diagnostic["check_name"] == expected.get(line), diagnostic
                actual[line] = diagnostic["check_name"]
            assert actual == expected, (actual, expected)
            assert all((p.read_bytes(), p.stat().st_mtime_ns) == original for p, original in before.items()), "source changed"
            report["runs"].append({"mode": mode, "controls": expected, "run": run})
        report["passed"] = True
    finally:
        shutil.rmtree(project)
        report["project_cleaned"] = True
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
