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

from .types import AuthError, HandlerRequest, HandlerResponse, \
        HandlerError  # noqa: F401 -- for callers to import
from .decorators import Handlers


async def handle(request: HandlerRequest) -> HandlerResponse:
    """
    Invoke a registered handler with arguments; never error.

    If the handler is not registered, returns error HandlerResponse.

    If the handler accepts different arguments, returns error HandlerResponse.

    If the handler raises any other exception, logs the exception for admins
    (it's a server-side error) and returns error HandlerResponse for the user
    to help with debugging.

    If the handler returns JSON, returns data HandlerResponse.
    """
    # Import -- so handlers are registered
    import server.handlers.tab  # noqa: F401
    #import server.handlers.upload  # noqa: F401
    import server.handlers.wf_module  # noqa: F401
    import server.handlers.workflow  # noqa: F401

    try:
        handler = Handlers[request.path]
    except KeyError:
        return HandlerResponse(request.request_id,
                               error=f'invalid path: {request.path}')

    return await handler(request)
