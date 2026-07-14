from typing import Any, Generic, TypeVar, cast

_ModelT = TypeVar("_ModelT")
_RowT = TypeVar("_RowT")


class QuerySet(Generic[_ModelT, _RowT]):
    def filter(self, **kwargs: Any) -> QuerySet[_ModelT, _RowT]:
        return self

    def get(self, **kwargs: Any) -> _RowT:
        return cast(_RowT, object())

    def first(self) -> _RowT | None:
        return None

    def values(self, *fields: str) -> QuerySet[_ModelT, dict[str, object]]:
        return cast(QuerySet[_ModelT, dict[str, object]], self)

    def values_list(
        self, *fields: str, flat: bool = False, named: bool = False
    ) -> QuerySet[_ModelT, object]:
        return cast(QuerySet[_ModelT, object], self)

    def annotate(self, **kwargs: Any) -> QuerySet[_ModelT, _RowT]:
        return self
