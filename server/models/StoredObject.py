from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone
from cjwstate import minio


# StoredObject is our persistence layer.
# Allows WfModules to store keyed, versioned binary objects
class StoredObject(models.Model):
    """
    EVIL way of storing fetch results.

    Ideally, a module's fetch() would store whatever it wants. Currently, we
    only allow storing data frames.

    StoredObject links to an S3 bucket+key. The key must adhere to the format:
    "{workflow_id}/{wf_module_id}/{uuidv1()}"
    """

    # delete stored data if WfModule deleted
    wf_module = models.ForeignKey(
        "WfModule", related_name="stored_objects", on_delete=models.CASCADE
    )

    # identification for file backing store
    bucket = models.CharField(max_length=255, null=False, blank=True, default="")
    key = models.CharField(max_length=255, null=False, blank=True, default="")
    stored_at = models.DateTimeField(default=timezone.now)

    # used only for stored tables
    hash = models.CharField(max_length=32)
    size = models.IntegerField(default=0)  # file size

    # keeping track of whether this version of the data has ever been loaded
    # and delivered to the frontend
    read = models.BooleanField(default=False)

    # make a deep copy for another WfModule
    def duplicate(self, to_wf_module):
        basename = self.key.split("/")[-1]
        key = f"{to_wf_module.workflow_id}/{to_wf_module.id}/{basename}"
        minio.copy(self.bucket, key, f"{self.bucket}/{self.key}")

        return to_wf_module.stored_objects.create(
            stored_at=self.stored_at,
            hash=self.hash,
            bucket=self.bucket,
            key=key,
            size=self.size,
        )


@receiver(pre_delete, sender=StoredObject)
def _delete_from_s3_pre_delete(sender, instance, **kwargs):
    """
    Delete file from S3, pre-delete.

    Why pre-delete and not post-delete? Because our user expects the file to be
    _gone_, completely, forever -- that's what "delete" means to the user. If
    deletion fails, we need the link to remain in our database -- that's how
    the user will know it isn't deleted.
    """
    if instance.bucket and instance.key:
        minio.remove(instance.bucket, instance.key)
