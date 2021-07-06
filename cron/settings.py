from cjworkbench.settings.database import *
from cjworkbench.settings.logging import *
from cjworkbench.settings.rabbitmq import *

INSTALLED_APPS = [
    "django.contrib.auth",  # cjwstate.models.workflow imports User
    "django.contrib.contenttypes",
    "cjworkbench",
]

SECRET_KEY = "not-a-web-server"
