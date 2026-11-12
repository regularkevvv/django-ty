from typing import assert_type
from uuid import UUID

from primaryapp.models import (
    AbstractChild,
    ExplicitChild,
    LateChild,
    ProxyText,
    Ref,
    TextChild,
    TextKey,
    UuidKey,
)

valid_text: str | None = (
    Ref().text_id
)  # conformance: relations.foreign-key-one-to-one/custom-key-01 expect=pass
wrong_text: int | None = (
    Ref().text_id
)  # conformance: relations.foreign-key-one-to-one/custom-key-02 expect=fail
Ref(
    text_id="slug"
)  # conformance: relations.foreign-key-one-to-one/custom-key-03 expect=pass
Ref(
    text_id=1
)  # conformance: relations.foreign-key-one-to-one/custom-key-04 expect=fail
Ref.objects.filter(
    text_id="slug"
)  # conformance: relations.foreign-key-one-to-one/custom-key-05 expect=pass
Ref.objects.filter(
    text_id=1
)  # conformance: relations.foreign-key-one-to-one/custom-key-06 expect=fail
assert_type(
    Ref.objects.values("text_id").get()["text_id"], str
)  # conformance: relations.foreign-key-one-to-one/custom-key-07 expect=pass
valid_uuid: UUID | None = (
    Ref().uuid_id
)  # conformance: relations.foreign-key-one-to-one/custom-key-08 expect=pass
wrong_uuid: int | None = (
    Ref().uuid_id
)  # conformance: relations.foreign-key-one-to-one/custom-key-09 expect=fail
Ref(
    uuid_id=UUID(int=1)
)  # conformance: relations.foreign-key-one-to-one/custom-key-10 expect=pass
Ref(
    uuid_id=1
)  # conformance: relations.foreign-key-one-to-one/custom-key-11 expect=fail
valid_code: str | None = (
    Ref().code_id
)  # conformance: relations.foreign-key-one-to-one/custom-key-12 expect=pass
wrong_code: int | None = (
    Ref().code_id
)  # conformance: relations.foreign-key-one-to-one/custom-key-13 expect=fail
Ref(
    code_id="code"
)  # conformance: relations.foreign-key-one-to-one/custom-key-14 expect=pass
Ref(
    code_id=1
)  # conformance: relations.foreign-key-one-to-one/custom-key-15 expect=fail
Ref.objects.filter(
    code_id="code"
)  # conformance: relations.foreign-key-one-to-one/custom-key-16 expect=pass
Ref.objects.filter(
    code_id=1
)  # conformance: relations.foreign-key-one-to-one/custom-key-17 expect=fail
assert_type(
    Ref.objects.values("code_id").get()["code_id"], str
)  # conformance: relations.foreign-key-one-to-one/custom-key-18 expect=pass
Ref(
    text=TextKey(slug="slug")
)  # conformance: relations.foreign-key-one-to-one/custom-key-19 expect=pass
Ref(text=1)  # conformance: relations.foreign-key-one-to-one/custom-key-20 expect=fail
reference = Ref()
reference.text = (
    1  # conformance: relations.foreign-key-one-to-one/custom-key-21 expect=fail
)
Ref.objects.filter(
    text="slug"
)  # conformance: relations.foreign-key-one-to-one/custom-key-22 expect=pass
Ref.objects.filter(
    code="code"
)  # conformance: relations.foreign-key-one-to-one/custom-key-23 expect=pass
assert_type(
    Ref.objects.values("text").get()["text"], str
)  # conformance: relations.foreign-key-one-to-one/custom-key-24 expect=pass
assert_type(
    Ref.objects.values("code").get()["code"], str
)  # conformance: relations.foreign-key-one-to-one/custom-key-25 expect=pass
assert_type(
    Ref.objects.values_list("text", "code").get(), tuple[str, str]
)  # conformance: relations.foreign-key-one-to-one/custom-key-26 expect=pass
assert_type(
    Ref.objects.values_list("text", flat=True).get(), str
)  # conformance: relations.foreign-key-one-to-one/custom-key-27 expect=pass
assert_type(
    Ref.objects.values("text__slug").get()["text__slug"], str
)  # conformance: relations.foreign-key-one-to-one/custom-key-28 expect=pass
assert_type(
    Ref.objects.values("uuid").get()["uuid"], UUID | None
)  # conformance: relations.foreign-key-one-to-one/custom-key-29 expect=pass
assert_type(
    Ref.objects.values("uuid__key").get()["uuid__key"], UUID | None
)  # conformance: relations.foreign-key-one-to-one/custom-key-30 expect=pass
assert_type(
    Ref.objects.values_list("uuid__key", flat=True).get(), UUID | None
)  # conformance: relations.foreign-key-one-to-one/custom-key-31 expect=pass

Ref.objects.filter(
    text=TextChild(slug="child")
)  # conformance: relations.foreign-key-one-to-one/custom-key-32 expect=pass
Ref.objects.filter(
    text__exact=TextChild(slug="child")
)  # conformance: relations.foreign-key-one-to-one/custom-key-33 expect=pass
Ref.objects.filter(
    text=UuidKey(key=UUID(int=1))
)  # conformance: relations.foreign-key-one-to-one/custom-key-34 expect=fail
Ref(
    text=TextChild(slug="child")
)  # conformance: relations.foreign-key-one-to-one/custom-key-35 expect=pass
reference.text = TextChild(
    slug="child"
)  # conformance: relations.foreign-key-one-to-one/custom-key-36 expect=pass


assert_type(
    Ref.objects.values_list().get(), tuple[int, str, UUID | None, str]
)  # conformance: querysets.values-values-list/default-row-01 expect=pass
assert_type(
    Ref.objects.values_list(flat=True).get(), int
)  # conformance: querysets.values-values-list/default-row-02 expect=pass
Ref.objects.values().get()[
    "pk"
]  # conformance: querysets.values-values-list/default-row-03 expect=fail
Ref.objects.values().get()[
    "text"
]  # conformance: querysets.values-values-list/default-row-04 expect=fail
assert_type(
    Ref.objects.values_list(named=True).get().text_id, str
)  # conformance: querysets.values-values-list/default-row-05 expect=pass
Ref.objects.values_list(
    named=True
).get().pk  # conformance: querysets.values-values-list/default-row-06 expect=fail
assert_type(
    TextKey.objects.values_list().get(), tuple[str]
)  # conformance: querysets.values-values-list/default-row-07 expect=pass
assert_type(
    TextChild.objects.values_list().get(), tuple[str, str]
)  # conformance: querysets.values-values-list/default-row-08 expect=pass

assert_type(
    AbstractChild.objects.values_list().get(), tuple[int, str, int]
)  # conformance: querysets.values-values-list/default-row-09 expect=pass
assert_type(
    ProxyText.objects.values_list().get(), tuple[str]
)  # conformance: querysets.values-values-list/default-row-10 expect=pass
assert_type(
    ExplicitChild.objects.values_list().get(), tuple[str, str, int]
)  # conformance: querysets.values-values-list/default-row-11 expect=pass
ExplicitChild.objects.values().get()[
    "textkey_ptr_id"
]  # conformance: querysets.values-values-list/default-row-12 expect=fail
assert_type(
    ExplicitChild.objects.values_list(named=True).get().parent_id, str
)  # conformance: querysets.values-values-list/default-row-13 expect=pass
AbstractChild.objects.values().get()[
    "pk"
]  # conformance: querysets.values-values-list/default-row-14 expect=fail

assert_type(
    LateChild.objects.values_list().get(), tuple[str, int, str]
)  # conformance: querysets.values-values-list/default-row-15 expect=pass
assert_type(
    LateChild.objects.values_list(named=True).get().link_id, str
)  # conformance: querysets.values-values-list/default-row-16 expect=pass
