from django.core.mail.message import EmailAttachment
from django.core.paginator import AsyncPage, AsyncPaginator
from django.core.validators import DomainNameValidator, StepValueValidator
from django.forms.widgets import ColorInput, SearchInput, TelInput
from typing_extensions import assert_type

assert_type(ColorInput().input_type, str)  # modern-api: color-input
assert_type(SearchInput().input_type, str)  # modern-api: search-input
assert_type(TelInput().input_type, str)  # modern-api: telephone-input
assert_type(StepValueValidator(2, offset=1).compare(1, 2), bool)  # modern-api: step-validator
assert_type(DomainNameValidator()("example.com"), None)  # modern-api: domain-validator
assert_type(EmailAttachment("example.txt", b"text", "text/plain").filename, str | None)  # modern-api: attachment

async def pagination(paginator: AsyncPaginator[int]) -> None:
    assert_type(await paginator.acount(), int)  # modern-api: async-count
    assert_type(await paginator.apage(1), AsyncPage[int])  # modern-api: async-page

wrong_widget: int = ColorInput().input_type  # modern-api: invalid-widget-type
wrong_validator: str = StepValueValidator(2).compare(1, 2)  # modern-api: invalid-validator-type
wrong_attachment: int = EmailAttachment("example.txt", b"text", "text/plain").filename  # modern-api: invalid-attachment-type
