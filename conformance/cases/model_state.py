from django.db.models.expressions import DatabaseDefault
from typing_extensions import assert_type

from conformance_models.models import (
    Article,
    AutoCounter,
    BookProxy,
    CustomInit,
    CustomLoader,
    DatabaseDefaultKey,
    NoSave,
    SignalInit,
    SignalAlias,
    StaticSignal,
    SignalSave,
    Tag,
    TagChild,
)


def loaded() -> None:
    tag = Tag.objects.get(pk=1)
    assert_type(tag.id, int)  # conformance: models.default-primary-key/loaded-id expect=pass
    assert_type(tag.pk, int)  # conformance: models.default-primary-key/loaded-pk expect=pass
    tag = Tag.objects.create(label="new")
    assert_type(tag.id, int)  # conformance: models.default-primary-key/created-id expect=pass
    tag = Tag.objects.all().get(pk=1)
    assert_type(tag.pk, int)  # conformance: models.default-primary-key/queryset-loaded-pk expect=pass


def saved() -> None:
    tag = Tag(label="new")
    tag.save()
    assert_type(tag.id, int)  # conformance: models.default-primary-key/saved-id expect=pass
    assert_type(tag.pk, int)  # conformance: models.default-primary-key/saved-pk expect=pass
    alias = tag
    alias.delete()
    assert_type(tag.id, None)  # conformance: models.default-primary-key/deleted-alias-id expect=pass
    assert_type(alias.pk, None)  # conformance: models.default-primary-key/deleted-alias-pk expect=pass
    tag.save()
    assert_type(tag.pk, int)  # conformance: models.default-primary-key/resaved-pk expect=pass


def branches(condition: bool) -> None:
    tag = Tag(label="branch")
    if condition:
        tag.save()
    assert_type(tag.id, int | None)  # conformance: models.default-primary-key/conditional-save expect=pass
    if condition:
        tag.save()
    else:
        tag.save()
    assert_type(tag.id, int)  # conformance: models.default-primary-key/both-branches-save expect=pass


def skipped(fields: list[str]) -> None:
    tag = Tag(label="skipped")
    tag.save(update_fields=[])
    assert_type(tag.pk, int | None)  # conformance: models.default-primary-key/skipped-save expect=pass
    tag.save(update_fields=fields)
    assert_type(tag.id, int | None)  # conformance: models.default-primary-key/unknown-update-fields expect=pass
    tag.save(update_fields=None)
    assert_type(tag.id, int)  # conformance: models.default-primary-key/full-save expect=pass


def unknown_mutation() -> None:
    tag = Tag.objects.get(pk=1)
    def mutate(value: Tag) -> None:
        value.delete()
    mutate(tag)
    assert_type(tag.id, int | None)  # conformance: models.default-primary-key/unknown-call-invalidates expect=pass


def overridden() -> None:
    tag = NoSave()
    tag.save()
    assert_type(tag.pk, int | None)  # conformance: models.default-primary-key/overridden-save expect=pass


def inherited() -> None:
    article = Article.objects.get(pk=1)
    assert_type(article.pk, int)  # conformance: models.default-primary-key/inherited-loaded-pk expect=pass
    counter = AutoCounter.objects.get(pk=1)
    assert_type(counter.key, int)  # conformance: models.default-primary-key/explicit-auto-loaded expect=pass
    counter.delete()
    assert_type(counter.key, None)  # conformance: models.default-primary-key/explicit-auto-deleted expect=pass
    assert_type(counter.pk, None)  # conformance: models.default-primary-key/explicit-auto-deleted-pk expect=pass


def constructed(identifier: int, nullable: int | None) -> None:
    assert_type(Tag(id=123).id, int)  # conformance: models.default-primary-key/explicit-constructor-id expect=pass
    assert_type(Tag(pk=123).id, int)  # conformance: models.default-primary-key/explicit-constructor-pk expect=pass
    assert_type(Tag(id=identifier).pk, int)  # conformance: models.default-primary-key/typed-constructor-id expect=pass
    assert_type(Tag(id=nullable).pk, int | None)  # conformance: models.default-primary-key/nullable-constructor-id expect=pass
    assert_type(Tag(id=123, pk=None).id, None)  # conformance: models.default-primary-key/constructor-pk-precedence expect=pass
    counter = AutoCounter()
    assert_type(counter.key, None)  # conformance: models.default-primary-key/explicit-auto-unsaved expect=pass
    counter = AutoCounter(key=123)
    assert_type(counter.pk, int)  # conformance: models.default-primary-key/explicit-auto-constructor expect=pass


def custom_lifecycle() -> None:
    custom = CustomInit(id=123)
    assert_type(custom.pk, int | None)  # conformance: models.default-primary-key/custom-initialization expect=pass
    custom_loaded = CustomLoader.objects.get(pk=1)
    assert_type(custom_loaded.pk, int | None)  # conformance: models.default-primary-key/custom-loading expect=pass
    no_save = NoSave.objects.create()
    assert_type(no_save.pk, int | None)  # conformance: models.default-primary-key/create-overridden-save expect=pass


def manual_mutation() -> None:
    tag = Tag.objects.get(pk=1)
    tag.id = None
    assert_type(tag.pk, int | None)  # conformance: models.default-primary-key/id-write-invalidates-pk expect=pass


def row_result() -> None:
    row = Tag.objects.values("id").get()
    assert_type(row["id"], int)  # conformance: models.default-primary-key/values-row-id expect=pass
    counter = AutoCounter.objects.values("key").get()
    assert_type(counter["key"], int)  # conformance: models.default-primary-key/explicit-auto-row expect=pass


def signals() -> None:
    initialized = SignalInit(id=123)
    assert_type(initialized.pk, int | None)  # conformance: models.default-primary-key/post-init-signal expect=pass
    saved = SignalSave()
    saved.save()
    assert_type(saved.pk, int | None)  # conformance: models.default-primary-key/post-save-signal expect=pass


def inheritance_keys() -> None:
    child = TagChild(id=123)
    assert_type(child.pk, int | None)  # conformance: models.default-primary-key/concrete-child-key expect=pass
    proxy = BookProxy(id=123)
    assert_type(proxy.pk, int)  # conformance: models.default-primary-key/proxy-constructor-key expect=pass


def database_default() -> None:
    model = DatabaseDefaultKey()
    assert_type(model.pk, DatabaseDefault)  # conformance: models.default-primary-key/database-default-unsaved expect=pass
    explicit = DatabaseDefaultKey(pk=123)
    assert_type(explicit.pk, int)  # conformance: models.default-primary-key/database-default-explicit expect=pass
    model.save()
    assert_type(model.pk, int)  # conformance: models.default-primary-key/database-default-saved expect=pass


def uncertain_database_default(model: DatabaseDefaultKey, options: dict[str, int]) -> None:
    assert_type(model.pk, int | None | DatabaseDefault)  # conformance: models.default-primary-key/database-default-unknown expect=pass
    unpacked = DatabaseDefaultKey(**options)
    assert_type(unpacked.pk, int | None | DatabaseDefault)  # conformance: models.default-primary-key/database-default-unpacked expect=pass


def aliased_signal_sender() -> None:
    model = SignalAlias(id=123)
    assert_type(model.pk, int | None)  # conformance: models.default-primary-key/aliased-signal-sender expect=pass


def class_signal_handler() -> None:
    model = StaticSignal(id=123)
    assert_type(model.pk, int | None)  # conformance: models.default-primary-key/class-signal-handler expect=pass


def failed_save() -> None:
    model = Tag()
    try:
        model.save(force_update=True)
    except ValueError:
        assert_type(model.pk, int | None)  # conformance: models.default-primary-key/failed-save-handler expect=pass
    assert_type(model.pk, int | None)  # conformance: models.default-primary-key/failed-save-join expect=pass


def rethrown_save() -> None:
    model = Tag()
    try:
        model.save()
    except Exception:
        raise
    assert_type(model.pk, int)  # conformance: models.default-primary-key/rethrown-save-success expect=pass
