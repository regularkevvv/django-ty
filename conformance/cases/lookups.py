from conformance_models.models import Article, Author, Book, Category


Category.objects.filter(parent__name__icontains="ada")  # conformance: lookups.field-traversal/related-text-path expect=pass
Category.objects.filter(parent__missing__exact="x")  # conformance: lookups.field-traversal/unknown-related-field expect=fail

Author.objects.filter(age=Book())  # conformance: lookups.value-validation/integer-exact-wrong-type expect=fail
Author.objects.filter(age__in=1)  # conformance: lookups.value-validation/integer-in-wrong-container expect=fail

Author.objects.get_or_create(name="Ada", defaults={"age": Book()})  # conformance: lookups.creation-defaults/get-or-create-default expect=fail
Author.objects.update_or_create(name="Ada", defaults={"age": Book()})  # conformance: lookups.creation-defaults/update-or-create-default expect=fail

Article.objects.values("missing")  # conformance: lookups.selected-field-validation/values-unknown expect=fail
Article.objects.values_list("missing", flat=True)  # conformance: lookups.selected-field-validation/values-list-unknown expect=fail
