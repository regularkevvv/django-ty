"""Compare fresh checker processes on two installed E2E fixture copies."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wasm-project", type=Path, required=True)
    parser.add_argument("--monty-project", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=7)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    results = {}
    projects = {
        "wasm": args.wasm_project.resolve(),
        "monty": args.monty_project.resolve(),
    }
    paths = [
        "accounts",
        "library",
        "commerce",
        "auditlog",
        "typechecks/positive.py",
        "typechecks/static_api.py",
    ]
    expected_versions = None
    for runtime, project in projects.items():
        python = project / ".venv/bin/python"
        code = 'import json,sys,importlib.metadata as m;print(json.dumps([sys.version, m.version("Django"), m.version("ty-extended"), m.version("django-ty")]))'
        versions = json.loads(
            subprocess.check_output([str(python), "-c", code], text=True)
        )
        if expected_versions is not None and versions != expected_versions:
            raise RuntimeError("Benchmark environments have different versions")
        expected_versions = versions
        files = {
            str(p.relative_to(project)): p.read_bytes()
            for path in paths
            for p in (
                [project / path]
                if (project / path).is_file()
                else sorted((project / path).rglob("*.py"))
            )
        }
        if runtime == "wasm":
            expected_files = files
        elif files != expected_files:
            raise RuntimeError("Benchmark fixture sources differ")
        results[runtime] = {"seconds": [], "versions": versions}
    # Alternate process launches to reduce order-related CPU/cache effects.
    for iteration in range(args.runs):
        runtimes = ["wasm", "monty"] if iteration % 2 == 0 else ["monty", "wasm"]
        for runtime in runtimes:
            project = projects[runtime]
            start = time.perf_counter()
            completed = subprocess.run(
                [str(project / ".venv/bin/ty"), "check", *paths],
                cwd=project,
                capture_output=True,
                text=True,
            )
            if completed.returncode:
                raise RuntimeError(completed.stdout + completed.stderr)
            results[runtime]["seconds"].append(time.perf_counter() - start)
    for result in results.values():
        result["median_seconds"] = statistics.median(result["seconds"])
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
