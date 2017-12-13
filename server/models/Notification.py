from django.db import models
from .WfModule import WfModule

class Notification(models.Model):
    wf_module = models.ForeignKey(WfModule, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.CharField(max_length=200)
