from django.apps import AppConfig


class ConformanceModelsConfig(AppConfig):
    name = "conformance_models"

    def ready(self) -> None:
        from . import signals  # noqa: F401 - register model signal receivers
