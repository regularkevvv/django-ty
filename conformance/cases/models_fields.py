from datetime import datetime

from typing_extensions import assert_type

from conformance_models.models import Article, Book, BookProxy


assert_type(Book.objects.get(), Book)  # conformance: models.subclass-transform/model-manager-result expect=pass
assert_type(Book(title="Dune").title, str)  # conformance: models.subclass-transform/model-instance-member expect=pass

assert_type(Book().id, int)  # conformance: models.default-primary-key/default-id expect=pass
assert_type(Book().pk, int)  # conformance: models.default-primary-key/default-pk expect=pass

assert_type(Book().title, str)  # conformance: models.field-descriptors/char-read expect=pass
assert_type(Book().pages, int | None)  # conformance: models.field-descriptors/nullable-int-read expect=pass
Book().title = ["Dune"]  # conformance: models.field-descriptors/char-write-rejection expect=fail

Book(title="Dune", pages=412)  # conformance: models.constructor-keywords/valid-keywords expect=pass
Book(title=["Dune"])  # conformance: models.constructor-keywords/invalid-keyword-type expect=fail
Book(unknown_field="x")  # conformance: models.constructor-keywords/unknown-keyword expect=fail

assert_type(Book.objects.create(title="Dune"), Book)  # conformance: models.create-keywords/return-model expect=pass
Article.objects.create(title=["Dune"])  # conformance: models.create-keywords/invalid-keyword-type expect=fail

assert_type(Article().created_at, datetime)  # conformance: models.abstract-proxy-inheritance/abstract-field expect=pass
assert_type(BookProxy().title, str)  # conformance: models.abstract-proxy-inheritance/proxy-field expect=pass

assert_type(Book.Status.DRAFT.label, str)  # conformance: models.choices-enums/choice-label expect=pass
assert_type(Book().get_status_display(), str)  # conformance: models.choices-enums/generated-display expect=pass

assert_type(Book().code, str)  # conformance: models.custom-fields/generic-field-read expect=pass
Book().code = 42  # conformance: models.custom-fields/generic-field-write expect=fail
