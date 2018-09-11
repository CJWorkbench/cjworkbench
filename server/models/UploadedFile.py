import os
from django.conf import settings
from django.db import models
from django.dispatch import receiver
from server.minio import minio_client


# Simple model that receives POST requests to upload a file.
# The uploadfile module ingests these, typically converting them to fetched
# data StoredObjects and then deleting
class UploadedFile(models.Model):
    # delete this object if its WfModule deleted
    wf_module = models.ForeignKey('WfModule', related_name='uploaded_files',
                                  on_delete=models.CASCADE)

    file = models.CharField(default=None, max_length=100, null=True)
    name = models.CharField(default=None, max_length=255, null=True)
    size = models.IntegerField(default=0)
    uuid = models.CharField(default=None, max_length=255, null=True)
    bucket = models.CharField(default=None, max_length=255, null=True)
    key = models.CharField(default=None, max_length=255, null=True)


@receiver(models.signals.post_delete, sender=UploadedFile)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    # Deletes file from filesystem when corresponding UploadedFile object is
    # deleted.
    if instance.file:
        path = os.path.join(settings.BASE_DIR, 'media', instance.file)
        if os.path.isfile(path):
            os.remove(path)

    if instance.bucket and instance.key:
        minio_client.remove_object(instance.bucket, instance.key)
