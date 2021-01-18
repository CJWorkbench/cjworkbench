from django.conf import settings
from django.db import models
from django.dispatch import receiver
from django.utils import timezone

from cjwstate import s3
from cjwstate.util import find_deletable_ids

from .step import Step


class UploadedFile(models.Model):
    class Meta:
        app_label = "server"
        db_table = "uploaded_file"
        ordering = ["-created_at"]

    step = models.ForeignKey(
        Step, related_name="uploaded_files", on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(default=timezone.now, null=True)
    """Time the file was uploaded.

    null=True is DEPRECATED. Also, `key` ought to be a folder structure, right?
    Let's solve both at once: rename files on S3 and fill in timestamps as we
    go.
    """

    name = models.CharField(max_length=255)
    size = models.IntegerField(default=0)
    uuid = models.CharField(max_length=255)
    key = models.CharField(max_length=255)


def delete_old_files_to_enforce_storage_limits(*, step: Step) -> int:
    """Delete old fetches that bring us past MAX_BYTES_FILES_PER_STEP or
    MAX_N_FILES_PER_STEP.

    We can't let every workflow grow forever.

    Return number of files deleted. If this isn't 0, the caller must send a
    clientside.Update with the new `files` list.
    """
    to_delete = find_deletable_ids(
        ids_and_sizes=step.uploaded_files.order_by("-created_at").values_list(
            "id", "size"
        ),
        n_limit=settings.MAX_N_FILES_PER_STEP,
        size_limit=settings.MAX_BYTES_FILES_PER_STEP,
    )

    if to_delete:
        # QuerySet.delete() sends pre_delete signal, which deletes from S3
        # ref: https://docs.djangoproject.com/en/2.2/ref/models/querysets/#django.db.models.query.QuerySet.delete
        step.uploaded_files.filter(id__in=to_delete).delete()


@receiver(models.signals.pre_delete, sender=UploadedFile)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    # Delete S3 data when UploadedFile is deleted
    s3.remove(s3.UserFilesBucket, instance.key)
