#!/usr/bin/env python3
"""Compare QueryDict assignment checking with the installed Django runtime."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

CASES = {
    "fresh-get": "HttpRequest().GET",
    "fresh-post": "HttpRequest().POST",
    "framework-get": 'RequestFactory().get("/").GET',
    "framework-post": 'RequestFactory().post("/").POST',
    "default-querydict": 'QueryDict("page=0")',
    "explicit-mutable": 'QueryDict("page=0", mutable=True)',
    "mutable-copy": 'RequestFactory().get("/").GET.copy()',
}
IMPORTS = "from django.http import HttpRequest, QueryDict\nfrom django.test import RequestFactory\n"


def check(environment: Path) -> dict[str, str]:
    python = environment / "bin" / "python"
    runtime = (
        IMPORTS
        + """from django.conf import settings
settings.configure(DEFAULT_CHARSET="utf-8", SECRET_KEY="querydict-test")
"""
    )
    runtime += f"cases = {CASES!r}\n"
    runtime += """import json
outcomes = {}
for name, expression in cases.items():
    querydict = eval(expression)
    try:
        querydict["page"] = "1"
    except AttributeError:
        outcomes[name] = "reject"
    else:
        assert querydict["page"] == "1"
        outcomes[name] = "accept"
print(json.dumps(outcomes))
"""
    actual = json.loads(
        subprocess.check_output([str(python), "-c", runtime], text=True)
    )
    expected = {
        name: "reject"
        if name in {"framework-get", "framework-post", "default-querydict"}
        else "accept"
        for name in CASES
    }
    if actual != expected:
        raise RuntimeError(f"Django runtime mutability changed: {actual}")
    with tempfile.TemporaryDirectory(prefix="django-ty-querydict-") as directory:
        root = Path(directory)
        (root / "pyproject.toml").write_text(
            '[project]\nname = "querydict-proof"\nversion = "0"\nrequires-python = ">=3.10"\n[tool.ty.plugins]\nauto-discover = true\n'
        )
        for name, expression in CASES.items():
            path = root / "case.py"
            path.write_text(
                IMPORTS + f'querydict = {expression}\nquerydict["page"] = "1"\n'
            )
            result = subprocess.run(
                [
                    str(environment / "bin" / "ty"),
                    "check",
                    str(path),
                    "--project",
                    str(root),
                    "--python",
                    str(environment),
                    "--output-format",
                    "concise",
                    "--color",
                    "never",
                    "--no-progress",
                ],
                capture_output=True,
                text=True,
            )
            output = result.stdout + result.stderr
            if actual[name] == "accept":
                if result.returncode != 0:
                    raise RuntimeError(
                        f"{name}: checker rejected a mutable QueryDict:\n{output}"
                    )
            else:
                diagnostics = re.findall(r"error\[([^]]+)\]", output)
                if (
                    result.returncode != 1
                    or len(diagnostics) != 1
                    or "django-ty.immutable-querydict-write" not in output
                ):
                    raise RuntimeError(
                        f"{name}: expected exactly one plugin mutation diagnostic:\n{output}"
                    )
    return actual


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment", type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.environment.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
