"""Static-files app, used in development.

This app serves two purposes:

* In dev mode, it emulates our production static-files server.
* During build, it dumps all files to ./static/ for later upload.

The rules: any request to this server must serve the most up-to-date file
possible.
"""
import os
import os.path

from cjworkbench.settings.util import DJANGO_ROOT

SECRET_KEY = "no-key-because-this-is-dev-mode-only"
DEBUG = True  # log a bit more

# Apps to search for assets. Mimics cjworkbench.settings.INSTALLED_APPS
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.facebook",
    "allauth.socialaccount.providers.google",
]

# Enable middleware+templates to load django.contrib.admin. We need its
# assets. TODO nix django.contrib.admin and home-roll our own tools.
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "staticfilesdev.middleware.cors",  # the only useful middleware
]
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
            ]
        },
    }
]
STATIC_URL = "/static/"  # silence a django runserver warning

# Static files. CSS, JavaScript are bundled by webpack, but fonts, test data,
# images, etc. are not
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "staticfilesdev.finders.LessonSupportDataFinder",
]
STATIC_ROOT = os.path.join(DJANGO_ROOT, "static")  # collectstatic writes here
STATICFILES_DIRS = (
    ("bundles", os.path.join(DJANGO_ROOT, "assets", "bundles")),
    ("fonts", os.path.join(DJANGO_ROOT, "assets", "fonts")),
    ("images", os.path.join(DJANGO_ROOT, "assets", "images")),
)
