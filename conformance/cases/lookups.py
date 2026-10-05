from datetime import date

from conformance_models.models import Article, Author, Book, Category


Category.objects.filter(parent__name__icontains="ada")  # conformance: lookups.field-traversal/related-text-path expect=pass
Category.objects.filter(parent__missing__exact="x")  # conformance: lookups.field-traversal/unknown-related-field expect=fail

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
