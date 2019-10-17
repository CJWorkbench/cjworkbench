from dataclasses import dataclass
import datetime
from typing import Optional
from allauth.account.utils import user_display
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from cjwkernel.types import RenderResult
from cjwstate.models import WfModule, Workflow
from server.utils import get_absolute_url
from cjworkbench.i18n.templates import get_i18n_context


@dataclass
class OutputDelta:
    """Description of changes between two versions of WfModule output."""

    user: User
    workflow: Workflow
    wf_module: WfModule
    old_result: Optional[RenderResult]
    new_result: RenderResult

    @property
    def workflow_name(self) -> str:
        return self.workflow.name

    @property
    def wf_module_id(self) -> int:
        return self.wf_module.id

    @property
    def module_name(self) -> str:
        return self.wf_module.module_id_name

    @property
    def workflow_url(self) -> str:
        return get_absolute_url(self.workflow.get_absolute_url())


def email_output_delta(output_delta: OutputDelta, updated_at: datetime.datetime):
    user = output_delta.user

    ctx = {
        **get_i18n_context(user=user),
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
