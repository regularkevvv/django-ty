"""Replay regression requests through CPython or the pinned Monty sandbox.

scripts/check-monty-parity.sh generates the corpus, runs both interpreters and
compares complete responses through tests/monty_parity.rs. Django runtime
contracts provide the independent semantic reference; the historical Rust
implementation uses a different declaration provider and eager index format.
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
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    if args.runtime == "monty" and args.reference is None:
        parser.error("Monty requires independently executed CPython responses")
    sdk = importlib.util.find_spec("ty_extended.plugin_sdk")
    if sdk is None or sdk.origin is None:
        raise RuntimeError("Install ty-extended 0.90.0 in the test environment")
    root = Path(__file__).resolve().parent.parent
    source = (
        Path(sdk.origin).read_text()
        + "\n\n"
        + (root / "python/django_ty/monty.py").read_text()
    )
    records = [json.loads(line) for line in args.oracle.read_text().splitlines()]
    records.append({"request": {"kind": "manifest"}})
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
                            inputs={
                                "request_json": json.dumps(record["request"]),
                                # Match hosts that provide the full inline index.
                                # No external lookup or suspension is permitted.
                                "_ty_project_index_lookup": None,
                            },
                        )
                    except Exception as exc:
                        raise RuntimeError(
                            f"Monty failed on regression request {index}: {record['request']['kind']}"
                        ) from exc
                    produced.append(json.loads(response))
    # Check the complete current handshake, including fields absent from the
    # historical SDK. The subsequent parity comparison also preserves all fields.
    expected_manifest = {
        "kind": "manifest",
        **json.loads((root / "python/django_ty/ty-plugin.json").read_text()),
    }
    if produced[-1] != expected_manifest:
        raise RuntimeError("Runtime manifest differs from the packaged manifest")
    reference = (
        [json.loads(line) for line in args.reference.read_text().splitlines()]
        if args.reference is not None
        else None
    )
    if reference is not None and len(reference) != len(records):
        raise RuntimeError("CPython reference has a different request count")
    with args.output.open("w") as output:
        for index, (record, actual) in enumerate(zip(records, produced, strict=True)):
            row = {"request": record["request"], "actual": actual}
            if reference is not None:
                if reference[index]["request"] != record["request"]:
                    raise RuntimeError(f"CPython reference request changed at {index}")
                row["expected"] = reference[index]["actual"]
            output.write(json.dumps(row) + "\n")
    print(f"Executed {len(records)} regression requests through {args.runtime}")


if __name__ == "__main__":
    main()
