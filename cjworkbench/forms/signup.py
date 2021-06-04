import logging
import time

from asgiref.sync import async_to_sync
from django import forms
from django.contrib.auth import get_user_model

from cjworkbench.models.userprofile import UserProfile
from cjworkbench.i18n.trans import trans_lazy
from cjwstate import rabbitmq


logger = logging.getLogger(__name__)


class WorkbenchSignupForm(forms.ModelForm):
    get_newsletter = forms.BooleanField(required=False, initial=True)
    field_order = [
        "email",
        "first_name",
        "last_name",
        "password1",
        "password2",
        "get_newsletter",
    ]

    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "placeholder": trans_lazy(
                        "py.forms.signup.firstName.placeholder", default="First name"
                    )
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "placeholder": trans_lazy(
                        "py.forms.signup.lastName.placeholder", default="Last name"
                    )
                }
            ),
        }

    def signup(self, request, user):
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save(update_fields=["first_name", "last_name"])

        # User profile
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "get_newsletter": self.cleaned_data["get_newsletter"],
                "locale_id": request.locale_id,
            },
        )

        try:
            async_to_sync(rabbitmq.queue_intercom_message)(
                http_method="POST",
                http_path="/contacts",
                data=dict(
                    role="user",
                    external_id=str(user.id),
                    email=user.email,
                    name=(user.first_name + " " + user.last_name).strip(),
                    signed_up_at=int(time.time()),
                    unsubscribed_from_emails=not self.cleaned_data["get_newsletter"],
                ),
            )
        except Exception:
            logger.exception("Failed to queue data for Intercom")
