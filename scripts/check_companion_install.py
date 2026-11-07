"""Qualify an installed wheel through discovery, CLI and real editor sessions."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from lsp_client import Client
from ty_extended import find_ty_extended_bin

ROOT = Path(__file__).resolve().parents[1]
PATHS = [
    "accounts",
    "library",
    "commerce",
    "auditlog",
    "typechecks/positive.py",
    "typechecks/static_api.py",
]


def source_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    project = out / "project"
    shutil.copytree(ROOT / "e2e/django5_fixture", project)
    (project / "ty.toml").write_text(
        "[environment]\npython = "
        + json.dumps(sys.executable)
        + f'\npython-version = "{sys.version_info.major}.{sys.version_info.minor}"\n'
        + "[plugins]\nenabled = true\nauto-discover = true\n"
    )
    before = source_hash(project)
    binary = Path(find_ty_extended_bin()).resolve()
    package = Path(metadata.distribution("django-ty").locate_file("django_ty"))
    manifest = json.loads((package / "ty-plugin.json").read_text())
    assert manifest["version"] == metadata.version("django-ty")
    assert (package / "ty-plugin.json").read_bytes() == (
        package / "ty-plugin-monty.json"
    ).read_bytes()
    assert manifest["runtime"] == {"kind": "monty", "artifact": "monty.py"}
    assert not list(package.rglob("*.wasm"))
    names = {d.metadata.get("Name", "").lower() for d in metadata.distributions()}
    assert not any(name.startswith("pydantic-monty") for name in names)
    assert not names.intersection({"django-stubs", "django-stubs-ext", "mypy"})
    env = {
        **os.environ,
        "TY_UV": "0",
        "TY_MAX_PARALLELISM": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    env.pop("TY_COMPANION_TY", None)
    report = {
        "passed": False,
        "versions": {
            name: metadata.version(name)
            for name in ["django-ty", "ty-extended", "ty", "Django"]
        },
        "companion_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "checks": [],
    }

    def run(label: str, command: list[str], environment: dict[str, str] = env):
        result = subprocess.run(
            command,
            cwd=project,
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
        )
        (out / (label + ".stdout")).write_text(result.stdout)
        (out / (label + ".stderr")).write_text(result.stderr)
        return result

    try:
        for label, command, environment in [
            ("discovery", [str(binary), "check", *PATHS], env),
            ("module", [sys.executable, "-m", "django_ty", "check", *PATHS], env),
            (
                "empty-path",
                [
                    sys.executable,
                    "-m",
                    "django_ty",
                    "--settings-module",
                    "config.settings",
                    "check",
                    *PATHS,
                ],
                {**env, "PATH": str(out / "empty-path")},
            ),
        ]:
            result = run(label, command, environment)
            assert result.returncode == 0, (label, result.stdout, result.stderr)
            report["checks"].append(label)
        negative = run(
            "negative",
            [
                sys.executable,
                "-m",
                "django_ty",
                "check",
                "accounts",
                "library",
                "commerce",
                "auditlog",
                "caveats",
                "typechecks/negative.py",
            ],
        )
        assert negative.returncode == 1, negative
        for text in [
            "django-ty.unknown-relation-target",
            "django-ty.reverse-relation-conflict",
            "django-ty.invalid-lookup-value",
            "django-ty.unknown-lookup",
            "invalid-assignment",
        ]:
            assert text in negative.stdout + negative.stderr, text
        report["checks"].append("negative CLI controls")

        source = project / "typechecks/positive.py"
        original = source.read_text()
        configuration = {"diagnosticMode": "workspace"}

        def server_request(client: Client, request: dict) -> bool:
            if request["method"] != "workspace/configuration":
                return False
            client.send(
                {
                    "id": request["id"],
                    "result": [configuration for _ in request["params"]["items"]],
                }
            )
            return True

        client = Client(
            [str(binary), "server"],
            project,
            out / "editor.stderr",
            server_request_handler=server_request,
        )
        try:
            client.request(
                "initialize",
                {
                    "rootUri": project.as_uri(),
                    "workspaceFolders": [{"uri": project.as_uri(), "name": "project"}],
                    "capabilities": {
                        "textDocument": {
                            "diagnostic": {},
                            "hover": {"contentFormat": ["markdown"]},
                        },
                        "workspace": {"configuration": True},
                    },
                },
            )
            client.notify("initialized")
            uri = source.as_uri()
            client.notify(
                "textDocument/didOpen",
                {
                    "textDocument": {
                        "uri": uri,
                        "languageId": "python",
                        "version": 1,
                        "text": original,
                    }
                },
            )

            def diagnostics():
                return client.request(
                    "textDocument/diagnostic", {"textDocument": {"uri": uri}}
                )["items"]

            initial = diagnostics()
            assert not [item for item in initial if item.get("severity", 1) == 1], (
                initial
            )
            line = next(
                i
                for i, value in enumerate(original.splitlines())
                if value.startswith("title: str = book.title")
            )
            hover = client.request(
                "textDocument/hover",
                {
                    "textDocument": {"uri": uri},
                    "position": {
                        "line": line,
                        "character": original.splitlines()[line].index("book.title")
                        + 6,
                    },
                },
            )
            assert "str" in json.dumps(hover), hover
            bad = original + "\neditor_bad: int = book.title\n"
            client.notify(
                "textDocument/didChange",
                {
                    "textDocument": {"uri": uri, "version": 2},
                    "contentChanges": [{"text": bad}],
                },
            )
            items = diagnostics()
            assert any(
                item.get("code") == "invalid-assignment"
                and item["range"]["start"]["line"] == len(original.splitlines()) + 1
                for item in items
            ), items
            client.notify(
                "textDocument/didChange",
                {
                    "textDocument": {"uri": uri, "version": 3},
                    "contentChanges": [{"text": original}],
                },
            )
            restored = diagnostics()
            deadline = time.monotonic() + 5
            while (
                any(item.get("severity", 1) == 1 for item in restored)
                and time.monotonic() < deadline
            ):
                time.sleep(0.025)
                restored = diagnostics()
            assert not [item for item in restored if item.get("severity", 1) == 1], (
                restored
            )
            report["editor"] = {
                "configuration": configuration,
                "configuration_requests": client.server_requests,
                "initial": initial,
                "hover": hover,
                "unsaved_negative": items,
                "restored": restored,
            }
            report["checks"].extend(
                [
                    "LSP diagnostics",
                    "field hover",
                    "unsaved negative source span",
                    "unsaved restoration",
                ]
            )
        finally:
            client.close()
        assert source_hash(project) == before
        report["source_preserved"] = True
        report["passed"] = True
    finally:
        (out / "acceptance.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "Installed Django companion: discovery, module, empty PATH, CLI controls and LSP passed"
    )


if __name__ == "__main__":
    main()
