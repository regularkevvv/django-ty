"""Reviewed adaptations shared by vendoring and provenance verification."""

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
        source = source.replace(
            "    def __init__(self) -> None: ...\n",
            "    def __new__(cls) -> _MutableHttpRequest: ...\n",
            1,
        ).replace('_Z = TypeVar("_Z")', MUTABLE_REQUEST + '_Z = TypeVar("_Z")', 1)
    return source
