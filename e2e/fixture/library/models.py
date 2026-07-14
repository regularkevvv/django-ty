from django.conf import settings
from django.db import models


class Author(models.Model):
    name = models.CharField()


class Tag(models.Model):
    label = models.CharField()


class Book(models.Model):
    title = models.CharField()
    pages = models.IntegerField(null=True)
    author = models.ForeignKey(Author, models.CASCADE, related_name="books")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, null=True)
    tags = models.ManyToManyField("Tag")
