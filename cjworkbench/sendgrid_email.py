from django.core.mail import send_mail
from django.template.loader import render_to_string
from account.hooks import AccountDefaultHookSet
from cjworkbench import settings
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
import os
import pdb

class SendgridEmails(AccountDefaultHookSet):
    def ctx_to_subs(self, ctx):
        return {'-%s-' % key: value for key, value in ctx.items()}

    def send_invitation_email(self, to, ctx):
        subject = render_to_string("account/email/invite_user_subject.txt", ctx)
        message = render_to_string("account/email/invite_user.txt", ctx)
        mail = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to
        )
        mail.attach_alternative(message, "text/html")
        mail.substitutions = self.ctx_to_subs(ctx)
        mail.template_id = settings.SENDGRID_TEMPLATE_IDS['invitation']
        mail.send()

    def send_confirmation_email(self, to, ctx):
        subject = render_to_string("account/email/email_confirmation_subject.txt", ctx)
        subject = "".join(subject.splitlines())  # remove superfluous line breaks
        message = render_to_string("account/email/email_confirmation_message.txt", ctx)
        mail = EmailMultiAlternatives(
          subject=subject,
          body=message,
          from_email=settings.DEFAULT_FROM_EMAIL,
          to=to
        )
        mail.attach_alternative(message, "text/html")
        mail.substitutions = self.ctx_to_subs(ctx)
        mail.template_id = settings.SENDGRID_TEMPLATE_IDS['confirmation']
        mail.send()

    def send_password_change_email(self, to, ctx):
        subject = render_to_string("account/email/password_change_subject.txt", ctx)
        subject = "".join(subject.splitlines())
        message = render_to_string("account/email/password_change.txt", ctx)
        mail = EmailMultiAlternatives(
          subject=subject,
          body=message,
          from_email=settings.DEFAULT_FROM_EMAIL,
          to=to
        )
        mail.attach_alternative(message, "text/html")
        mail.substitutions = self.ctx_to_subs(ctx)
        mail.template_id = settings.SENDGRID_TEMPLATE_IDS['password_change']
        mail.send()

    def send_password_reset_email(self, to, ctx):
        subject = render_to_string("account/email/password_reset_subject.txt", ctx)
        subject = "".join(subject.splitlines())
        message = render_to_string("account/email/password_reset.txt", ctx)
        mail = EmailMultiAlternatives(
          subject=subject,
          body=message,
          from_email=settings.DEFAULT_FROM_EMAIL,
          to=to
        )
        mail.attach_alternative(message, "text/html")
        mail.substitutions = self.ctx_to_subs(ctx)
        settings.SENDGRID_TEMPLATE_IDS['password_reset']
        mail.send()
