from django.db import models
from django.utils import timezone

# A Workflow is the user's "document," a series of Modules
class AclEntry(models.Model):
    """
    Access-control-list entry granting a user access to a workflow.
    """

    class Meta:
        app_label = "server"
        db_table = "acl_entry"
        ordering = ["email"]
        unique_together = ("workflow", "email")

    workflow = models.ForeignKey(
        "server.Workflow", related_name="acl", on_delete=models.CASCADE
    )

    email = models.EmailField("email", db_index=True)  # so user can list workflows
    """
    Email of user who has access.

    We use email, not user ID, so owners can share with people who have not yet
    signed up to Workbench.
    """

    # use default, not auto_now_add, so we can set custom values in tests
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    can_edit = models.BooleanField(default=False)
