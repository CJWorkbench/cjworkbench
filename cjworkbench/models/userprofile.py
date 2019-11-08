from django.db import models
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.db.models.signals import post_save
from allauth.account.utils import user_display
from cjworkbench import i18n


User = get_user_model()


class UserProfile(models.Model):
    user = models.OneToOneField(
        User, related_name="user_profile", on_delete=models.CASCADE
    )

    get_newsletter = models.BooleanField(default=False)
    """
    True iff the user is requesting to be part of our newsletter.

    There is a race here. TODO delete this field and query our mass-mail
    service instead.
    """

    max_fetches_per_day = models.IntegerField(
        default=500,
        help_text=(
            "Applies to the sum of all this user's Workflows. "
            "One fetch every 5min = 288 fetches per day."
        ),
    )
    """
    Quota for cronjobs.
    """

    locale_id = models.CharField(
        max_length=5,
        default=i18n.default_locale,
        choices=[(x, x) for x in i18n.supported_locales],
    )
    """
    User-selected locale ID.

    This overrides the request-session locale ID. It's also used for emailed
    "new data available" notifications (for which there are no HTTP requests).
    """

    def __str__(self):
        return user_display(self.user) + " (" + self.user.email + ")"

    @receiver(post_save, sender=User)
    def handle_user_save(sender, instance, created, **kwargs):
        if created:
            UserProfile.objects.get_or_create(user=instance)
