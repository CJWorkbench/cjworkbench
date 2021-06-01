from contextlib import contextmanager
from typing import Any, ContextManager, Dict, Literal

from cjwstate.models.workflow import Workflow
from django.db import transaction

from .types import HandlerError


def is_workflow_authorized(
    workflow: Workflow, scope: Dict[str, Any], role: Literal["read", "write", "owner"]
) -> None:
    """Return whether user+session+has_secret can access Workflow.

    This queries the database. Call it within database_sync_to_async().
    """
    user = scope["user"]
    session = scope["session"]

    if role == "read":
        # If the user supplied a secret and then got here, the user is authorized
        has_secret = isinstance(
            scope["url_route"]["kwargs"]["workflow_id_or_secret_id"], str
        )
        return has_secret or workflow.user_session_authorized_read(user, session)
    elif role == "write":
        return workflow.user_session_authorized_write(user, session)
    elif role == "owner":
        return workflow.user_session_authorized_owner(user, session)


@contextmanager
def lock_workflow_for_role(
    workflow: Workflow, scope: Dict[str, Any], role: Literal["read", "write", "owner"]
) -> ContextManager:
    """Update Workflow, authenticate and yield; or raise HandlerError.

    Raise HandlerError if workflow does not exist.

    Raise HandlerError if request scope is not allowed role.

    This must be called in synchronous database code. The yielded block will
    run within a transaction in which `workflow` is guaranteed not to be
    written by any other processes.
    """
    with transaction.atomic():
        try:
            # Lock the workflow, in the database.
            # This will block until the workflow is released.
            # https://docs.djangoproject.com/en/2.0/ref/models/querysets/#select-for-update
            #
            # list() executes the query
            list(Workflow.objects.select_for_update().filter(id=workflow.id))
        except Workflow.DoesNotExist:
            raise HandlerError("Workflow.DoesNotExist")
        # save() overwrites all fields, so make sure we have the latest
        # versions.
        # https://code.djangoproject.com/ticket/28344#comment:10
        workflow.refresh_from_db()  # won't fail: we're locked

        if not is_workflow_authorized(workflow, scope, role):
            raise HandlerError("AuthError: no %s access to workflow" % (role,))

        yield
