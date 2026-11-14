"""Reproduce packaged declarations from the two reviewed distribution wheels."""

from __future__ import annotations

import hashlib
import io
import json
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

from vendor_native_django import DESTINATION, RECEIPT, files, fingerprint, reproduce


def download(url: str) -> bytes:
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return response.read()
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))
    raise AssertionError("unreachable")


def main() -> None:
    receipt = json.loads(RECEIPT.read_text())
    with tempfile.TemporaryDirectory(
        prefix="django-ty-declaration-sources-"
    ) as temporary:
        roots = {}
        for label, prefix in [
            ("native", "django-stubs/"),
            ("legacy", "django_ty/stubs/django/"),
        ]:
            raw = download(receipt[label]["wheel_url"])
            assert hashlib.sha256(raw).hexdigest() == receipt[label]["wheel_sha256"]
            root = Path(temporary) / label
            roots[label] = root
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                for name in archive.namelist():
                    if not name.startswith(prefix):
                        continue
                    relative = Path(name.removeprefix(prefix))
                    if relative.suffix != ".pyi" and relative.name != "py.typed":
                        continue
                    assert not relative.is_absolute() and ".." not in relative.parts
                    target = root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(name))
        generated = reproduce(roots["native"], roots["legacy"])
        assert generated == files(DESTINATION)
        for label, root in roots.items():
            target = next(root.rglob("*.pyi"))
            original = target.read_bytes()
            target.write_bytes(original + b"\n# invalid source modification\n")
            try:
                reproduce(roots["native"], roots["legacy"])
            except ValueError:
                pass
            else:
                raise AssertionError(f"modified {label} input was accepted")
            finally:
                target.write_bytes(original)
        print(
            json.dumps(
                {
                    "passed": True,
                    "static_files": len(generated),
                    "tree_sha256": fingerprint(generated),
                    "tamper_controls": 2,
                }
            )
        )


if __name__ == "__main__":
    main()
