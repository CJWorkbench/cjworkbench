import logging
import time

from django import forms
from django.contrib.auth import get_user_model

from cjworkbench.models.intercom_helpers import notify_intercom_of_new_user
from cjworkbench.models.userprofile import UserProfile
from cjworkbench.i18n.trans import trans_lazy
from cjwstate import rabbitmq

User = get_user_model()

logger = logging.getLogger(__name__)


class WorkbenchSignupForm(forms.Form):
    first_name = forms.CharField(
        required=False,
        label=trans_lazy("py.forms.signup.firstName.label", default="First name"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "given-name",
                "placeholder": trans_lazy(
                    "py.forms.signup.firstName.placeholder", default="First name"
                ),
            }
        ),
    )
    last_name = forms.CharField(
        required=False,
        label=trans_lazy("py.forms.signup.lastName.label", default="Last name"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "family-name",
                "placeholder": trans_lazy(
                    "py.forms.signup.lastName.placeholder", default="Last name"
                ),
            }
        ),
    )
    get_newsletter = forms.BooleanField(required=False, initial=True)
    field_order = [
        "email",
        "first_name",
        "last_name",
        "password1",
        "password2",
        "get_newsletter",
    ]

    def signup(self, request, user: User):
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save(update_fields=["first_name", "last_name"])

        # User profile
        user_profile = UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "get_newsletter": self.cleaned_data["get_newsletter"],
                "locale_id": request.locale_id,
            },
        )
