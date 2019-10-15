from allauth.account.adapter import DefaultAccountAdapter
from cjworkbench.i18n.templates import context_processor


class AccountAdapter(DefaultAccountAdapter):
    # allauth builds its own context, which does not include
    # the context injected by the context processors in settings.
    # Since we always need our i18n context for translation tags in templates,
    # we have to inject it here.
    def send_mail(self, template_prefix, email, context):
        return super().send_mail(
            template_prefix, email, {**context, **context_processor(context["request"])}
        )
