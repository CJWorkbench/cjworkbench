import time

from allauth.account.signals import email_confirmed
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.dispatch import receiver

from cjworkbench.models.userprofile import UserProfile
from cjwstate import rabbitmq


def notify_intercom_of_new_user(user: User, user_profile: UserProfile) -> None:
    """Notify Intercom of the user's unsubscribed_from_emails and created_at.

    To save ourselves spam, we don't notify Intercom of unverified email
    addresses. Once the user confirms, then we can finally inform Intercom.

    Not all users confirm their email addresses. Social-account users are
    automatically confirmed. This function must be called every time a user
    becomes confirmed -- by creation or by update.
    """

    async_to_sync(rabbitmq.queue_intercom_message)(
        http_method="POST",
        http_path="/contacts",
        data=dict(
            role="user",
            external_id=str(user.id),
            email=user.email,
            name=(user.first_name + " " + user.last_name).strip(),
            signed_up_at=int(time.time()),
            unsubscribed_from_emails=not user_profile.get_newsletter,
        ),
    )


@receiver(email_confirmed)
def on_email_confirmed_notify_intercom(
    sender, request, email_address: str, **kwargs
) -> None:
    user = (
        User.objects.filter(email=email_address).select_related("user_profile").first()
    )

    if user is None:
        # User was deleted somehow. *shrug* whatever.
        return

    if (
        user.emailaddress_set.filter(verified=True)
        .exclude(email=email_address)
        .exists()
    ):
        # User already confirmed a different email address. That means this
        # user is _not_ transitioning from unconfirmed to confirmed.
        return

    notify_intercom_of_new_user(user, user.user_profile)
