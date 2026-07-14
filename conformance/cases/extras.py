from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from django.utils.translation import gettext_lazy
from typing_extensions import assert_type

from conformance_models.models import Book, User


class BookForm(forms.ModelForm[Book]):
    class Meta:  # conformance: forms.model-forms/model-form-meta expect=pass
        model = Book
        fields = ["title"]


class AlternateBookForm(BookForm):
    class Meta(BookForm.Meta):  # conformance: forms.model-forms/inherited-meta expect=pass
        fields = ["title", "pages"]


assert_type(get_user_model(), type[User])  # conformance: auth.user-model/get-user-model expect=pass
assert_type(HttpRequest().user, User | AnonymousUser)  # conformance: auth.user-model/request-user expect=pass

Book().save(update_fields=["missing"])  # conformance: models.save-update-fields/save-invalid-field expect=fail
Book().save(update_fields=["title"])  # conformance: models.save-update-fields/save-valid-field expect=pass


def request_from_framework() -> HttpRequest:
    return HttpRequest()


HttpRequest().GET["page"] = "1"  # conformance: http.querydict-mutability/fresh-request-write expect=pass


lazy_message = gettext_lazy("hello")
assert_type(lazy_message.upper(), str)  # conformance: typing.lazy-string/string-method expect=pass
assert_type(lazy_message.split(), list[str])  # conformance: typing.lazy-string/string-list-method expect=pass

request_from_framework().GET["page"] = "1"  # conformance: http.querydict-mutability/immutable-querydict-write expect=fail
