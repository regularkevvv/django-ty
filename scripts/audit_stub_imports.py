"""Reject unresolved Django-local imports in the packaged declaration tree."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
from pathlib import Path


def unresolved_imports(root: Path) -> list[tuple[str, str]]:
    modules = {}

    def flat(body):
        for n in body:
            if isinstance(n, (ast.If, ast.Try)):
                yield from flat(n.body)
                yield from flat(n.orelse)
                for handler in getattr(n, "handlers", []):
                    yield from flat(handler.body)
            else:
                yield n

    for p in root.rglob("*.pyi"):
        rel = p.relative_to(root).with_suffix("")
        parts = ["django", *rel.parts]
        package = parts[-1] == "__init__"
        if package:
            parts.pop()
        module = ".".join(parts)
        bindings = {}
        imports = []
        stars = []
        for n in flat(ast.parse(p.read_text()).body):
            if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                bindings[n.name] = True
            elif isinstance(n, (ast.Assign, ast.AnnAssign)):
                for t in n.targets if isinstance(n, ast.Assign) else [n.target]:
                    if isinstance(t, ast.Name):
                        bindings[t.id] = True
            elif isinstance(n, ast.Import):
                for a in n.names:
                    bindings[a.asname or a.name.split(".")[0]] = True
            elif isinstance(n, ast.ImportFrom):
                pkg = module if package else module.rpartition(".")[0]
                target = (
                    importlib.util.resolve_name("." * n.level + (n.module or ""), pkg)
                    if n.level
                    else n.module
                )
                for a in n.names:
                    if a.name == "*":
                        stars.append(target)
                        continue
                    bindings[a.asname or a.name] = (target, a.name)
                    if target.startswith("django.") or target == "django":
                        imports.append((target, a.name))
        modules[module] = {
            "bindings": bindings,
            "imports": imports,
            "stars": stars,
            "path": str(p.relative_to(root)),
        }

    def exists(module, name, seen=None):
        if module + "." + name in modules:
            return True
        if module not in modules:
            return not module.startswith("django")
        key = (module, name)
        seen = set() if seen is None else seen
        if key in seen:
            return False
        seen = seen | {key}
        entry = modules[module]
        value = entry["bindings"].get(name)
        if value is True:
            return True
        if value is not None:
            return exists(*value, seen)
        return any(exists(star, name, seen) for star in entry["stars"])

    missing = sorted(
        set(
            (target, name)
            for m in modules.values()
            for target, name in m["imports"]
            if not exists(target, name)
        )
    )
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stub-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "python/django_ty/stubs/django",
    )
    args = parser.parse_args()
    missing = unresolved_imports(args.stub_root)
    if missing:
        print(json.dumps(missing, indent=2))
        return 1
    print("All Django-local declaration imports resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
