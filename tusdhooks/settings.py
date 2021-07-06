from cjworkbench.settings.s3 import *
from cjworkbench.settings.rabbitmq import *
from cjworkbench.settings.database import *
from cjworkbench.settings.debug import DEBUG
from cjworkbench.settings.logging import *
from cjworkbench.settings.userlimits import *
from cjworkbench.settings.hardlimits import *

SECRET_KEY = "internal-only-so-no-secret-key"

INSTALLED_APPS = [
    "django.contrib.auth",  # cjwstate.models.workflow imports User
    "django.contrib.contenttypes",
    "django.contrib.sites",
    "cjworkbench",  # UserProfile model, etc.
    "tusdhooks",
]

MIDDLEWARE = []

ROOT_URLCONF = "tusdhooks.urls"

ALLOWED_HOSTS = ["*"]
