from cjworkbench.settings.database import *
from cjworkbench.settings.logging import *
from cjworkbench.settings.s3 import *  # to delete files associated with workflows
from cjworkbench.settings.userlimits import *  # how many days to delete

INSTALLED_APPS = [
    "django.contrib.auth",  # cjwstate.models.workflow imports User
    "django.contrib.contenttypes",
    "cjworkbench",
]

SECRET_KEY = "not-a-web-server"
