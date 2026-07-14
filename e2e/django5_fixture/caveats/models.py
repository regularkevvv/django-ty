from django.db import models


class BrokenLink(models.Model):
    target = models.ForeignKey("missing.App", on_delete=models.CASCADE)


class FirstDuplicate(models.Model):
    author = models.ForeignKey(
        "library.Author",
        on_delete=models.CASCADE,
        related_name="duplicate_books",
    )


class SecondDuplicate(models.Model):
    author = models.ForeignKey(
        "library.Author",
        on_delete=models.CASCADE,
        related_name="duplicate_books",
    )
