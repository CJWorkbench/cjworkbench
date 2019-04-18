import asyncio
import functools
import logging
from channels.db import database_sync_to_async
from .types import AuthError, HandlerRequest, HandlerResponse, HandlerError


Handlers = {}


logger = logging.getLogger(__name__)


ParentModuleName = '.'.join(__name__.split('.')[:-1])


def register_websockets_handler(func):
    """
    Register a handler, to be used in handle().
    """
    module_name = func.__module__  # server.handlers.workflow.help
    submodule_name = module_name.replace(f'{ParentModuleName}.',
                                         '')  # workflow.help
    Handlers[f'{submodule_name}.{func.__name__}'] = func
    return func


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


def websockets_handler(role: str = 'read'):
    """
    Augment a function with auth, logging and error handling.

    Usage:

        @websockets_handler(role='read')
        async def noop(**kwargs):
            # Do nothing
            return

        @websockets_handler(role='read')
        async def echo(message, **kwargs):
            # Return a message for the user
            return {'message': message}

        @websockets_handler(role='write')
        @database_sync_to_async
        def set_title(workflow, title, **kwargs):
            # Database writes must be wrapped in database_sync_to_async()
            workflow.title = title
            workflow.save(update_fields=['title'])

        @websocket_handler(role='read')
        async def set_title_with_command(workflow, title, **kwargs):
            # If invoking as async, database writes must _still_ be wrapped in
            # database_sync_to_async().
            @database_sync_to_async
            def write_title():
                workflow.title = title
                workflow.save(update_fields=['title'])

            await asyncio.sleep(0.001)
            await write_title()

        @websocket_handler(role='read')
        async def return_error_to_user(**kwargs):
            # Exceptions in handlers are all bugs, _except_ HandlerError which
            # is a response for the client.
            raise HandlerError('error message')
    """
    def decorator_websockets_handler(func):
        @functools.wraps(func)
        async def inner(request: HandlerRequest) -> HandlerResponse:
            logger.info('%s(workflow=%d)', request.path,
                        request.workflow.id)

            try:
                await _authorize(request.scope['user'],
                                 request.scope['session'],
                                 request.workflow, role)
            except AuthError as err:
                return HandlerResponse(request.request_id,
                                       error=f'AuthError: {str(err)}')

            try:
                task = func(scope=request.scope, workflow=request.workflow,
                            **request.arguments)
            except TypeError as err:
                return HandlerResponse(request.request_id,
                                       error=f'invalid arguments: {str(err)}')

            try:
                data = await task
            except HandlerError as err:
                return HandlerResponse(request.request_id, error=str(err))
            except asyncio.CancelledError:
                raise  # and don't log
            except Exception as err:
                logger.exception(f'Error in handler')
                message = f'{type(err).__name__}: {str(err)}'
                return HandlerResponse(request.request_id, error=message)

            return HandlerResponse(request.request_id, data)

        return inner
    return decorator_websockets_handler
