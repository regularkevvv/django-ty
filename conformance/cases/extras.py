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
def check_framework_user(request: HttpRequest) -> None:
    assert_type(request.user, User | AnonymousUser)  # conformance: auth.user-model/request-user expect=pass

Book(pk=1).save(update_fields=["missing"])  # conformance: models.save-update-fields/save-invalid-field expect=fail
Book(pk=1).save(update_fields=["title"])  # conformance: models.save-update-fields/save-valid-field expect=pass


def write_mutable_copy(request: HttpRequest) -> None:
    request.GET.copy()["page"] = "1"  # conformance: http.querydict-mutability/mutable-copy-write expect=pass


lazy_message = gettext_lazy("hello")
assert_type(lazy_message.upper(), str)  # conformance: typing.lazy-string/string-method expect=pass
assert_type(lazy_message.split(), list[str])  # conformance: typing.lazy-string/string-list-method expect=pass

def write_framework_request(request: HttpRequest) -> None:
    request.GET["page"] = "1"  # conformance: http.querydict-mutability/immutable-querydict-write expect=fail


def write_fresh_get() -> None:
    HttpRequest().GET["page"] = "1"  # conformance: http.querydict-mutability/fresh-get-write expect=pass


def write_fresh_post() -> None:
    HttpRequest().POST["page"] = "1"  # conformance: http.querydict-mutability/fresh-post-write expect=pass


class CustomRequest(HttpRequest):
    custom: str = "hello"


assert_type(CustomRequest(), CustomRequest)  # conformance: http.querydict-mutability/custom-request-type expect=pass
assert_type(CustomRequest().custom, str)  # conformance: http.querydict-mutability/custom-request-attribute expect=pass
