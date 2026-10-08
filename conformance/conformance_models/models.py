from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db import models
from django.db.models.signals import post_init, post_save
from django.dispatch import receiver
from typing_extensions import Self


class User(models.Model):
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=120)


class Author(models.Model):
    name = models.CharField(max_length=120)
    age = models.IntegerField(null=True, default=None)


class Tag(models.Model):
    label = models.CharField(max_length=64)


class Category(models.Model):
    name = models.CharField(max_length=80)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, related_name="children")


if TYPE_CHECKING:
    class CodeField(models.Field[str, str]):
        pass
else:
    class CodeField(models.Field):
        def db_type(self, connection: object) -> str:
            return "text"


class BookManager(models.Manager["Book"]):
    def featured_label(self) -> str:
        return "featured"


class Book(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=200)
    pages = models.IntegerField(null=True, default=None)
    published_at = models.DateTimeField(null=True, default=None)
    code = CodeField()
    # ty >= 0.0.82 drops `type[E]` union members (astral-sh/ty#4597); keep
    # `choices=Status` so the plugin sees the enum ref. Revert when fixed.
    status = models.CharField(max_length=20, choices=Status, default=Status.DRAFT)  # ty: ignore[invalid-argument-type]
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name="books",
        related_query_name="authored_book",
    )
    editor = models.OneToOneField(  # conformance: relations.string-settings-targets/settings-field-declaration expect=pass
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="edited_book",
    )
    tags = models.ManyToManyField(Tag, related_name="books")
    objects = BookManager()
    published = BookManager()


class Timestamped(models.Model):
    created_at = models.DateTimeField(default=datetime.now)

    class Meta:
        abstract = True


class Article(Timestamped):
    title = models.CharField(max_length=200)


class BookProxy(Book):
    class Meta:
        proxy = True


class PublishedQuerySet(models.QuerySet["Publication"]):
    def published_only(self) -> Self:
        return self.filter(is_published=True)  # conformance: managers.custom-queryset-methods/queryset-self-return expect=pass

    def score(self) -> int:
        return 1


class Publication(models.Model):
    title = models.CharField(max_length=200)
    is_published = models.BooleanField(default=False)
    objects = PublishedQuerySet.as_manager()


class GeneratedQuerySet(models.QuerySet["GeneratedPublication"]):
    def generated_only(self) -> Self:
        return self.all()  # conformance: managers.from-queryset-as-manager/generated-queryset-self-return expect=pass


GeneratedManager = models.Manager.from_queryset(GeneratedQuerySet)  # conformance: managers.from-queryset-as-manager/generated-manager-class expect=pass


class GeneratedPublication(models.Model):
    title = models.CharField(max_length=200)
    objects = GeneratedManager()


class AutoCounter(models.Model):
    key = models.BigAutoField(primary_key=True)
    label = models.CharField(max_length=64)


class NoSave(models.Model):
    def save(self, *args: object, **kwargs: object) -> None:
        pass


class CustomInit(models.Model):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.pk = None


class CustomLoader(models.Model):
    @classmethod
    def from_db(cls, *args: Any, **kwargs: Any) -> Self:
        return cls()


class SignalInit(models.Model):
    pass


class SignalSave(models.Model):
    pass


@receiver(post_init, sender=SignalInit)
def clear_initialized_id(sender: Any, instance: SignalInit, **kwargs: Any) -> None:
    instance.pk = None


@receiver(post_save, sender=SignalSave)
def clear_saved_id(sender: Any, instance: SignalSave, **kwargs: Any) -> None:
    instance.pk = None


class TagChild(Tag):
    pass


class DatabaseDefaultKey(models.Model):
    id = models.AutoField(primary_key=True, db_default=123)


class SignalAlias(models.Model):
    pass


SignalAliasRef = SignalAlias


@receiver(post_init, sender=SignalAliasRef)
def clear_aliased_sender_id(sender: Any, instance: SignalAlias, **kwargs: Any) -> None:
    instance.pk = None


class StaticSignal(models.Model):
    pass
