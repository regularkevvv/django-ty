"""Check modern Django declarations through an installed plugin and runtime."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata as metadata
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from runtime_config import checker_options
from ty_extended import find_ty_extended_bin

ROOT = Path(__file__).resolve().parents[1]


def runtime_contracts() -> dict:
    from django.conf import settings

    if not settings.configured:
        settings.configure(USE_I18N=False)
    from django.core.exceptions import ValidationError
    from django.core.mail.message import EmailAttachment
    from django.core.paginator import AsyncPaginator
    from django.core.validators import DomainNameValidator, StepValueValidator
    from django.forms.widgets import ColorInput, SearchInput, TelInput

    observed = {}
    for widget, expected in [
        (ColorInput, "color"),
        (SearchInput, "search"),
        (TelInput, "tel"),
    ]:
        assert widget().input_type == expected
        observed[widget.__name__] = expected
    assert DomainNameValidator()("example.com") is None
    validator = StepValueValidator(2, offset=1)
    assert validator(3) is None
    try:
        validator(4)
    except ValidationError:
        observed["step-invalid-value"] = "rejected"
    else:
        raise AssertionError("step validator accepted an invalid value")
    attachment = EmailAttachment("example.txt", b"text", "text/plain")
    assert attachment.filename == "example.txt"
    observed["attachment"] = attachment.filename

    async def pagination():
        paginator = AsyncPaginator([1, 2], 1)
        assert await paginator.acount() == 2
        page = await paginator.apage(1)
        assert await page.aget_object_list() == [1]
        return {"count": 2, "page": [1]}

    observed["async-pagination"] = asyncio.run(pagination())
    return observed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    assert tuple(map(int, metadata.version("Django").split(".")[:2])) >= (6, 1)
    source = ROOT / "e2e/modern_static_api.py"
    markers = {
        number: match.group(1)
        for number, line in enumerate(source.read_text().splitlines(), 1)
        if (match := re.search(r"# modern-api: ([a-z-]+)", line))
    }
    expected = {line for line, name in markers.items() if name.startswith("invalid-")}
    assert len(markers) == 11 and len(expected) == 3
    binary = Path(find_ty_extended_bin()).resolve()
    environment = Path(sys.executable).parent.parent
    command = [
        str(binary),
        "check",
        str(source),
        *checker_options(environment, settings_module="conformance_project.settings"),
        "--project",
        str(ROOT / "conformance"),
        "--python",
        str(environment),
        "--python-version",
        f"{sys.version_info.major}.{sys.version_info.minor}",
        "--output-format",
        "gitlab",
        "--no-progress",
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "TY_UV": "0", "TY_MAX_PARALLELISM": "1"},
    )
    (args.output / "stdout.json").write_text(result.stdout)
    (args.output / "stderr.log").write_text(result.stderr)
    assert result.returncode == 1, result.stderr
    diagnostics = json.loads(result.stdout)
    actual = {item["location"]["positions"]["begin"]["line"] for item in diagnostics}
    assert actual == expected and len(diagnostics) == len(expected), diagnostics
    assert all(item["check_name"] == "invalid-assignment" for item in diagnostics)
    assert all(
        Path(item["location"]["path"]).resolve() == source.resolve()
        for item in diagnostics
    )
    report = {
        "passed": True,
        "versions": {
            name: metadata.version(name)
            for name in ["django-ty", "ty-extended", "ty", "Django"]
        },
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "checker_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "positive_assertions": len(markers) - len(expected),
        "negative_controls": len(expected),
        "runtime": runtime_contracts(),
        "documentation": [
            "https://docs.djangoproject.com/en/6.1/ref/forms/widgets/",
            "https://docs.djangoproject.com/en/6.1/ref/paginator/",
            "https://docs.djangoproject.com/en/6.1/ref/validators/",
            "https://docs.djangoproject.com/en/6.1/topics/email/",
        ],
    }
    (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
