from django.apps import apps
from typing_extensions import assert_type

from conformance_models.models import Book, User

assert_type(apps.get_model("conformance_models.Book"), type[Book])  # conformance: apps.model-registry/qualified-reference expect=pass
assert_type(apps.get_model("conformance_models", "book"), type[Book])  # conformance: apps.model-registry/case-insensitive-reference expect=pass
assert_type(apps.get_model(app_label="conformance_models", model_name="User"), type[User])  # conformance: apps.model-registry/keyword-reference expect=pass
wrong: type[User] = apps.get_model("conformance_models.Book")  # conformance: apps.model-registry/wrong-model expect=fail
