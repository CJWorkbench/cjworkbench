from cjworkbench.settings.database import *
from cjworkbench.settings.hardlimits import *
from cjworkbench.settings.logging import *
from cjworkbench.settings.oauth import OAUTH_SERVICES
from cjworkbench.settings.rabbitmq import *
from cjworkbench.settings.s3 import *
from cjworkbench.settings.userlimits import FREE_TIER_USER_LIMITS

# Fetcher uses asyncio because it uses RabbitMQ. But when it comes to the
# database, for all intents and purposes it's single-threaded.
N_SYNC_DATABASE_CONNECTIONS = 1

INSTALLED_APPS = [
    "django.contrib.auth",  # cjwstate.models.workflow imports User
    "django.contrib.contenttypes",
    "django.contrib.sites",
    "cjworkbench",  # UserProfile model, etc.
]

MIDDLEWARE = []

SECRET_KEY = "not-a-web-server"
