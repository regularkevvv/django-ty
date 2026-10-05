"""Reviewed adaptations shared by vendoring and provenance verification."""

import re

TEMPLATES_SETTING_IMPORT = "from django_stubs_ext.settings import TemplatesSetting\n"
TEMPLATES_SETTING_CLASS = """@type_check_only
class TemplatesSetting(TypedDict):
    BACKEND: str
    NAME: NotRequired[str]
    DIRS: NotRequired[list[str | _Path]]
    APP_DIRS: NotRequired[bool]
    OPTIONS: NotRequired[dict[str, Any]]
"""
MUTABLE_REQUEST = """@type_check_only
class _MutableHttpRequest(HttpRequest):
    GET: QueryDict  # type: ignore[assignment]
    POST: QueryDict  # type: ignore[assignment]

"""


def normalize_stub(relative_path: str, source: str) -> str:
    if (
        relative_path == "conf/global_settings.pyi"
        and TEMPLATES_SETTING_IMPORT in source
    ):
        source = source.replace(
            "from collections.abc import Collection, Mapping, Sequence\n",
            "from collections.abc import Collection, Mapping, Sequence\nfrom pathlib import Path as _Path\n",
            1,
        ).replace(TEMPLATES_SETTING_IMPORT, TEMPLATES_SETTING_CLASS, 1)
    if (
        relative_path == "http/request.pyi"
        and "class _MutableHttpRequest(" not in source
    ):
        if (
            source.count("    def __init__(self) -> None: ...\n") != 1
            or source.count('_Z = TypeVar("_Z")') != 1
        ):
            raise ValueError(
                "upstream HttpRequest layout changed; review the mutable constructor adaptation"
            )
        # Constructor mutability belongs to the exact-class call hook. Changing
        # __new__ here would also replace the type of every request subclass.
        source = source.replace(
            '_Z = TypeVar("_Z")', MUTABLE_REQUEST + '_Z = TypeVar("_Z")', 1
        )
    if relative_path == "db/models/enums.pyi":
        source = source.replace(
            "from enum import EnumType, IntEnum, StrEnum\nfrom enum import property as enum_property\n",
            """from enum import IntEnum
if sys.version_info >= (3, 11):
    from enum import EnumType, StrEnum
    from enum import property as enum_property
else:
    from enum import EnumMeta as EnumType
    from builtins import property as enum_property
    class StrEnum(str, enum.Enum): ...
""",
        )
    if relative_path in {"db/migrations/operations/base.pyi", "utils/csp.pyi"}:
        enum_name = "_StrEnum" if relative_path == "utils/csp.pyi" else "StrEnum"
        enum_import = (
            "from enum import StrEnum"
            + (" as _StrEnum" if enum_name.startswith("_") else "")
            + "\n"
        )
        source = re.sub(
            r"^" + re.escape(enum_import),
            "import sys as _sys\nfrom enum import Enum as _Enum\n"
            + f"if _sys.version_info >= (3, 11):\n    from enum import StrEnum as {enum_name}\n"
            + f"else:\n    class {enum_name}(str, _Enum): ...\n",
            source,
            flags=re.MULTILINE,
        )
    modern = {
        "Self",
        "NotRequired",
        "Required",
        "Never",
        "Unpack",
        "TypeVarTuple",
        "LiteralString",
        "TypeIs",
        "ReadOnly",
        "TypeAliasType",
        "override",
    }

    def backport(match: re.Match[str]) -> str:
        names = match.group(1).split(", ")
        moved = [name for name in names if name in modern]
        if not moved:
            return match.group(0)
        kept = [name for name in names if name not in modern]
        imports = ["from typing import " + ", ".join(kept)] if kept else []
        imports.append("from typing_extensions import " + ", ".join(moved))
        return "\n".join(imports)

    return re.sub(
        r"^from typing import ([^\n]+)$", backport, source, flags=re.MULTILINE
    )
