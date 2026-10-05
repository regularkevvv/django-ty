from collections.abc import Callable
from datetime import date

from conformance_models.models import Article, Author, Book, Category


Category.objects.filter(parent__name__icontains="ada")  # conformance: lookups.field-traversal/related-text-path expect=pass
Category.objects.filter(parent__missing__exact=1)  # conformance: lookups.field-traversal/unknown-related-field expect=fail

Author.objects.filter(age=Book())  # conformance: lookups.value-validation/integer-exact-wrong-type expect=fail
Author.objects.filter(age__in=1)  # conformance: lookups.value-validation/integer-in-wrong-container expect=fail

Author.objects.get_or_create(name="Ada", defaults={"age": Book()})  # conformance: lookups.creation-defaults/get-or-create-default expect=fail
Author.objects.update_or_create(name="Ada", defaults={"age": Book()})  # conformance: lookups.creation-defaults/update-or-create-default expect=fail

Article.objects.values("missing")  # conformance: lookups.selected-field-validation/values-unknown expect=fail
Article.objects.values_list("missing", flat=True)  # conformance: lookups.selected-field-validation/values-list-unknown expect=fail

Book.objects.filter(title__in="Dune")  # conformance: lookups.value-validation/string-in-lookup expect=pass
Book.objects.filter(title__range="AZ")  # conformance: lookups.value-validation/string-range-lookup expect=pass
Author.objects.get_or_create(name="Grace", defaults={"age": lambda: 43})  # conformance: lookups.creation-defaults/callable-create-default expect=pass
Author.objects.update_or_create(name="Grace", defaults={"age": lambda: 44})  # conformance: lookups.creation-defaults/callable-update-default expect=pass

Author.objects.get_or_create(name="BadCallable", defaults={"age": lambda: Book()})  # conformance: lookups.creation-defaults/callable-invalid-result expect=fail
Book.objects.filter(title=None)  # conformance: lookups.value-validation/null-exact-lookup expect=pass
Book.objects.filter(published_at__year=2026)  # conformance: lookups.value-validation/year-lookup expect=pass
Book.objects.filter(published_at__month=10)  # conformance: lookups.value-validation/month-lookup expect=pass
Book.objects.filter(published_at__day=5)  # conformance: lookups.value-validation/day-lookup expect=pass
Book.objects.filter(published_at__date=date(2026, 10, 5))  # conformance: lookups.value-validation/date-lookup expect=pass

Author.objects.filter(age__in="42")  # conformance: lookups.value-validation/string-integer-in expect=pass
Author.objects.filter(age__in="x2")  # conformance: lookups.value-validation/string-integer-invalid expect=fail
Author.objects.filter(age__range="19")  # conformance: lookups.value-validation/string-integer-range expect=pass


def default_age() -> int:
    return 45


def bad_default_age() -> Book:
    return Book()


typed_age: Callable[[], int] = default_age
typed_bad_age: Callable[[], Book] = bad_default_age
Author.objects.get_or_create(name="Named", defaults={"age": default_age})  # conformance: lookups.creation-defaults/named-callable-create expect=pass
Author.objects.get_or_create(name="Typed", defaults={"age": typed_age})  # conformance: lookups.creation-defaults/typed-callable-create expect=pass
Author.objects.get_or_create(name="BadNamed", defaults={"age": bad_default_age})  # conformance: lookups.creation-defaults/named-callable-invalid expect=fail
Author.objects.get_or_create(name="BadTyped", defaults={"age": typed_bad_age})  # conformance: lookups.creation-defaults/typed-callable-invalid expect=fail
Author.objects.update_or_create(name="Branches", defaults={"age": bad_default_age})  # conformance: lookups.creation-defaults/invalid-existing-defaults expect=fail
Author.objects.get_or_create(name="Mixed", defaults={"name": "Mixed", "age": lambda: 46})  # conformance: lookups.creation-defaults/mixed-literal-callable expect=pass
Book.objects.get_or_create(title="MixedBook", defaults={"title": lambda: "MixedBook", "pages": lambda: 47})  # conformance: lookups.creation-defaults/heterogeneous-callables expect=pass
Author.objects.update_or_create(name="Branches", defaults={"age": default_age}, create_defaults={"age": lambda: 48})  # conformance: lookups.creation-defaults/callable-create-defaults expect=pass
Author.objects.update_or_create(name="BadBranches", defaults={"age": default_age}, create_defaults={"age": bad_default_age})  # conformance: lookups.creation-defaults/invalid-create-defaults expect=fail


async def check_async_defaults() -> None:
    await Author.objects.aget_or_create(name="AsyncCreate", defaults={"age": default_age})  # conformance: lookups.creation-defaults/async-callable-create expect=pass
    await Author.objects.aupdate_or_create(name="AsyncUpdate", defaults={"age": lambda: 49})  # conformance: lookups.creation-defaults/async-callable-update expect=pass
    await Author.objects.aget_or_create(name="AsyncBad", defaults={"age": bad_default_age})  # conformance: lookups.creation-defaults/async-callable-invalid expect=fail
