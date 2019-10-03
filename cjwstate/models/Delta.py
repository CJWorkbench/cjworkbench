# Delta
# A single change to state of a workflow
# You can also think of this as a "command." Contains a specification of what
# actually happened.
from django.db import connection, models
import django.utils
from polymorphic.models import PolymorphicModel


# Base class of a single undoable/redoable action
# Derived classes implement the actual mutations on the database
# (via polymorphic forward()/backward())
# To derive a command from Delta:
#
#   - implement @classmethod amend_create_kwargs() -- a database-sync method.
#   - implement load_ws_data() -- a database-sync method.
#   - implement forward() and backward() -- database-sync methods.
#
# Create Deltas using `cjwstate.commands.do()`. This will call these
# synchronous methods correctly.
class Delta(PolymorphicModel):
    class Meta:
        app_label = "server"
        db_table = "server_delta"

    # These fields must be set by any child classes, when instantiating
    workflow = models.ForeignKey(
        "Workflow", related_name="deltas", on_delete=models.CASCADE
    )

    # Next and previous Deltas on this workflow, a linked list.
    prev_delta = models.OneToOneField(
        "self",
        related_name="next_delta",
        null=True,
        default=None,
        on_delete=models.CASCADE,
    )

    datetime = models.DateTimeField("datetime", default=django.utils.timezone.now)

    def _load_workflow_ws_data(self):
        """
        Load the 'updateWorkflow' component of any WebSockets message.
        """
        workflow = self.workflow
        return {
            "name": workflow.name,
            "public": workflow.public,
            "last_update": workflow.last_update().isoformat(),
        }

    def load_ws_data(self):
        """
        Create a dict to send over WebSockets so the client gets new state.

        This is called synchronously. It may access the database. It should
        return `{'updateWorkflow': self._load_workflow_ws_data()}` at the very
        least, because that holds metadata about the delta itself.
        """
        return {"updateWorkflow": self._load_workflow_ws_data()}

    def get_modifies_render_output(self) -> bool:
        """
        Return whether this Delta might change a Step's render() output.

        This must be called in a `workflow.cooperative_lock()`.
        """
        return False

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

    def delete_with_successors(self):
        """
        Delete all Deltas starting with this one.

        Do it in SQL, not code: there can be thousands, and Django's models are
        resource-intensive. (Also, recursion is out of the question, in these
        quantities.)

        Assumes a Delta with a higher ID is a successor.

        Consider calling `workflow.delete_orphan_soft_deleted_models()` after
        calling this method: it may leave behind Tab and WfModule objects that
        nothing refers to, if they previously had `.is_deleted == True`.
        """
        # Oh, Did You Know: django-polymorphic does not have a "delete"
        # feature?
        command_relations = [
            rel for rel in Delta._meta.related_objects if rel.parent_link
        ]
        with_clauses = [
            f"""
            delete_{i} AS (
                DELETE FROM {rel.related_model._meta.db_table} t
                WHERE t.{rel.get_joining_columns()[0][1]} IN (
                    SELECT id FROM to_delete
                )
            )
            """
            for i, rel in enumerate(command_relations)
        ]
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
            WITH
            to_delete AS (
                SELECT id
                FROM {Delta._meta.db_table}
                WHERE workflow_id = {int(self.workflow_id)}
                  AND id >= {int(self.id)}
            ),
            {', '.join(with_clauses)}
            DELETE FROM {Delta._meta.db_table}
            WHERE id IN (SELECT id FROM to_delete)
            """
            )

    @property
    def command_description(self):
        # can be called from Django admin when deleting a wf
        return "Base Delta object"

    def __str__(self):
        return str(self.datetime) + " " + self.command_description
