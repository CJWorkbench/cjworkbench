from django.db import models
from django.contrib.auth import get_user_model
from django.contrib import admin
from django.dispatch import receiver
from django.db.models.signals import post_save
from allauth.account.utils import user_display

User = get_user_model()


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        related_name="user_profile",
        on_delete=models.CASCADE,
    )
    get_newsletter = models.BooleanField(default=False)

    def __str__(self):
        return user_display(self.user) + ' (' + self.user.email + ')'

    @receiver(post_save, sender=User)
    def handle_user_save(sender, instance, created, **kwargs):
        if created:
            UserProfile.objects.get_or_create(user=instance)


admin.site.register(UserProfile)
