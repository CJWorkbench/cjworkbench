from django.db import models
from .WfModule import WfModule
from server.notifications import email_notification

class Notification(models.Model):
    wf_module = models.ForeignKey(WfModule, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.CharField(max_length=200)

    @staticmethod
    def create(wf_module, message):
        new_notification = Notification.objects.create(
            wf_module = wf_module,
            message = message
        )
        saved = new_notification.save()
        email_notification(wf_module.workflow.owner.email, wf_module)
        return saved
