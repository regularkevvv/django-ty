"""Generate/check the manifest embedded in the standalone Monty plugin."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    package = root / "python/django_ty"
    manifest_path = package / "ty-plugin.json"
    alias_path = package / "ty-plugin-monty.json"
    source_path = package / "monty.py"
    manifest = json.loads(manifest_path.read_text())
    if manifest["runtime"] != {"kind": "monty", "artifact": "monty.py"}:
        raise RuntimeError("The packaged plugin must use the Monty companion")
    version = re.search(
        r'^version = "([^"]+)"', (root / "pyproject.toml").read_text(), re.MULTILINE
    ).group(1)
    if manifest["version"] != version:
        raise RuntimeError("Monty manifest version does not match package version")
    encoded = json.dumps(manifest, indent=2) + "\n"
    prefix = source_path.read_text().split("\n# Packaged manifest\n")[0]
    source = (
        prefix
        + "\n# Packaged manifest\n@on_manifest\n"
        + "def packaged_manifest(request: dict[str, JsonValue]) -> dict[str, JsonValue]:\n"
        + '    return json.loads(r"""\n'
        + encoded
        + '""")\n'
    )
    if args.check:
        if (
            manifest_path.read_text() != encoded
            or alias_path.read_text() != encoded
            or source_path.read_text() != source
        ):
            raise RuntimeError(
                "Run python scripts/build-monty.py to regenerate the embedded manifest"
            )
    else:
        manifest_path.write_text(encoded)
        alias_path.write_text(encoded)
        if source_path.read_text() != source:
            source_path.write_text(source)


if __name__ == "__main__":
    main()
