from django.db import models


class User(models.Model):
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return str(self.email)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True)
    reputation = models.IntegerField(default=0)

# Create your models here.
