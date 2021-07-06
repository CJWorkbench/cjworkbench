import datetime
from enum import Enum

from django.db import models

from .fields import Role, RoleField


class AclEntry(models.Model):
    """Access-control-list entry granting a user access to a workflow."""

    class Meta:
        app_label = "cjworkbench"
        db_table = "acl_entry"
        ordering = ["email"]
        unique_together = ("workflow", "email")

    workflow = models.ForeignKey(
        "cjworkbench.Workflow", related_name="acl", on_delete=models.CASCADE
    )

    email = models.EmailField("email", db_index=True)  # so user can list workflows
    """Email of user who has access.

    We use email, not user ID, so owners can share with people who have not yet
    signed up to Workbench.
    """

    role = RoleField(default=Role.VIEWER)
    """User's role."""

    created_at = models.DateTimeField(default=datetime.datetime.now, editable=False)
    """Timestamp of when the entry was created."""
