#!/usr/bin/env python3
"""Read a conformance value from the compatibility map."""

from __future__ import annotations

import argparse
from pathlib import Path

import tomllib


MAP_PATH = (
    Path(__file__).resolve().parents[1]
    / "compatibility"
    / "django-stubs-6.0.6.toml"
)


def conformance_value(key: str, path: Path = MAP_PATH) -> str:
    with path.open("rb") as file:
        value = tomllib.load(file).get("conformance", {}).get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing string conformance value: {key}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("key")
    args = parser.parse_args()
    print(conformance_value(args.key))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
