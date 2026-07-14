from django.conf import settings
from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=120)
    age = models.IntegerField(null=True, default=None)


class Tag(models.Model):
    label = models.CharField(max_length=64)


class Category(models.Model):
    name = models.CharField(max_length=80)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        related_name="children",
    )


class BookQuerySet(models.QuerySet["Book", "Book"]):
    pass


class BookManager(models.Manager["Book"]):
    pass


class Book(models.Model):
    title = models.CharField(max_length=200)
    pages = models.IntegerField(null=True, default=None)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books")
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="edited_books",
    )
    category = models.ForeignKey(
        "Category",
        on_delete=models.PROTECT,
        null=True,
        related_name="+",
    )
    tags = models.ManyToManyField("Tag", related_name="books")
    objects = BookManager()
    published = BookManager()

# Create your models here.
