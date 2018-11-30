# Delta
# A single change to state of a workflow
# You can also think of this as a "command." Contains a specification of what
# actually happened.
import json
from typing import Any
from channels.db import database_sync_to_async
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
import django.utils
from polymorphic.models import PolymorphicModel
from server import rabbitmq, websockets
from server.serializers import WfModuleSerializer


def _prepare_json(data: Any) -> Any:
    """Convert `data` into a simple, JSON-ready dict."""
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


# Base class of a single undoable/redoable action
# Derived classes implement the actual mutations on the database
# (via polymorphic forward()/backward())
# To derive a command from Delta:
#   - implement forward_impl() and backward_impl()
#   - implement a static create() that takes parameters and calls
#     `MyCommandClass.create_impl(**kwargs)`. `Delta.create_impl()`
#     will call `delta.forward()` within a Workflow.cooperative_lock().
class Delta(PolymorphicModel):
    class Meta:
        # OMG this bug ate so many hours...
        # https://github.com/django-polymorphic/django-polymorphic/issues/229
        base_manager_name = 'base_objects'

    # These fields must be set by any child classes, when instantiating
    workflow = models.ForeignKey('Workflow', related_name='deltas',
                                 on_delete=models.CASCADE)

    # Next and previous Deltas on this workflow, a linked list.
    prev_delta = models.OneToOneField('self', related_name='next_delta',
                                      null=True, default=None,
                                      on_delete=models.CASCADE)

    datetime = models.DateTimeField('datetime',
                                    default=django.utils.timezone.now)

    @database_sync_to_async
    def _call_forward_and_load_ws_data(self):
        with self.workflow.cooperative_lock():
            self.forward_impl()

            # Point workflow to us
            self.workflow.last_delta = self
            self.workflow.save(update_fields=['last_delta_id'])

            return self.load_ws_data()

    @database_sync_to_async
    def _call_backward_and_load_ws_data(self):
        with self.workflow.cooperative_lock():
            self.backward_impl()

            # Point workflow to previous delta
            # Only update prev_delta_id: other columns may have been edited in
            # backward_impl().
            self.workflow.last_delta = self.prev_delta
            self.workflow.save(update_fields=['last_delta_id'])

            return self.load_ws_data()

    async def forward(self):
        """Call forward_impl() with workflow.cooperative_lock()."""
        ws_data = await self._call_forward_and_load_ws_data()
        await self.ws_notify(ws_data)
        await self.schedule_execute()

    async def backward(self):
        """Call backward_impl() with workflow.cooperative_lock()."""
        ws_data = await self._call_backward_and_load_ws_data()
        await self.ws_notify(ws_data)
        await self.schedule_execute()

    async def ws_notify(self, ws_data):
        """
        Notify WebSocket clients that we just undid or redid.

        This default implementation sends a 'delta' command. It will always
        include a 'set-workflow' property; it may include a 'set-wf-module'
        command and may include a 'clear-wf-module' command.

        This must be called within the same Workflow.cooperative_lock() that
        triggered the change in the first place.
        """
        await websockets.ws_client_send_delta_async(self.workflow_id, ws_data)

    def load_ws_data(self):
        workflow = self.workflow
        data = {
            'updateWorkflow': {
                'name': workflow.name,
                'public': workflow.public,
                'last_update': workflow.last_update().isoformat(),
            },
            'updateWfModules': {}
        }

        if hasattr(self, '_changed_wf_module_versions'):
            for id, delta_id in self._changed_wf_module_versions:
                data['updateWfModules'][str(id)] = {
                    'last_relevant_delta_id': delta_id,
                    'quick_fixes': [],
                    'output_columns': [],
                    'output_error': '',
                    'output_status': 'busy',
                    'output_n_rows': 0,
                }

        if hasattr(self, 'wf_module'):
            if self.wf_module.is_deleted or self.wf_module.tab.is_deleted:
                # When we did or undid this command, we removed the
                # WfModule from the Workflow.
                data['clearWfModuleIds'] = [self.wf_module_id]
            else:
                # Serialize _everything_, including params
                #
                # TODO consider serializing only what's changed, so when Alice
                # changes 'has_header' it doesn't overwrite Bob's 'url' while
                # he's editing it.
                wf_module_data = WfModuleSerializer(self.wf_module).data

                data['updateWfModules'][str(self.wf_module_id)] = \
                    _prepare_json(wf_module_data)

            data['updateTabs'] = {
                str(self.wf_module_id): {
                    'wf_module_ids': list(self.wf_module.tab.live_wf_modules
                                          .values_list('id', flat=True)),
                },
            }

        return data

    async def schedule_execute(self) -> None:
        """Tell renderers to render the new workflow."""
        await rabbitmq.queue_render(self.workflow.id,
                                    self.workflow.last_delta_id)

    @classmethod
    async def create(cls, *, workflow, **kwargs):
        """
        Wrap create_impl().

        A bit of history: previously, we used @staticmethod instead of
        @classmethod to define `create()` methods, meaning we needed one on
        each command. They tend to look alike. Now we've switched to
        @classmethod. TODO delete the subclasses' `create()` methods.
        """
        return await cls.create_impl(workflow=workflow, **kwargs)

    @classmethod
    async def create_impl(cls, *args, **kwargs) -> None:
        """Create the given Delta and run .forward().

        Keyword arguments vary by cls, but `workflow` is always required.

        If `amend_create_kwargs()` returns `None`, no-op.

        Example:

            delta = await ChangeWfModuleNotesCommand.create_impl(
                workflow=wf_module.workflow,
                # ... other kwargs
            )
            # now delta has been applied and committed to the database, and
            # websockets users have been notified.
        """

        delta, ws_data = await cls._first_forward_and_save_returning_ws_data(
            *args,
            **kwargs
        )

        if delta:
            await delta.ws_notify(ws_data)
            await delta.schedule_execute()

        return delta

    @classmethod
    def amend_create_kwargs(cls, **kwargs):
        """
        Look up additional objects.create() kwargs from the database.

        Delta creation can depend upon values already in the database. The
        delta may calculate those values itself.

        Return `None` to abort creating the Delta altogether.

        Example:

            @classmethod
            def amend_create_kwargs(cls, *, workflow, **kwargs):
                return {**kwargs, 'workflow': workflow, 'old_value': ... }
        """
        return kwargs

    @classmethod
    @database_sync_to_async
    def _first_forward_and_save_returning_ws_data(cls, *args, **kwargs):
        """
        Create and execute command, returning `(Delta, WebSockets data)`.

        If `amend_create_kwargs()` returns `None`, return `(None, None)` here.

        All this, in a cooperative lock.
        """
        workflow = kwargs['workflow']
        with workflow.cooperative_lock():
            create_kwargs = cls.amend_create_kwargs(**kwargs)
            if not create_kwargs:
                return (None, None)

            # Delete unapplied deltas. We identify these by looking for the
            # head of the linked list that comes _after_ workflow.last_delta.
            orphan_delta = Delta.objects \
                .filter(prev_delta_id=workflow.last_delta_id) \
                .first()
            if orphan_delta:
                orphan_delta.delete()  # recurses through CASCADE

            delta = cls.objects.create(*args,
                                       prev_delta_id=workflow.last_delta_id,
                                       **create_kwargs)
            delta.forward_impl()

            # Point workflow to us
            workflow.last_delta = delta
            workflow.save(update_fields=['last_delta_id'])

            return (delta, delta.load_ws_data())

    @property
    def command_description(self):
        raise NotImplemented

    def __str__(self):
        return str(self.datetime) + ' ' + self.command_description
