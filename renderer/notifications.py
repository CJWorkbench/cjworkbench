import datetime
import logging
import smtplib
from typing import NamedTuple

from allauth.account.utils import user_display
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from cjworkbench.i18n.templates import get_i18n_context
from cjwstate.models import Step, Workflow
from server.utils import get_absolute_url


logger = logging.getLogger(__name__)


class OutputDelta(NamedTuple):
    """Description of changes between two versions of Step output."""

    user: User
    workflow: Workflow
    step: Step

    @property
    def workflow_name(self) -> str:
        return self.workflow.name

    @property
    def step_id(self) -> int:
        return self.step.id

    @property
    def module_name(self) -> str:
        return self.step.module_id_name

    @property
    def workflow_url(self) -> str:
        return get_absolute_url(self.workflow.get_absolute_url())


def email_output_delta(output_delta: OutputDelta, updated_at: datetime.datetime):
    user = output_delta.user

    ctx = {
        **get_i18n_context(user=user),
        "user_name": user_display(user),
        "module_name": output_delta.module_name,
        "workflow_nname": output_delta.workflow_name,
        "workflow_url": output_delta.workflow_url,
        "date": updated_at,
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

    try:
        mail.send()
    except smtplib.SMTPServerDisconnected:
        logger.error("Failed to send email notification")
