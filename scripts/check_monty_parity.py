"""Replay Rust regression requests through CPython or the pinned Monty sandbox.

Usage: python scripts/check_monty_parity.py oracle.jsonl responses.jsonl --runtime monty
Pass responses.jsonl to `cargo run --example compare_monty` for SDK-level equality.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("oracle", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--runtime", choices=["cpython", "monty"], required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    sdk = importlib.util.find_spec("ty.plugin_sdk")
    if sdk is None or sdk.origin is None:
        raise RuntimeError("Install ty-extended 0.84.4 in the test environment")
    root = Path(__file__).resolve().parent.parent
    source = (
        Path(sdk.origin).read_text()
        + "\n\n"
        + (root / "python/django_ty/monty.py").read_text()
    )
    records = [json.loads(line) for line in args.oracle.read_text().splitlines()]
    packaged = json.loads(args.manifest.read_text())
    packaged["runtime"] = {"kind": "monty", "artifact": "monty.py"}
    records.append(
        {"request": {"kind": "manifest"}, "expected": {"kind": "manifest", **packaged}}
    )
    if args.runtime == "cpython":
        namespace = {}
        exec(compile(source, "django-ty.py", "exec"), namespace)
        produced = [
            json.loads(namespace["__ty_handle__"](json.dumps(record["request"])))
            for record in records
        ]
    else:
        from pydantic_monty import Monty

        produced = []
        with Monty(max_processes=1) as pool:
            for index, record in enumerate(records):
                with pool.checkout(
                    limits={
                        "max_feed_duration_secs": 5.0,
                        "max_recursion_depth": 1000,
                        "max_suspensions": 0,
                    }
                ) as session:
                    try:
                        response = session.feed_run(
                            source + "\n\n__ty_handle__(request_json)",
                            inputs={"request_json": json.dumps(record["request"])},
                        )
                    except Exception as exc:
                        raise RuntimeError(
                            f"Monty failed on regression request {index}: {record['request']['kind']}"
                        ) from exc
                    produced.append(json.loads(response))
    with args.output.open("w") as output:
        for record, actual in zip(records, produced, strict=True):
            output.write(json.dumps({**record, "actual": actual}) + "\n")
    print(f"Executed {len(records)} regression requests through {args.runtime}")


if __name__ == "__main__":
    main()
