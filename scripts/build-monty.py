"""Generate/check the manifest embedded in the standalone Monty plugin."""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--from-wasm", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    package = root / "python/django_ty"
    manifest_path = package / "ty-plugin-monty.json"
    source_path = package / "monty.py"
    manifest = json.loads(
        (package / "ty-plugin.json" if args.from_wasm else manifest_path).read_text()
    )
    manifest["runtime"] = {"kind": "monty", "artifact": "monty.py"}
    version = re.search(
        r'^version = "([^"]+)"', (root / "pyproject.toml").read_text(), re.MULTILINE
    ).group(1)
    if manifest["version"] != version:
        raise RuntimeError("Monty manifest version does not match package version")
    encoded = json.dumps(manifest, indent=2) + "\n"
    prefix = source_path.read_text().split("\n# Packaged manifest\n")[0]
    source = (
        prefix
        + '\n# Packaged manifest\nset_manifest(\n    json.loads(r"""\n'
        + encoded
        + '""")\n)\n'
    )
    if args.check:
        module = ast.parse(source_path.read_text())
        embedded = json.loads(ast.literal_eval(module.body[-1].value.args[0].args[0]))
        if manifest_path.read_text() != encoded or embedded != manifest:
            raise RuntimeError(
                "Run python scripts/build-monty.py to regenerate the embedded manifest"
            )
    else:
        manifest_path.write_text(encoded)
        module = ast.parse(source_path.read_text())
        embedded = json.loads(ast.literal_eval(module.body[-1].value.args[0].args[0]))
        if embedded != manifest:
            source_path.write_text(source)


if __name__ == "__main__":
    main()
