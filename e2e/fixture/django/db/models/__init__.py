from typing import Any

from .base import Model
from .manager import BaseManager, Manager
from .query import QuerySet

CASCADE = object()


class Field:
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...


class CharField(Field):
    pass


class EmailField(Field):
    pass


class IntegerField(Field):
    pass


class BooleanField(Field):
    pass


class ForeignKey(Field):
    pass


class OneToOneField(Field):
    pass


class ManyToManyField(Field):
    pass


__all__ = [
    "BaseManager",
    "BooleanField",
    "CASCADE",
    "CharField",
    "EmailField",
    "Field",
    "ForeignKey",
    "IntegerField",
    "Manager",
    "ManyToManyField",
    "Model",
    "OneToOneField",
    "QuerySet",
]
