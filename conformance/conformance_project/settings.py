SECRET_KEY = "django-ty-conformance"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "conformance_models",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
AUTH_USER_MODEL = "conformance_models.User"
SITE_NAME = "Django ty conformance"
