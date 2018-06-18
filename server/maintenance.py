import warnings
from django.conf import settings
from django.contrib.sessions.models import Session
from server.models import Workflow


def delete_expired_anonymous_workflows() -> None:
    """Delete Workflows that have an expired session and no owner.

    Rationale: nobody can access these Workflows.

    Implementation note: currently (2018-06-18), we use
    django.contrib.sessions.db to determine whether or not the session has
    expired. Call ``SessionStore.clear_expired()`` before calling this
    function.

    In the future, should Workbench switch to cookie-based sessions, we won't
    be able to tell which sessions are expired. In that case we should switch
    this function's logic to simply delete old workflows.
    """
    if settings.SESSION_ENGINE != 'django.contrib.sessions.backends.db':
        warnings.warn('WARNING: not deleting anonymous workflows because we do not know which sessions are expired. Rewrite delete_expired_anonymous_workflows() to fix this problem.')
        return

    active_session_keys = Session.objects.all().values_list('session_key',
                                                            flat=True)
    workflows = Workflow.objects \
            .filter(owner__isnull=True) \
            .exclude(anonymous_owner_session_key__in=active_session_keys)

    for workflow in workflows:
        with workflow.cooperative_lock():
            workflow.delete()
