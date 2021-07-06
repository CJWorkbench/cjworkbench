import os
from collections import defaultdict

__all__ = ("DATABASES", "MIGRATION_MODULES", "N_SYNC_DATABASE_CONNECTIONS", "TIME_ZONE")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "cjworkbench",
        "USER": "cjworkbench",
        "HOST": os.environ["CJW_DB_HOST"],
        "PASSWORD": os.environ["CJW_DB_PASSWORD"],
        "PORT": "5432",
        "CONN_MAX_AGE": 30,
        "TEST": {"SERIALIZE": False, "NAME": "cjworkbench", "MIGRATE": False},
    }
}

# (Any block of Workbench code with a "cooperative_lock" consumes a database
# transaction until finish. Currently, we lock during S3 transfers. TODO make
# cooperative_lock() use PgLocker instead.)
#
# (PgLocker connections do not count against SYNC_DATABASE_CONNECTIONS.)
N_SYNC_DATABASE_CONNECTIONS = 3
"""Number of simultaneous Django database operations.

This indicates the number of `database_sync_to_async` coroutines that can be
running simultaneously. Excess calls will block until older calls finish.

Smaller numbers give higher throughput on the database. There are no known
"slow" database queries in Workbench; but if we found some, we'd want to
increase this number so they don't block other requests.
"""

MIGRATION_MODULES = defaultdict(None)  # Disable Django migrations; we use Flyway

TIME_ZONE = "UTC"  # Set os.environ["TZ"]
