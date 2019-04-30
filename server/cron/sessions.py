import logging
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from cjworkbench.sync import database_sync_to_async
from server.models import Workflow


logger = logging.getLogger(__name__)


@database_sync_to_async
def delete_expired_sessions_and_workflows():
    delete_expired_sessions_and_workflows_sync()


def delete_expired_sessions_and_workflows_sync() -> None:
    """
    Delete expired browser sessions and their anonymous Workflows.

    Rationale: nobody can access these Workflows.

    Implementation note: currently (2018-06-18), we use
    django.contrib.sessions.db to determine whether or not the session has
    expired. Call ``SessionStore.clear_expired()`` before calling this
    function.

    In the future, should Workbench switch to cookie-based sessions, we won't
    be able to tell which sessions are expired. In that case we should switch
    this function's logic to simply delete old workflows.
    """
    SessionStore.clear_expired()

    active_session_keys = Session.objects.all().values_list('session_key',
                                                            flat=True)
    # TODO fix race here: new workflows created right now will be deleted
    # immediately. (DB Transactions don't prevent this race.)
    workflows = list(
            Workflow.objects
            .filter(owner__isnull=True)
            .exclude(anonymous_owner_session_key__in=active_session_keys)
    )

    for workflow in workflows:
        with workflow.cooperative_lock():
            logger.info('Deleting workflow %d ("%s")', workflow.id,
                        workflow.name)
            workflow.delete()
