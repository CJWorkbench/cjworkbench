import datetime

from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from cjwstate import s3

from .step import Step


class StoredObject(models.Model):
    """EVIL way of storing fetch results.

    StoredObject links to an S3 key in s3.StoredObjectsBucket. The key must
    adhere to the format: "{workflow_id}/{step_id}/{uuidv1()}"

    TODO store fetch results as fetches.
    """

    class Meta:
        app_label = "cjworkbench"
        db_table = "stored_object"

    # delete stored data if Step deleted
    step = models.ForeignKey(
        Step, related_name="stored_objects", on_delete=models.CASCADE
    )

    # identification for file backing store
    key = models.CharField(max_length=255, null=False, blank=True, default="")
    stored_at = models.DateTimeField(default=datetime.datetime.now)

    # used only for stored tables
    hash = models.CharField(max_length=32)
    size = models.IntegerField(default=0)  # file size

    # make a deep copy for another Step
    def duplicate(self, to_step):
        basename = self.key.split("/")[-1]
        key = f"{to_step.workflow_id}/{to_step.id}/{basename}"
        s3.copy(s3.StoredObjectsBucket, key, f"{s3.StoredObjectsBucket}/{self.key}")

        return to_step.stored_objects.create(
            stored_at=self.stored_at, hash=self.hash, key=key, size=self.size
        )


@receiver(pre_delete, sender=StoredObject)
def _delete_from_s3_pre_delete(sender, instance, **kwargs):
    """Delete file from S3, pre-delete.

    Why pre-delete and not post-delete? Because our user expects the file to be
    _gone_, completely, forever -- that's what "delete" means to the user. If
    deletion fails, we need the link to remain in our database -- that's how
    the user will know it isn't deleted.
    """
    if instance.key:
        s3.remove(s3.StoredObjectsBucket, instance.key)
