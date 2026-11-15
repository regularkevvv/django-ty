from django.db import models
class Implicit(models.Model):
    title=models.CharField(max_length=20)
    class Meta: app_label="probe"
class Explicit(models.Model):
    id=models.AutoField(primary_key=True)
    class Meta: app_label="probe"
class Custom(models.Model):
    slug=models.CharField(max_length=20,primary_key=True)
    class Meta: app_label="probe"
