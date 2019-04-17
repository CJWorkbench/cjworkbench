import os
from django.conf import settings
from django.db import models
from django.dispatch import receiver
from server import minio


# Simple model that receives POST requests to upload a file.
# The uploadfile module ingests these, typically converting them to fetched
# data StoredObjects and then deleting
class UploadedFile(models.Model):
    # delete this object if its WfModule deleted
    wf_module = models.ForeignKey('WfModule', related_name='uploaded_files',
                                  on_delete=models.CASCADE)

    name = models.CharField(max_length=255)
    size = models.IntegerField(default=0)
    uuid = models.CharField(max_length=255)
    bucket = models.CharField(max_length=255)
    key = models.CharField(max_length=255)


@receiver(models.signals.post_delete, sender=UploadedFile)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    # Delete S3 data when UploadedFile is deleted
    minio.remove(instance.bucket, instance.key)
