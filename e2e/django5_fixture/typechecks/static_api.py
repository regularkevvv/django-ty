from django import forms
from django.apps import AppConfig
from django.conf.global_settings import TEMPLATES
from django.core.mail import EmailMessage
from django.http import HttpRequest, HttpResponse, QueryDict
from django.template import Context, Template
from django.urls import URLPattern, path
from django.views.generic import TemplateView


class StaticApiConfig(AppConfig):
    name = "static_api"


class ContactForm(forms.Form):
    email = forms.EmailField()


def contact(request: HttpRequest) -> HttpResponse:
    data = QueryDict("email=ada%40example.com")
    message = EmailMessage(subject="Hello", body=data["email"], to=["ada@example.com"])
    rendered = Template("{{ greeting }}").render(Context({"greeting": "Hello"}))
    return HttpResponse(rendered + message.subject)


routes: list[URLPattern] = [path("contact/", contact)]
view: type[TemplateView] = TemplateView
template_backend: str = TEMPLATES[0]["BACKEND"]
