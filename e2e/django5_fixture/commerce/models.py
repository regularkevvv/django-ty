from django.conf import settings
from django.db import models

from library.models import Book


class Order(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="orders")
    quantity = models.IntegerField(default=1)
    note = models.TextField(null=True, default=None)


class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")
    external_id = models.CharField(max_length=40)

# Create your models here.
