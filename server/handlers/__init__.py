"""
Mini-framework for handling Websockets requests on /workflows.

Calling convention
------------------

The *Websockets* client sends a command like this:

    {
        "path": "workflow.set_name",
        "arguments": {
            "name": "foo"
        }
    }

This will attempt to invoke:

    await server.handlers.workflow.set_name(workflow=workflow, name='foo')

To avoid remote-code-execution security problems, the modules under `handler`
need to explicitly register submodules:

    server/handlers/workflow/__init__.py:

        from .. import websockets_handler
        # load sub-module code
        from . import tabs

        @register_websockets_handler
        @websockets_handler(role='read')
        async def set_name(workflow, name, **kwargs):
            # role is one of {'read', 'write', 'owner'}
            await ChangeWorkflowTitleCommand.create(workflow, name)
            return

TypeError (meaning, "client arguments don't match function signature") will
log a warning.

If the function returns something, it will be sent to the client. Otherwise,
the command is treated as write-and-forget. (A common pattern is to
write-and-forget and trust Workbench to _broadcast_ the outcome to all
clients, instead of just the requester. Another common pattern: on error,
`return {'error': 'some message'}`.)

If the handler raises any exception other than TypeError, that's a bug in our
code. It will be logged (so we'll get an email) _and_ returned to the user (so
the user can help us with debugging).

**Beware async**: handlers are all async, which means they should not access
the database directly. Instead, make them await methods decorated with
@database_sync_to_async, or make them sync and decorate them with
@database_sync_to_async.
"""

import functools
import logging
from typing import Any, Dict, Optional, Set
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from server.models import Workflow


logger = logging.getLogger(__name__)
Handlers = {}


def register_websockets_handler(func):
    """
    Register a handler, to be used in handle().
    """
    module_name = func.__module__  # server.handlers.workflow.help
    submodule_name = module_name.replace(f'{__name__}.', '')  # workflow.help
    Handlers[f'{submodule_name}.{func.__name__}'] = func
    return func


class AuthError(Exception):
    pass


@database_sync_to_async
def _authorize(user, session, workflow, role):
    if role == 'read':
        if not workflow.user_session_authorized_read(user, session):
            raise AuthError('no read access to workflow')
    elif role == 'write':
        if not workflow.user_session_authorized_write(user, session):
            raise AuthError('no write access to workflow')
    elif role == 'owner':
        if not workflow.user_session_authorized_owner(user, session):
            raise AuthError('no owner access to workflow')


def websockets_handler(role: str='read'):
    """
    Augment a function with auth and error handling.

    Usage:

        @websockets_handler(role='read')
        async def noop(user, workflow):
            # Do nothing
            return

        @websockets_handler(role='read')
        async def echo(user, workflow, message):
            # Return a message for the user
            return {'message': message}

        @websockets_handler(role='read')
        @database_sync_to_async
        def set_title(user, workflow, title):
            # Database writes must be wrapped in database_sync_to_async()
            workflow.title = title
            workflow.save(update_fields=['title'])

        @websocket_handler(role='read')
        async def set_title_with_command(user, workflow, title):
            # If invoking as async, database writes must _still_ be wrapped in
            # database_sync_to_async().
            @database_sync_to_async
            def write_title():
                workflow.title = title
                workflow.save(update_fields=['title'])

            await asyncio.sleep(0.001)
            await write_title()
    """
    def decorator_websockets_handler(func):
        @functools.wraps(func)
        async def inner(user: User, session: Session, workflow: Workflow,
                        arguments):
            try:
                await _authorize(user, session, workflow, role)
                return await func(user=user, session=session,
                                  workflow=workflow, **arguments)
            except AuthError as err:
                return {'error': f'AuthError: {str(err)}'}
            except TypeError as err:
                return {'error': f'invalid arguments: {str(err)}'}
            except Exception as err:
                logger.exception(f'Error in handler')
                return {'error': f'{type(err).__name__}: {str(err)}'}

        return inner
    return decorator_websockets_handler


async def handle(user: User, session: Session, workflow: Workflow, path: str,
                 arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Invoke a registered handler with arguments.

    If the handler is not registered, returns error JSON for the user.

    If the handler accepts different arguments, returns error JSON for the
    user.

    If the handler raises any other exception, logs the exception for admins
    (it's a server-side error) and returns the error JSON for the user to help
    with debugging.

    If the handler returns JSON, returns it for the user.
    """
    try:
        handler = Handlers[path]
    except KeyError:
        return {'error': f'invalid path: {path}'}

    return await handler(user, session, workflow, arguments)
