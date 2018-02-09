# Clone Workflows with "example" flag set when a user account is created, to give them something to play with

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from server.models import Workflow

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        examples = Workflow.objects.filter(example=True)
        for wf in examples:
            wf.duplicate(instance)
