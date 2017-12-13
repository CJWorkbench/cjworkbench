from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from cjworkbench import settings

def email_notification(to, wfm):
    subject = "New data version"
    message = "New data is available for workflow module %s at %s" \
        (wfm.workflow_version.workflow.name, wfm.stored_data_version)
    mail = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to]
    )
    mail.attach_alternative(message, "text/html")
    mail.send()
