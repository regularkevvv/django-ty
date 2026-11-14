#!/usr/bin/env python3
"""Reproduce the packaged native Django declarations from pinned inputs.

The native root is django-types 0.24.0's django-stubs directory. The legacy root
is Django-ty 0.7.0's python/django_ty/stubs/django directory. Both complete input
trees and every adapter preimage are verified before writing any output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "compatibility" / "native-types-vendor.json"
DESTINATION = ROOT / "python" / "django_ty" / "stubs" / "django"


def files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and (path.suffix == ".pyi" or path.name == "py.typed")
    }


def fingerprint(tree: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name, content in sorted(tree.items()):
        digest.update(name.encode() + b"\0" + content + b"\0")
    return digest.hexdigest()


def reproduce(native: Path, legacy: Path) -> dict[str, bytes]:
    receipt = json.loads(RECEIPT.read_text())
    trees = {"native": files(native), "legacy": files(legacy)}
    for label, tree in trees.items():
        if fingerprint(tree) != receipt[label]["tree_sha256"]:
            raise ValueError(f"{label} input differs from the reviewed pinned tree")
    result = trees["native"].copy()
    for name in receipt["restore"]:
        result[name] = trees["legacy"][name]
    for name in receipt["remove"]:
        del result[name]
    for name in receipt.get("modern_static", []):
        result[name] = trees["legacy"][name]
    for name, adapter in receipt["adapters"].items():
        original = result[name]
        if hashlib.sha256(original).hexdigest() != adapter["before_sha256"]:
            raise ValueError(f"adapter preimage differs: {name}")
        text = original.decode()
        for edit in reversed(adapter["edits"]):
            start, end = edit["start"], edit["end"]
            if text[start:end] != edit["before"]:
                raise ValueError(f"adapter context differs: {name}")
            text = text[:start] + edit["after"] + text[end:]
        result[name] = text.encode()
        if hashlib.sha256(result[name]).hexdigest() != adapter["after_sha256"]:
            raise ValueError(f"adapter output differs: {name}")
    if fingerprint(result) != receipt["output_tree_sha256"]:
        raise ValueError("reproduced output differs from the reviewed tree")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--django-types-root", required=True, type=Path)
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=DESTINATION)
    parser.add_argument("--write", action="store_true", help="replace the output tree")
    args = parser.parse_args()
    output = args.output.resolve()
    # Never erase an input tree when a caller chooses an output directory.
    for source in (args.django_types_root.resolve(), args.legacy_root.resolve()):
        if output == source or output in source.parents or source in output.parents:
            parser.error("output must be separate from both input trees")
    try:
        tree = reproduce(args.django_types_root, args.legacy_root)
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    if args.write:
        if output.exists():
            shutil.rmtree(output)
        for name, content in tree.items():
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    elif files(output) != tree:
        parser.exit(1, "vendored tree differs; inspect it before regenerating\n")
    print(f"verified {len(tree)} static files: {fingerprint(tree)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
