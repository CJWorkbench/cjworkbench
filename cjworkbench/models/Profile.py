from django.db import models
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.db.models.signals import post_save

User = get_user_model()

class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        related_name="user_profile")
    get_newsletter = models.BooleanField(default=False)

    @receiver(post_save, sender=User)
    def handle_user_save(sender, instance, created, **kwargs):
        if created:
            UserProfile.objects.create(user=instance)
