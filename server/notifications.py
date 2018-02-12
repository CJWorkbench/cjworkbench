from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from cjworkbench import settings
from django.template.loader import render_to_string
#from account.utils import user_display
from server.utils import get_absolute_url

def email_notification(user, wfm):
    ctx = {
        'user_name':user_display(user),
        'workflow_name':wfm.workflow.name,
        'workflow_url':get_absolute_url( wfm.workflow.get_absolute_url() ),
        'date': wfm.stored_data_version.strftime('%b %-d, %Y at %-I:%M %p')
    }
    subject = render_to_string("notifications/new_data_version_subject.txt", ctx)
    subject = "".join(subject.splitlines())
    message = render_to_string("notifications/new_data_version.txt", ctx)
    mail = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )
    mail.attach_alternative(message, "text/html")
    mail.send()
