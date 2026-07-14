from typing import Any

from django.conf import settings
from django.db import models
from typing_extensions import assert_type

from conformance_models.models import Book


assert_type(settings.SITE_NAME, str)  # conformance: settings.project-settings-types/custom-setting expect=pass
assert_type(settings.AUTH_USER_MODEL, str)  # conformance: settings.project-settings-types/auth-model-setting expect=pass

title_field: models.CharField[Any, Any] = Book._meta.get_field("title")  # conformance: metadata.get-field/known-field expect=pass
Book._meta.get_field("missing")  # conformance: metadata.get-field/unknown-field expect=fail
