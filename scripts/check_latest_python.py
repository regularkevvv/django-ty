"""Check latest Python against Django contracts independently of comparator support."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import tomllib
from check_querydict_runtime import check as querydict_check
from ty_extended import find_ty_extended_bin


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mypy-bin", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    assert sys.version_info[:2] == (3, 15)
    root = Path(__file__).resolve().parents[1]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    baseline = tomllib.loads((root / "compatibility/conformance.toml").read_text())
    environment = Path(sys.executable).parent.parent
    result_path = out / "contracts.json"
    subprocess.run(
        [
            sys.executable,
            str(root / "scripts/evaluate_differential_conformance.py"),
            "--mypy-bin",
            str(args.mypy_bin),
            "--ty-bin",
            str(find_ty_extended_bin()),
            "--ty-python",
            str(environment),
            "--probe",
            "--write",
            "--result-path",
            str(result_path),
            "--django-stubs-commit",
            baseline["baseline"]["commit"],
        ],
        check=True,
    )
    result = json.loads(result_path.read_text())
    assert result["authority"]["name"] == "Django official documentation"
    assert result["candidate"]["python"] == "3.15"
    assert result["candidate"]["django"] == "6.1.3"
    assert (
        result["scores"]["contract_matched_assertions"]
        == result["scores"]["total_assertions"]
        == 172
    )
    assert not result["unowned_diagnostics"].get("ty")
    assert not any(result["unparsed_output"].values())
    proofs = result["django_runtime"]["cases"]
    assert len(proofs) == 84 and all(proof["passed"] for proof in proofs.values())
    querydict = querydict_check(environment)
    assert len(querydict) == 9
    receipt = {
        "passed": True,
        "candidate": result["candidate"],
        "reference": result["reference"],
        "contract_assertions": 172,
        "runtime_contracts": 84,
        "querydict": querydict,
        "scope": "Django documentation and its installed runtime are the authority on Python 3.15. The pinned mypy/django-stubs baseline runs on its separately supported Python interpreter; this is not a version-matched Python 3.15 comparator pair.",
    }
    (out / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        "Python 3.15: 172 Django assertions, 84 runtime contracts and nine QueryDict cases passed"
    )


if __name__ == "__main__":
    main()
