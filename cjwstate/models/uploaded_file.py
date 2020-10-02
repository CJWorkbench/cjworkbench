from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from cjwstate import minio
from .step import Step


# Simple model that receives POST requests to upload a file.
# The uploadfile module ingests these, typically converting them to fetched
# data StoredObjects and then deleting
class UploadedFile(models.Model):
    class Meta:
        app_label = "server"
        db_table = "uploaded_file"
        ordering = ["-created_at"]

    # delete this object if its Step deleted
    step = models.ForeignKey(
        Step, related_name="uploaded_files", on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(default=timezone.now, null=True)
    """
    Time the file was uploaded.

    null=True is DEPRECATED. Also, `key` ought to be a folder structure, right?
    Let's solve both at once: rename files on S3 and fill in timestamps as we
    go.
    """

    name = models.CharField(max_length=255)
    size = models.IntegerField(default=0)
    uuid = models.CharField(max_length=255)
    key = models.CharField(max_length=255)


@receiver(models.signals.pre_delete, sender=UploadedFile)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    # Delete S3 data when UploadedFile is deleted
    minio.remove(minio.UserFilesBucket, instance.key)
