#!/usr/bin/env python3
"""Check documented Django behavior independently of either type checker."""

from __future__ import annotations

import asyncio
from datetime import date
import tempfile
import importlib.metadata
import json
import os
from pathlib import Path
import sys


def check() -> dict:
    with tempfile.TemporaryDirectory(prefix="django-ty-runtime-") as directory:
        return check_database(Path(directory) / "contracts.sqlite3")


def check_database(database: Path) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "conformance"))
    os.environ["DJANGO_SETTINGS_MODULE"] = "conformance_project.settings"
    import django

    from django.conf import settings

    settings.DATABASES["default"]["NAME"] = str(database)
    django.setup()
    from django.apps import apps
    from django.core.exceptions import FieldDoesNotExist, FieldError
    from django.db import connection
    from django.db.models import Prefetch
    from django.http import HttpRequest
    from conformance_models.models import (
        Article,
        AutoCounter,
        CustomInit,
        CustomLoader,
        DatabaseDefaultKey,
        NoSave,
        SignalInit,
        SignalAlias,
        StaticSignal,
        SignalSave,
        Author,
        Book,
        Category,
        Publication,
        PublishedQuerySet,
        Tag,
        TagChild,
        BookProxy,
        User,
    )

    with connection.schema_editor() as editor:
        for model in apps.get_models():
            if not model._meta.proxy:
                editor.create_model(model)
    author = Author.objects.create(name="Seed", age=42)
    book = Book.objects.create(title="D", author=author, code="code")
    tag = Tag.objects.create(label="tag")
    book.tags.add(tag)
    observed = {}

    def equal(name, actual, expected):
        if actual != expected:
            raise AssertionError(f"{name}: {actual!r} != {expected!r}")
        observed[name] = {"passed": True, "observed": str(actual)}

    def rejected(name, operation, exceptions):
        try:
            operation()
        except exceptions as error:
            observed[name] = {"passed": True, "exception": type(error).__name__}
        else:
            raise AssertionError(f"{name}: invalid input was accepted")

    from django.db.models.expressions import DatabaseDefault
    defaulted = DatabaseDefaultKey()
    equal("state-database-default", isinstance(defaulted.pk, DatabaseDefault), True)
    equal("state-database-default-explicit", DatabaseDefaultKey(pk=123).pk, 123)
    defaulted.save()
    equal("state-database-default-saved", isinstance(defaulted.pk, int), True)
    equal("state-concrete-child", (TagChild(id=123).id, TagChild(id=123).pk), (123, None))
    equal("state-proxy-key", BookProxy(id=123).pk, 123)
    failed = Tag()
    rejected("state-failed-save", lambda: failed.save(force_update=True), ValueError)
    if failed.pk is not None:
        raise AssertionError("failed forced update established an ID")
    equal("state-class-signal", StaticSignal(id=123).pk is None, True)
    equal("state-signal-alias", SignalAlias(id=123).pk is None, True)
    equal("state-signal-init", SignalInit(id=123).pk is None, True)
    signal_saved = SignalSave()
    signal_saved.save()
    equal("state-signal-save", signal_saved.pk is None, True)
    equal("state-custom-init", CustomInit(id=123).pk is None, True)
    custom_loader = CustomLoader.objects.create()
    equal("state-custom-loader", CustomLoader.objects.get(pk=custom_loader.pk).pk is None, True)
    equal("state-create-overridden-save", NoSave.objects.create().pk is None, True)
    branch_states = []
    for condition in [False, True]:
        branch_tag = Tag(label="branch")
        if condition:
            branch_tag.save()
        branch_states.append(branch_tag.pk is not None)
    equal("state-conditional-save", branch_states, [False, True])
    equal("state-constructor-nullable", Tag(id=None).pk is None, True)
    equal("state-constructor-precedence", Tag(id=123, pk=None).id is None, True)
    equal("state-explicit-auto-unsaved", AutoCounter().key is None, True)
    state_tag = Tag(label="state")
    state_tag.save(update_fields=[])
    equal("state-skipped-save", state_tag.pk is None, True)
    state_tag.save()
    equal("state-save", (isinstance(state_tag.id, int), state_tag.id == state_tag.pk), (True, True))
    equal("state-loaded", isinstance(Tag.objects.get(pk=state_tag.pk).id, int), True)
    manual = Tag.objects.get(pk=state_tag.pk)
    manual.id = None
    equal("state-id-write", manual.pk is None, True)
    mutated = Tag.objects.get(pk=state_tag.pk)
    def mutate(value):
        value.id = None
    mutate(mutated)
    equal("state-unknown-call", mutated.pk is None, True)
    alias = state_tag
    alias.delete()
    equal("state-delete-alias", (state_tag.id, state_tag.pk, alias.pk), (None, None, None))
    state_tag.save()
    equal("state-resave", isinstance(state_tag.pk, int), True)
    overridden = NoSave()
    overridden.save()
    equal("state-overridden-save", overridden.pk is None, True)
    counter = AutoCounter.objects.create(label="auto")
    equal("state-explicit-auto", isinstance(counter.key, int) and counter.pk == counter.key, True)
    counter.delete()
    equal("state-explicit-auto-delete", (counter.key, counter.pk), (None, None))
    from django.utils import timezone
    article = Article.objects.create(title="inherited", created_at=timezone.now())
    equal("state-inherited", isinstance(Article.objects.get(pk=article.pk).pk, int), True)
    equal("unsaved-auto-id", Book().id is None, True)
    equal("unsaved-auto-pk", Book().pk is None, True)
    equal("constructor-pk", Book(pk=1).pk, 1)
    equal("constructor-id", Book(id=1).id, 1)
    equal("constructor-relation-id", Book(author_id=author.pk).author_id, author.pk)
    equal("constructor-null-pk", Book(pk=None).pk is None, True)
    equal("registry-qualified", apps.get_model("conformance_models.Book") is Book, True)
    equal(
        "registry-case-insensitive",
        apps.get_model("conformance_models", "book") is Book,
        True,
    )
    equal(
        "registry-keywords",
        apps.get_model(app_label="conformance_models", model_name="User") is User,
        True,
    )
    equal(
        "registry-wrong-model", apps.get_model("conformance_models.Book") is User, False
    )
    rejected(
        "save-invalid-field", lambda: book.save(update_fields=["missing"]), ValueError
    )
    book.title = "D"
    book.save(update_fields=["title"])
    equal("save-valid-field", Book.objects.get(pk=book.pk).title, "D")
    rejected(
        "unknown-related-field",
        lambda: Category.objects.filter(parent__missing__exact=1),
        FieldError,
    )
    rejected(
        "integer-wrong-type",
        lambda: Author.objects.filter(age=Book()),
        (TypeError, ValueError),
    )
    rejected(
        "integer-in-wrong-container",
        lambda: Author.objects.filter(age__in=1),
        TypeError,
    )
    rejected(
        "get-or-create-default",
        lambda: Author.objects.get_or_create(
            name="InvalidCreate", defaults={"age": Book()}
        ),
        (TypeError, ValueError),
    )
    rejected(
        "update-or-create-default",
        lambda: Author.objects.update_or_create(
            name="InvalidUpdate", defaults={"age": Book()}
        ),
        (TypeError, ValueError),
    )
    equal(
        "copied-chain-method",
        isinstance(Publication.objects.published_only(), PublishedQuerySet),
        True,
    )
    equal("copied-scalar-method", Publication.objects.score(), 1)
    loaded = (
        Book.objects.prefetch_related(
            Prefetch("tags", Tag.objects.all(), to_attr="loaded_tags")
        )
        .get(pk=book.pk)
        .loaded_tags
    )
    equal(
        "prefetch-list",
        isinstance(loaded, list) and len(loaded) == 1 and isinstance(loaded[0], Tag),
        True,
    )
    rejected("order-by-invalid", lambda: Book.objects.order_by("missing"), FieldError)
    rejected(
        "only-invalid",
        lambda: str(Book.objects.only("missing").query),
        (FieldError, FieldDoesNotExist),
    )
    rejected(
        "bulk-update-invalid-field",
        lambda: Book.objects.bulk_update([book], ["missing"]),
        FieldDoesNotExist,
    )
    rejected(
        "bulk-create-wrong-model",
        lambda: Book.objects.bulk_create([Tag(label="other")]),
        (AttributeError, TypeError, ValueError),
    )
    for attribute in ("GET", "POST"):
        querydict = getattr(HttpRequest(), attribute)
        querydict["page"] = "1"
        equal("fresh-request-" + attribute.lower(), querydict["page"], "1")
    equal(
        "string-in-lookup",
        list(Book.objects.filter(title__in="Dune").values_list("title", flat=True)),
        ["D"],
    )
    equal(
        "string-range-lookup",
        list(Book.objects.filter(title__range="AZ").values_list("title", flat=True)),
        ["D"],
    )

    class CustomRequest(HttpRequest):
        custom: str = "hello"

    equal("custom-request-type", type(CustomRequest()) is CustomRequest, True)
    equal("custom-request-attribute", CustomRequest().custom, "hello")

    def default_age() -> int:
        return 45

    def bad_default_age() -> Book:
        return Book()

    from collections.abc import Callable

    typed_age: Callable[[], int] = default_age
    typed_bad_age: Callable[[], Book] = bad_default_age
    rejected(
        "typed-callable-invalid",
        lambda: Author.objects.get_or_create(
            name="BadTyped", defaults={"age": typed_bad_age}
        ),
        (TypeError, ValueError),
    )
    for proof, name, value in [
        ("named-callable-create", "Named", default_age),
        ("typed-callable-create", "Typed", typed_age),
    ]:
        named, _ = Author.objects.get_or_create(name=name, defaults={"age": value})
        equal(proof, named.age, 45)
    rejected(
        "named-callable-invalid",
        lambda: Author.objects.get_or_create(
            name="BadNamed", defaults={"age": bad_default_age}
        ),
        (TypeError, ValueError),
    )
    mixed, _ = Author.objects.get_or_create(
        name="Mixed", defaults={"name": "Mixed", "age": lambda: 46}
    )
    equal("mixed-literal-callable", (mixed.name, mixed.age), ("Mixed", 46))
    mixed_book, _ = Book.objects.get_or_create(
        title="MixedBook",
        defaults={
            "title": lambda: "MixedBook",
            "pages": lambda: 47,
            "author_id": author.pk,
        },
    )
    equal(
        "heterogeneous-callables",
        (mixed_book.title, mixed_book.pages),
        ("MixedBook", 47),
    )
    branch, created = Author.objects.update_or_create(
        name="Branches",
        defaults={"age": default_age},
        create_defaults={"age": lambda: 48},
    )
    equal("callable-create-defaults", (created, branch.age), (True, 48))
    branch, created = Author.objects.update_or_create(
        name="Branches",
        defaults={"age": default_age},
        create_defaults={"age": lambda: 48},
    )
    equal("callable-existing-defaults", (created, branch.age), (False, 45))
    rejected(
        "invalid-create-defaults",
        lambda: Author.objects.update_or_create(
            name="BadBranches", create_defaults={"age": lambda: Book()}
        ),
        (TypeError, ValueError),
    )
    rejected(
        "invalid-existing-defaults",
        lambda: Author.objects.update_or_create(
            name="Branches", defaults={"age": lambda: Book()}
        ),
        (TypeError, ValueError),
    )

    created, _ = Author.objects.get_or_create(
        name="CallableCreate", defaults={"age": lambda: 43}
    )
    equal("callable-create-default", created.age, 43)
    updated, _ = Author.objects.update_or_create(
        name="CallableUpdate", defaults={"age": lambda: 44}
    )
    equal("callable-update-default", updated.age, 44)
    rejected(
        "callable-invalid-result",
        lambda: Author.objects.get_or_create(
            name="BadCallable", defaults={"age": lambda: Book()}
        ),
        (TypeError, ValueError),
    )

    async def check_async_defaults() -> None:
        async_created, _ = await Author.objects.aget_or_create(
            name="AsyncCreate", defaults={"age": default_age}
        )
        equal("async-callable-create", async_created.age, 45)
        async_updated, _ = await Author.objects.aupdate_or_create(
            name="AsyncUpdate", defaults={"age": lambda: 49}
        )
        equal("async-callable-update", async_updated.age, 49)
        try:
            await Author.objects.aget_or_create(
                name="AsyncBad", defaults={"age": bad_default_age}
            )
        except (TypeError, ValueError) as error:
            observed["async-callable-invalid"] = {
                "passed": True,
                "exception": type(error).__name__,
            }
        else:
            raise AssertionError("async-callable-invalid: invalid input was accepted")

    asyncio.run(check_async_defaults())
    equal("null-exact-lookup", Book.objects.filter(title=None).exists(), False)
    equal("year-lookup", Book.objects.filter(published_at__year=2026).exists(), False)
    equal("month-lookup", Book.objects.filter(published_at__month=10).exists(), False)
    equal("day-lookup", Book.objects.filter(published_at__day=5).exists(), False)
    equal(
        "date-lookup",
        Book.objects.filter(published_at__date=date(2026, 10, 5)).exists(),
        False,
    )
    equal("unsaved-relation-id", Book().author_id is None, True)
    equal("string-integer-in", Author.objects.filter(age__in="42").count(), 0)
    rejected(
        "string-integer-invalid",
        lambda: Author.objects.filter(age__in="x2"),
        ValueError,
    )
    equal("string-integer-range", Author.objects.filter(age__range="19").count(), 0)
    return {"django": importlib.metadata.version("Django"), "cases": observed}


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
