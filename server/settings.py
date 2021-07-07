import os
import os.path

from dotenv import load_dotenv

from cjworkbench.i18n import default_locale, supported_locales

from cjworkbench.settings.database import *
from cjworkbench.settings.debug import DEBUG, I_AM_TESTING
from cjworkbench.settings.hardlimits import *
from cjworkbench.settings.logging import *
from cjworkbench.settings.oauth import OAUTH_SERVICES
from cjworkbench.settings.rabbitmq import *  # incl. RABBITMQ_HOST
from cjworkbench.settings.smtp import *
from cjworkbench.settings.s3 import *
from cjworkbench.settings.userlimits import FREE_TIER_USER_LIMITS
from cjworkbench.settings.util import DJANGO_ROOT, FalsyStrings

SITE_ID = 1  # for allauth
ALLOWED_HOSTS = ["*"]
SECRET_KEY = os.environ["CJW_SECRET_KEY"]

if "HTTPS" in os.environ and os.environ["HTTPS"] not in FalsyStrings:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = bool(os.environ["CJW_FORCE_SSL"])

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
    "allauth.socialaccount",  # providers are inserted below depending on env
    "cjworkbench",
    "server",  # templatetags
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "cjworkbench.middleware.i18n.SetCurrentLocaleMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

SESSION_ENGINE = "django.contrib.sessions.backends.db"

ROOT_URLCONF = "cjworkbench.urls"

# EMAIL_BACKEND (copied in renderer/settings.py)
if DEBUG or os.environ.get("CJW_MOCK_EMAIL"):
    EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
    EMAIL_FILE_PATH = os.path.join(DJANGO_ROOT, "local_mail")
else:
    # Default EMAIL_BACKEND => SMTP
    EMAIL_HOST = os.environ["CJW_SMTP_HOST"]
    EMAIL_HOST_USER = os.environ["CJW_SMTP_USER"]
    EMAIL_HOST_PASSWORD = os.environ["CJW_SMTP_PASSWORD"]
    EMAIL_PORT = int(os.environ["CJW_SMTP_PORT"])
    EMAIL_USE_TLS = os.environ["CJW_SMTP_USE_TLS"] not in FalsyStrings

# For django-allauth
ACCOUNT_ADAPTER = "cjworkbench.accounts.adapter.AccountAdapter"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_USER_DISPLAY = lambda user: user.email
ACCOUNT_SIGNUP_FORM_CLASS = "cjworkbench.accounts.forms.WorkbenchSignupForm"
SOCIALACCOUNT_ADAPTER = "cjworkbench.socialaccounts.adapter.SocialAccountAdapter"
SOCIALACCOUNT_EMAIL_VERIFICATION = False
SOCIALACCOUNT_FORMS = {
    "signup": "cjworkbench.socialaccounts.forms.WorkbenchSocialaccountSignupForm"
}
SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_PROVIDERS = {}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "cjworkbench.i18n.templates.context_processor",
            ]
        },
    }
]

ASGI_APPLICATION = "cjworkbench.asgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/account/login"
LOGIN_REDIRECT_URL = "/workflows"

# TODO nix USE_I18N
#
# Currently, we only use it for Django login-form error translation. We have our
# own i18n system for everything else. [2020-12-22] Django + async views won't
# work with i18n, and we must avoid touching Django's `activate()` in async
# views.
LANGUAGE_CODE = default_locale
USE_I18N = True
USE_L10N = True

LANGUAGES = [(locale, locale) for locale in supported_locales]

LOCALE_PATHS = (os.path.join(DJANGO_ROOT, "assets", "locale"),)

# We break with Django tradition here and serve files from a different URL
# even in DEBUG mode. Anything else would be obfuscation.
STATIC_URL = os.environ.get("STATIC_URL", "http://localhost:8003/")

AUTHENTICATION_BACKENDS = ["allauth.account.auth_backends.AuthenticationBackend"]

# Stripe is configured via environment variables; but in dev mode, a file
# "stripe.json" can serve as fallback.
try:
    load_dotenv(os.path.join(DJANGO_ROOT, "stripe.env"))
except FileNotFoundError:
    # This is normal
    pass

if "STRIPE_API_KEY" in os.environ:
    STRIPE_API_KEY = os.environ["STRIPE_API_KEY"]
    STRIPE_PUBLIC_API_KEY = os.environ["STRIPE_PUBLIC_API_KEY"]
    STRIPE_WEBHOOK_SIGNING_SECRET = os.environ["STRIPE_WEBHOOK_SIGNING_SECRET"]


INTERCOM_APP_ID = os.environ.get("CJW_INTERCOM_APP_ID")
INTERCOM_IDENTITY_VERIFICATION_SECRET = os.environ.get(
    "CJW_INTERCOM_IDENTITY_VERIFICATION_SECRET"
)

# Knowledge base root url, used as a default for missing help links
KB_ROOT_URL = "http://help.workbenchdata.com/"

TUS_CREATE_UPLOAD_URL = os.environ.get("TUS_CREATE_UPLOAD_URL", "")
TUS_EXTERNAL_URL_PREFIX_OVERRIDE = os.environ.get(
    "TUS_EXTERNAL_URL_PREFIX_OVERRIDE", TUS_CREATE_UPLOAD_URL
)

LESSON_FILES_URL = "https://static.workbenchdata.com"
"""URL where we publish data for users to fetch in lessons.

[2019-11-12] Currently, this is in the production static-files URL. TODO move
it to a new bucket, because developers must write to the bucket before
deploying code that depends on it.

Why not use an environment-specific url, like STATIC_URL? Because our network
sandbox forbids fetcher modules from accessing private-use IP addresses. We
don't use internal resolvers (e.g., Docker DNS, Docker-managed /etc/hosts) and
we firewall internal IP addresses (e.g., s3, localhost). Dev,
integration-test and production all have different network setups, and we'd
need three different codepaths to make environment-specific URLs work.
"""

BIG_TABLE_ROWS_PER_TILE = 100
"""Number of rows fetched in a single request of a table.

A smaller number means more HTTP requests are needed to fill a table. A larger
number means each request returns more data -- and React renders are slower.
"""

BIG_TABLE_COLUMNS_PER_TILE = 20
"""Number of rows fetched in a single request of a table.

A smaller number means more HTTP requests are needed to fill a table. A larger
number means each request returns more data -- and React renders are slower.
"""

if "google" in OAUTH_SERVICES:
    INSTALLED_APPS.insert(
        INSTALLED_APPS.index("allauth.socialaccount") + 1,
        "allauth.socialaccount.providers.google",
    )
    SOCIALACCOUNT_PROVIDERS["google"] = {
        "APP": dict(
            client_id=OAUTH_SERVICES["google"]["client_id"],
            secret=OAUTH_SERVICES["google"]["client_secret"],
            key="",
        )
    }

if "CJW_FACEBOOK_CLIENT_ID" in os.environ:
    INSTALLED_APPS.insert(
        INSTALLED_APPS.index("allauth.socialaccount") + 1,
        "allauth.socialaccount.providers.facebook",  # before Google
    )
    SOCIALACCOUNT_PROVIDERS["facebook"] = {
        "APP": dict(
            client_id=os.environ["CJW_FACEBOOK_CLIENT_ID"],
            secret=os.environ["CJW_FACEBOOK_SECRET"],
            key="",
        )
    }

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_rabbitmq.core.RabbitmqChannelLayer",
        "CONFIG": {"host": RABBITMQ_HOST, "local_capacity": 2000},
    }
}
