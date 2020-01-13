from allauth.account.adapter import DefaultAccountAdapter
from cjworkbench.i18n.templates import context_processor
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from django.contrib import messages


class AccountAdapter(DefaultAccountAdapter):
    # allauth builds its own context (in `send_confirmation email`, in `add_message` and maybe in other places),
    # which does not include the context injected by the context processors in settings.
    # Since we always need our i18n context for translation tags in templates,
    # we have to inject it here.
    def send_mail(self, template_prefix, email, context):
        return super().send_mail(
            template_prefix, email, {**context, **context_processor(context["request"])}
        )

    # send_confirmation_email does not add request to ctx by default,
    # hence there is no request for our send_mail to find
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        current_site = get_current_site(request)
        activate_url = self.get_email_confirmation_url(request, emailconfirmation)
        ctx = {
            "user": emailconfirmation.email_address.user,
            "activate_url": activate_url,
            "current_site": current_site,
            "key": emailconfirmation.key,
            "request": request,  # only this line differs from the original
        }
        if signup:
            email_template = "account/email/email_confirmation_signup"
        else:
            email_template = "account/email/email_confirmation"
        self.send_mail(email_template, emailconfirmation.email_address.email, ctx)

    def add_message(
        self, request, level, message_template, message_context=None, extra_tags=""
    ):
        """
        Wrapper of `django.contrib.messages.add_message`, that reads
        the message text from a template.
        """
        if "django.contrib.messages" in settings.INSTALLED_APPS:
            try:
                if message_context is None:
                    message_context = {}
                message = render_to_string(
                    message_template, {**message_context, **context_processor(request)}
                ).strip()
                if message:
                    messages.add_message(request, level, message, extra_tags=extra_tags)
            except TemplateDoesNotExist:
                pass
