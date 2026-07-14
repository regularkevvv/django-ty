from datetime import datetime

from django.db.models import Prefetch, Value
from typing_extensions import assert_type

from conformance_models.models import (
    Article,
    Book,
    GeneratedPublication,
    GeneratedQuerySet,
    Publication,
    PublishedQuerySet,
    Tag,
)


assert_type(Book.objects.get(), Book)  # conformance: managers.default-manager/default-get expect=pass
assert_type(Book._default_manager.get(), Book)  # conformance: managers.default-manager/default-manager-attribute expect=pass

assert_type(Book.published.get(), Book)  # conformance: managers.declared-manager/declared-get expect=pass
assert_type(Book.published.featured_label(), str)  # conformance: managers.declared-manager/custom-method expect=pass

assert_type(Publication.objects.published_only(), PublishedQuerySet)  # conformance: managers.custom-queryset-methods/copied-chain-method expect=pass
assert_type(Publication.objects.score(), int)  # conformance: managers.custom-queryset-methods/copied-scalar-method expect=pass

assert_type(GeneratedPublication.objects.generated_only(), GeneratedQuerySet)  # conformance: managers.from-queryset-as-manager/from-queryset-method expect=pass
assert_type(GeneratedPublication.objects.get(), GeneratedPublication)  # conformance: managers.from-queryset-as-manager/from-queryset-model expect=pass

assert_type(Book.objects.filter(title="Dune").order_by("title").get(), Book)  # conformance: querysets.chain-preserving-methods/filter-order-get expect=pass
assert_type(Book.objects.none().all().first(), Book | None)  # conformance: querysets.chain-preserving-methods/none-all-first expect=pass

assert_type(Book.objects.get(), Book)  # conformance: querysets.scalar-return-methods/get expect=pass
assert_type(Book.objects.first(), Book | None)  # conformance: querysets.scalar-return-methods/first expect=pass
assert_type(Book.objects.count(), int)  # conformance: querysets.scalar-return-methods/count expect=pass

async def check_async_methods() -> None:
    assert_type(await Book.objects.aget(), Book)  # conformance: querysets.async-return-methods/aget expect=pass
    assert_type(await Book.objects.afirst(), Book | None)  # conformance: querysets.async-return-methods/afirst expect=pass

assert_type(Article.objects.values("title").get()["title"], str)  # conformance: querysets.values/scalar-field expect=pass
assert_type(Article.objects.values("created_at").get()["created_at"], datetime)  # conformance: querysets.values/inherited-field expect=pass

assert_type(Article.objects.values_list("title", flat=True).get(), str)  # conformance: querysets.values-list/flat expect=pass
assert_type(Article.objects.values_list("title", "created_at").get(), tuple[str, datetime])  # conformance: querysets.values-list/tuple expect=pass

Book.objects.annotate(score=Value(1)).get().score  # conformance: querysets.annotate/value-attribute expect=pass
Book.objects.annotate(label=Value("ready")).get().label  # conformance: querysets.annotate/string-attribute expect=pass

assert_type(Book.objects.prefetch_related(Prefetch("tags", Tag.objects.all(), to_attr="loaded_tags")).get().loaded_tags, list[Tag])  # conformance: querysets.prefetch-annotations/to-attr-list expect=pass
assert_type(Book.objects.prefetch_related("tags").get(), Book)  # conformance: querysets.prefetch-annotations/basic-prefetch expect=pass

Book.objects.order_by("missing")  # conformance: querysets.ordering-field-validation/order-by-invalid expect=fail
Book.objects.only("missing")  # conformance: querysets.ordering-field-validation/only-invalid expect=fail

Book.objects.bulk_update([Book()], ["missing"])  # conformance: querysets.bulk-operations/bulk-update-invalid-field expect=fail
Book.objects.bulk_create([Tag()])  # conformance: querysets.bulk-operations/bulk-create-wrong-model expect=fail
