"""Check the Monty implementation, SDK signatures and rejection of invalid types."""

from __future__ import annotations

import ast
import inspect
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from ty import plugin_sdk

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "python/django_ty"

NEGATIVE = """from django_ty._monty_sdk import call_state_patch, field_patch, type_annotation
from django_ty._monty_types import CallRequest, CallReturnResponse, LiteralValue, ModelIndex
from django_ty.monty import typed_literal

literal: LiteralValue = {"kind": "int", "value": "wrong"}  # reject
field_patch("id", type_annotation("int"), instance_set_type=42)  # reject
call_state_patch(receiver_members={"id": "int"})  # reject
request: CallRequest = {"callee": type_annotation("Book"), "argumnts": []}  # reject
response: CallReturnResponse = {"kind": "call-state-patch", "return-type": type_annotation("int")}  # reject
result: int | None = typed_literal({"kind": "keyword"}, "str")  # reject

def invalid_index(model: ModelIndex) -> None:
    model["field_types"]["title"] = 42  # reject
"""


def check_annotations() -> int:
    functions = [
        node
        for node in ast.walk(ast.parse((PACKAGE / "monty.py").read_text()))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    for node in functions:
        args = node.args
        parameters = [*args.posonlyargs, *args.args, *args.kwonlyargs]
        parameters += [arg for arg in (args.vararg, args.kwarg) if arg is not None]
        if node.returns is None or any(arg.annotation is None for arg in parameters):
            raise RuntimeError(f"Unannotated function: {node.name}:{node.lineno}")
    return len(functions)


def check_sdk_signatures() -> int:
    declarations = [
        node
        for node in ast.parse((PACKAGE / "_monty_sdk.pyi").read_text()).body
        if isinstance(node, ast.FunctionDef)
    ]
    for node in declarations:
        # Compile only the argument layout, without annotations. The SDK is
        # dynamic: hook decorators are closures rather than function declarations.
        args = node.args
        for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs]:
            arg.annotation = None
        for arg in (args.vararg, args.kwarg):
            if arg is not None:
                arg.annotation = None
        args.defaults = [ast.Constant(None) for _ in args.defaults]
        args.kw_defaults = [
            ast.Constant(None) if default is not None else None
            for default in args.kw_defaults
        ]
        node.returns = None
        namespace: dict[str, object] = {}
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                "sdk-signature",
                "exec",
            ),
            namespace,
        )

        def layout(signature: inspect.Signature) -> list[tuple[str, object, bool]]:
            return [
                (name, parameter.kind, parameter.default is not inspect.Parameter.empty)
                for name, parameter in signature.parameters.items()
            ]

        actual = layout(inspect.signature(getattr(plugin_sdk, node.name)))
        declared = layout(inspect.signature(namespace[node.name]))
        if actual != declared:
            raise RuntimeError(
                f"SDK signature changed for {node.name}: {actual} != {declared}"
            )
    return len(declarations)


def check_types() -> None:
    command = [
        sys.executable,
        "-m",
        "ty",
        "check",
        "--extra-search-path",
        str(ROOT / "python"),
        "--python",
        sys.executable,
        "--output-format",
        "concise",
        "--color",
        "never",
        "--no-progress",
    ]
    subprocess.run(
        [
            *command,
            *(
                str(PACKAGE / name)
                for name in ("monty.py", "_monty_types.pyi", "_monty_sdk.pyi")
            ),
        ],
        check=True,
        cwd=ROOT,
    )
    with tempfile.TemporaryDirectory(prefix="django-ty-types-") as directory:
        fixture = Path(directory) / "invalid.py"
        fixture.write_text(NEGATIVE)
        result = subprocess.run(
            [*command, str(fixture)], capture_output=True, text=True, cwd=ROOT
        )
        expected = {
            number
            for number, line in enumerate(NEGATIVE.splitlines(), 1)
            if "# reject" in line
        }
        diagnostics = result.stdout + result.stderr
        rejected = {
            int(line)
            for line in re.findall(r"invalid\.py:(\d+):\d+: error\[", diagnostics)
        }
        if result.returncode != 1 or rejected != expected:
            raise RuntimeError(
                f"Expected type errors on lines {expected}, got {rejected}:\n{diagnostics}"
            )
        print(
            f"ty rejected all {len(expected)} invalid payload, SDK, index and return types"
        )


def main() -> None:
    print(
        f"Annotated functions: {check_annotations()}; SDK declarations verified: {check_sdk_signatures()}"
    )
    check_types()


if __name__ == "__main__":
    main()
