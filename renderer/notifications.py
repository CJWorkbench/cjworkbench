import datetime
import logging
import smtplib
from typing import NamedTuple

from allauth.account.utils import user_display
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from cjwstate.models.step import Step
from cjwstate.models.workflow import Workflow


logger = logging.getLogger(__name__)


class OutputDelta(NamedTuple):
    """Description of changes between two versions of Step output."""

    user: User
    workflow: Workflow
    step: Step
    locale_id: str

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
    def workflow_id(self) -> str:
        return self.workflow.id


def email_output_delta(output_delta: OutputDelta, updated_at: datetime.datetime):
    domain = Site.objects.get_current().domain
    workflow_url = f"https://${domain}/workflows/{output_delta.workflow_id}/"

    ctx = {
        "i18n": {"locale_id": output_delta.locale_id},
        "user_name": user_display(output_delta.user),
        "module_name": output_delta.module_name,
        "workflow_name": output_delta.workflow_name,
        "workflow_url": workflow_url,
        "date": updated_at,
    }
    subject = render_to_string("new_data_version_subject.txt", ctx)
    subject = "".join(subject.splitlines())
    message = render_to_string("new_data_version.txt", ctx)
    mail = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[output_delta.user.email],
    )
    mail.attach_alternative(message, "text/html")

    try:
        mail.send()
    except smtplib.SMTPServerDisconnected:
        logger.error("Failed to send email notification")
