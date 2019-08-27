import datetime
from typing import Optional
from allauth.account.utils import user_display
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from cjwkernel.pandas.types import ProcessResult
from server.utils import get_absolute_url


class OutputDelta:
    """Description of changes between two versions of WfModule output."""

    def __init__(
        self,
        wf_module: "WfModule",
        old_result: Optional[ProcessResult],
        new_result: ProcessResult,
    ):
        workflow = wf_module.workflow

        self.user = workflow.owner
        self.workflow_name = workflow.name
        self.wf_module_id = wf_module.id
        self.module_name = wf_module.module_id_name
        self.workflow_url = get_absolute_url(workflow.get_absolute_url())
        self.old_result = old_result
        self.new_result = new_result

    def __repr__(self):
        return "OutputDelta" + repr(
            (self.wf_module_id, self.old_result, self.new_result)
        )

    def __eq__(self, other):
        return (
            isinstance(other, OutputDelta)
            and self.wf_module_id == other.wf_module_id
            and self.old_result == other.old_result
            and self.new_result == other.new_result
        )


def email_output_delta(output_delta: OutputDelta, updated_at: datetime.datetime):
    user = output_delta.user

    ctx = {
        "user_name": user_display(user),
        "module_name": output_delta.module_name,
        "workflow_name": output_delta.workflow_name,
        "workflow_url": output_delta.workflow_url,
        "date": updated_at.strftime("%b %-d, %Y at %-I:%M %p"),
    }
    subject = render_to_string("notifications/new_data_version_subject.txt", ctx)
    subject = "".join(subject.splitlines())
    message = render_to_string("notifications/new_data_version.txt", ctx)
    mail = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    mail.attach_alternative(message, "text/html")
    mail.send()
