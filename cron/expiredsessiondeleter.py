import logging
import time

import django
import django.db
from django.conf import settings

from cjworkbench.util import benchmark_sync


logger = logging.getLogger(__name__)

Interval = 300  # seconds


def delete_expired_sessions_and_workflows() -> None:
    """Delete expired browser sessions and their anonymous Workflows.

    Rationale: nobody can access these Workflows.

    Implementation note: currently (2018-06-18), we use
    django.contrib.sessions.db to determine whether or not the session has
    expired. Call ``SessionStore.clear_expired()`` before calling this
    function.

    In the future, should Workbench switch to cookie-based sessions, we won't
    be able to tell which sessions are expired. In that case we should switch
    this function's logic to simply delete old workflows.
    """
    # import _after_ django.setup() initializes apps
    from django.contrib.sessions.backends.db import SessionStore
    from django.contrib.sessions.models import Session
    from cjwstate.models import Workflow

    SessionStore.clear_expired()

    active_session_keys = Session.objects.all().values_list("session_key", flat=True)
    # TODO fix race here: new workflows created right now will be deleted
    # immediately. (DB Transactions don't prevent this race.)
    workflows = list(
        Workflow.objects.filter(owner__isnull=True).exclude(
            anonymous_owner_session_key__in=active_session_keys
        )
    )

    for workflow in workflows:
        with workflow.cooperative_lock():
            logger.info("Deleting workflow %d", workflow.id)
            workflow.delete()


if __name__ == "__main__":
    django.setup()

    if settings.SESSION_ENGINE != "django.contrib.sessions.backends.db":
        warnings.warn(
            "WARNING: not deleting anonymous workflows because we do not know "
            "which sessions are expired. Rewrite "
            "delete_expired_sessions_and_workflows() to fix this problem."
        )
        # Run forever
        while True:
            time.sleep(999999)

    while True:
        django.db.close_old_connections()
        with benchmark_sync(logger, "Deleting expired sessions"):
            delete_expired_sessions_and_workflows()
        time.sleep(Interval)
