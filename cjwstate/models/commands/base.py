from typing import List, Tuple

from cjwstate import clientside


class BaseCommand:
    """Logic to execute a Delta.

    `Delta.command_type` points to a subclass of this.

    Subclasses must specify a never-modified `DB_TYPE_NAME` constant. They
    must override `.amend_create_kwargs()`, `.forward()` and `.backward()`.
    They may override other methods, too.
    """

    def amend_create_kwargs(self, **kwargs):
        """Look up additional objects.create() kwargs from the database.

        Delta creation can depend upon values already in the database. The
        delta may calculate those values itself.

        Return `None` to abort creating the Delta altogether.

        Example:

            def amend_create_kwargs(self, *, workflow, **kwargs):
                return {**kwargs, 'workflow': workflow, 'old_value': ... }
        """
        return kwargs

    def forward(self, delta: "Delta") -> None:
        """Modify the database according to delta.values_for_forward, etc.

        If you mixin ChangesStepOutputs, call `self.forward_affected_delta_ids`
        here.
        """
        raise NotImplementedError

    def backward(self, delta: "Delta") -> None:
        """Modify the database according to delta.values_for_backward, etc.

        If you mixin ChangesStepOutputs, call `self.backward_affected_delta_ids`
        here.
        """
        raise NotImplementedError

    def load_clientside_update(self, delta: "Delta") -> clientside.Update:
        """Build state updates for the client to receive over Websockets.

        This is called synchronously. It may access the database. When
        overriding, be sure to call super() to update the most basic data.

        This must be called in a `workflow.cooperative_lock()`.
        """
        return clientside.Update(
            workflow=clientside.WorkflowUpdate(updated_at=delta.workflow.updated_at)
        )

    def affected_step_delta_ids(self, step: "Step") -> List[Tuple[int, int]]:
        """Calculate [(step_id, previous_delta_id)] for `step` and deps.

        This is a stub. Subclass ChangesStepOutputs (and read this method's
        documentation there) if you are creating a Delta that may require a
        render.
        """
        return []

    def get_modifies_render_output(self, delta: "Delta") -> bool:
        """Return whether this Delta might change a Step's render() output.

        This must be called in a `workflow.cooperative_lock()`.
        """
        return False
