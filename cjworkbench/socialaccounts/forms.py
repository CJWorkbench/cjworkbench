import time

from allauth.account.adapter import get_adapter as get_account_adapter
from allauth.socialaccount.forms import SignupForm
from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction

from cjwstate import rabbitmq
from ..i18n.trans import trans_lazy
from ..models.intercom_helpers import notify_intercom_of_new_user
from ..models.userprofile import UserProfile

User = get_user_model()


class WorkbenchSocialaccountSignupForm(forms.Form):
    get_newsletter = forms.BooleanField(required=False)
    field_order = ["get_newsletter"]

    def __init__(self, *, sociallogin, **kwargs):
        self.sociallogin = sociallogin
        super().__init__(**kwargs)

    def save(self, request):
        with transaction.atomic():
            # skip SocialAccountAdapter. This is a huge refactor of allauth: much,
            # much more direct.
            user = self.sociallogin.user
            user.set_unusable_password()
            get_account_adapter().populate_username(request, user)
            user.save()  # skip default behavior of reading name, email from form
            self.sociallogin.save(request)

            # User profile
            user_profile = UserProfile.objects.create(
                user=user,
                locale_id=request.locale_id,
                get_newsletter=self.cleaned_data["get_newsletter"],
            )
        notify_intercom_of_new_user(user, user_profile)
        return user
