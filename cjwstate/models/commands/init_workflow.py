from .base import BaseCommand


class InitWorkflow(BaseCommand):
    """Special "marker" delta at the start of a workflow.

    Every Workflow needs a sentinel at the beginning of its undo history, so we
    have an ID to cache renders against. Some workflows, such as duplicated
    workflows and test workflows, are fully-functional even with just this one
    Delta.

    Undo and redo are no-ops.
    """

    @classmethod
    def create(cls, workflow: "Workflow") -> "Delta":
        """Save a new Delta on `workflow`, and return the Delta.

        This `create` method is synchronous and assumes you're in a
        `workflow.cooperative_lock()`.
        """
        from ..delta import Delta

        delta = Delta.objects.create(workflow=workflow, command_name=cls.__name__)

        workflow.last_delta = delta
        workflow.save(update_fields=["last_delta_id"])

        return delta

    def forward(self, delta):
        raise RuntimeError("Cannot forward() an init-workflow Delta")

    def backward(self, delta):
        raise RuntimeError("Cannot forward() an init-workflow Delta")
