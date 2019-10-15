from allauth.account.adapter import DefaultAccountAdapter
from cjworkbench.i18n.templates import context_processor


class AccountAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix, email, context):
        return super().send_mail(
            template_prefix, email, {**context, **context_processor(context["request"])}
        )
