from allauth.account.adapter import DefaultAccountAdapter
from cjworkbench.i18n.templates import context_processor
from django.contrib.sites.shortcuts import get_current_site


class AccountAdapter(DefaultAccountAdapter):
    # allauth builds its own context (both in send_confirmation email and in other places),
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
