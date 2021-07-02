from cjworkbench.settings import (
    AWS_S3_ENDPOINT,
    DATABASES,
    DEBUG,
    DJANGO_ROOT,
    FREE_TIER_USER_LIMITS,
    LOGGING,
    MAX_BYTES_FILES_PER_STEP,
    MAX_N_FILES_PER_STEP,
    MIGRATION_MODULES,
    N_SYNC_DATABASE_CONNECTIONS,
    RABBITMQ_HOST,
    S3_BUCKET_NAME_PATTERN,
    SECRET_KEY,
    TIME_ZONE,
)

INSTALLED_APPS = [
    "django.contrib.auth",  # cjwstate.models.workflow imports User
    "django.contrib.contenttypes",
    "django.contrib.sites",
    "cjworkbench",  # UserProfile model, etc.
    "tusdhooks",
]

MIDDLEWARE = []

ROOT_URLCONF = "tusdhooks.urls"
