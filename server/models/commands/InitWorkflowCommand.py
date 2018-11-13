from server.models import Delta


class InitWorkflowCommand(Delta):
    """
    Special "marker" delta for a duplicated workflow.

    A duplicated workflow doesn't keep the original's undo history; but we
    still need to render it because there are modules with output. Render
    results need a delta ID: thus, they need an initial delta to render.

    Undo and redo are no-ops.
    """

    async def forward(self):
        """Crash. There is no way to undo, so forward() can't be called."""
        raise RuntimeError(
            'InitWorkflowCommand cannot be undone, so forward() cannot happen'
        )

    async def backward(self):
        """Do nothing at all."""
        # Don't do _anything_.
        pass

    @classmethod
    def create(cls, workflow):
        """
        Save a new Delta on `workflow`, and return the Delta.

        Unlike with other Commands, this `create` method is synchronous and
        assumes you're in a `workflow.cooperative_lock()`.
        """
        delta = cls.objects.create(workflow=workflow)

        workflow.last_delta = delta
        workflow.save(update_fields=['last_delta_id'])

        return delta

    @property
    def command_description(self):
        return f'Duplicate Workflow'
