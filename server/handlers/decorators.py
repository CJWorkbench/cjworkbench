import functools
import logging
from typing import Optional

from cjworkbench.sync import database_sync_to_async
from .types import HandlerRequest, HandlerResponse, HandlerError
from .util import is_workflow_authorized


Handlers = {}


logger = logging.getLogger(__name__)


ParentModuleName = ".".join(__name__.split(".")[:-1])


_is_workflow_authorized_async = database_sync_to_async(is_workflow_authorized)


def register_websockets_handler(func):
    """
    Register a handler, to be used in handle().
    """
    module_name = func.__module__  # server.handlers.workflow.help
    submodule_name = module_name.replace(f"{ParentModuleName}.", "")  # workflow.help
    Handlers[f"{submodule_name}.{func.__name__}"] = func
    return func


def websockets_handler(role: Optional[str]):
    """Augment a function with auth, logging and error handling.

    The `role=None` only makes sense if A) the request doesn't really pertain to
    the workflow; or B) the decorated function does its own authentication, e.g.
    with `util.lock_workflow_for_role()`.

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

        @websocket_handler(role=None)
        async def authenticate_separately(scope, workflow, **kwargs):
            with lock_workflow_for_role(workflow, scope, 'owner'):  # or HandlerError
                workflow.title = 'Changed!'
                workflow.save(update_fields=['title'])
    """

    def decorator_websockets_handler(func):
        @functools.wraps(func)
        async def inner(request: HandlerRequest) -> HandlerResponse:
            logger.info("%s(workflow=%d)", request.path, request.workflow.id)

            if role is not None and not await _is_workflow_authorized_async(
                request.workflow, request.scope, role
            ):
                return HandlerResponse(
                    request.request_id,
                    error="AuthError: no %s access to workflow" % (role,),
                )

            try:
                task = func(
                    scope=request.scope, workflow=request.workflow, **request.arguments
                )
            except TypeError as err:
                return HandlerResponse(
                    request.request_id, error=f"invalid arguments: {str(err)}"
                )

            try:
                data = await task
            except HandlerError as err:
                return HandlerResponse(request.request_id, error=str(err))
            except Exception as err:
                logger.exception("Error in handler")
                message = f"{type(err).__name__}: {str(err)}"
                return HandlerResponse(request.request_id, error=message)

            return HandlerResponse(request.request_id, data)

        return inner

    return decorator_websockets_handler
