from typing import Any, Generic, TypeVar, cast

from django.db.models.query import QuerySet

_ModelT = TypeVar("_ModelT")


class BaseManager(Generic[_ModelT]):
    def all(self) -> QuerySet[_ModelT, _ModelT]:
        return QuerySet()

    def filter(self, **kwargs: Any) -> QuerySet[_ModelT, _ModelT]:
        return QuerySet()

    def exclude(self, **kwargs: Any) -> QuerySet[_ModelT, _ModelT]:
        return QuerySet()

    def get(self, **kwargs: Any) -> _ModelT:
        return cast(_ModelT, object())

    def create(self, **kwargs: Any) -> _ModelT:
        return cast(_ModelT, object())

    def get_or_create(self, **kwargs: Any) -> tuple[_ModelT, bool]:
        return (cast(_ModelT, object()), True)

    def first(self) -> _ModelT | None:
        return None

    def count(self) -> int:
        return 0

    def exists(self) -> bool:
        return False

    def values(self, *fields: str) -> QuerySet[_ModelT, dict[str, object]]:
        return QuerySet()

    def values_list(
        self, *fields: str, flat: bool = False, named: bool = False
    ) -> QuerySet[_ModelT, object]:
        return QuerySet()

    def annotate(self, **kwargs: Any) -> QuerySet[_ModelT, _ModelT]:
        return QuerySet()


class Manager(BaseManager[_ModelT]):
    pass
