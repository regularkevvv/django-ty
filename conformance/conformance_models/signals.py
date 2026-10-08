from typing import Any

from django.db.models.signals import post_init
from django.dispatch import receiver

from . import models


class StaticSignalHandlers:
    @staticmethod
    @receiver(post_init, sender=models.StaticSignal)
    def clear_id(sender: Any, instance: models.StaticSignal, **kwargs: Any) -> None:
        instance.pk = None
