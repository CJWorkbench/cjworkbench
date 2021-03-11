import datetime
from enum import Enum

from django.db import models


class Role(Enum):
    """Access level of an ACL entry's user to its workflow."""

    EDITOR = "editor"
    """User may add, remove or edit steps and edit the report.

    User cannot view or edit secrets.
    """

    VIEWER = "viewer"
    """User may view steps (including their parameters) and the report.

    User cannot view secrets.
    """

    REPORT_VIEWER = "report-viewer"
    """User may view the "report" -- including all its embeds and tables.

    User cannot view any step parameters, or any embeds or tables that aren't
    included in the report. (The workflow editor is not viewable: only the
    report HTML and the data it links are viewable.)

    By default, a workflow's report includes all its embeds. So by default,
    report-viewer may view all those embeds and their tables.

    Access to an embed means access to the table data that backs it. The
    report-viewer may download all that table data.
    """


class AclEntry(models.Model):
    """Access-control-list entry granting a user access to a workflow."""

    class Meta:
        app_label = "server"
        db_table = "acl_entry"
        ordering = ["email"]
        unique_together = ("workflow", "email")

    workflow = models.ForeignKey(
        "server.Workflow", related_name="acl", on_delete=models.CASCADE
    )

    email = models.EmailField("email", db_index=True)  # so user can list workflows
    """Email of user who has access.

    We use email, not user ID, so owners can share with people who have not yet
    signed up to Workbench.
    """

    created_at = models.DateTimeField(default=datetime.datetime.now, editable=False)
    """Timestamp of when the entry was created."""

    can_edit = models.BooleanField(default=False)
    """DEPRECATED. When true, role is "editor"."""
