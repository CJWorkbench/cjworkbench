from django.db import models
from django.dispatch import receiver
import os

# Simple model that receives POST requests to upload a file.
# The uploadfile module ingests these, typically converting them to fetched data StoredObjects and then deleting
class UploadedFile(models.Model):
    # delete this object if its WfModule deleted
    wf_module = models.ForeignKey('WfModule', related_name='uploaded_files', on_delete=models.CASCADE)

    file = models.FileField()
    name = models.CharField(default=None, max_length=255, null=True)
    size = models.IntegerField(default=0)
    uuid = models.CharField(default=None, max_length=255, null=True)


@receiver(models.signals.post_delete, sender=UploadedFile)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    # Deletes file from filesystem when corresponding UploadedFile object is deleted.
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)
