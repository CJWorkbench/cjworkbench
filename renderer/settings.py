import os

from cjworkbench.settings.database import *
from cjworkbench.settings.logging import *
from cjworkbench.settings.rabbitmq import *
from cjworkbench.settings.smtp import *
from cjworkbench.settings.s3 import *

SITE_ID = 1  # for finding domain name when sending emails

# Renderer uses asyncio because it uses RabbitMQ. But when it comes to the
# database, for all intents and purposes it's single-threaded.
N_SYNC_DATABASE_CONNECTIONS = 1

INSTALLED_APPS = [
    "django.contrib.auth",  # cjwstate.models.workflow imports User
    "django.contrib.contenttypes",
    "django.contrib.sites",
    "cjworkbench",  # Workflow model, etc.
]

MIDDLEWARE = []

SECRET_KEY = "not-a-web-server"

# TEMPLATES for email notifications
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["/app/renderer/templates"],
    }
]

API_URL = os.environ["CJW_API_URL"]
"""Where the API server is, from users' perspective.

For example: https://api.workbenchdata.com

The renderer does not interact with the API server; but it writes its URL into
datapackages.
"""
