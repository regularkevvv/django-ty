from django.db import models


class TextKey(models.Model):
    slug = models.CharField(primary_key=True, max_length=30)


class TextChild(TextKey):
    pass


class UuidKey(models.Model):
    key = models.UUIDField(primary_key=True)


class CodeKey(models.Model):
    code = models.CharField(max_length=30, unique=True)


class Ref(models.Model):
    text = models.ForeignKey(TextKey, on_delete=models.CASCADE)
    uuid = models.ForeignKey(UuidKey, null=True, on_delete=models.CASCADE)
    code = models.ForeignKey(CodeKey, to_field="code", on_delete=models.CASCADE)


class AbstractBase(models.Model):
    zeta = models.CharField(max_length=30)

    class Meta:
        abstract = True


class AbstractChild(AbstractBase):
    alpha = models.IntegerField()


class ProxyText(TextKey):
    class Meta:
        proxy = True


class ExplicitChild(TextKey):
    parent = models.OneToOneField(
        TextKey, parent_link=True, primary_key=True, on_delete=models.CASCADE
    )
    extra = models.IntegerField(default=7)


class LateChild(TextKey):
    extra = models.IntegerField(default=11)
    link = models.OneToOneField(
        TextKey, parent_link=True, primary_key=True, on_delete=models.CASCADE
    )
