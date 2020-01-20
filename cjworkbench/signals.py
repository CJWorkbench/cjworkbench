from allauth.account.signals import user_logged_in
from django.dispatch import receiver
from cjworkbench.i18n import set_language_cookie


@receiver(user_logged_in)
def set_locale_cookie_after_login(sender, *, response, user, **kwargs):
    set_language_cookie(response, user.user_profile.locale_id)
