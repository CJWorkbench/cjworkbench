from cjwstate.models import Delta


class InitWorkflowCommand(Delta):
    """
    Special "marker" delta at the start of a workflow.

    Every Workflow needs a sentinel at the beginning of its undo history, so we
    have an ID to cache renders against. Some workflows, such as duplicated
    workflows and test workflows, are fully-functional even with just this one
    Delta.

    Undo and redo are no-ops.
    """

    class Meta:
        app_label = "server"
        proxy = True

    @classmethod
    def create(cls, workflow):
        """
        Save a new Delta on `workflow`, and return the Delta.

        Unlike with other Commands, this `create` method is synchronous and
        assumes you're in a `workflow.cooperative_lock()`.
        """
        delta = cls.objects.create(workflow=workflow)

        workflow.last_delta = delta
        workflow.save(update_fields=["last_delta_id"])

        return delta
