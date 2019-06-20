import uuid
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone
import pandas as pd
from server.pandas_util import hash_table
from server import minio, parquet


def _build_key(workflow_id: int, wf_module_id: int) -> str:
    """Build a helpful S3 key."""
    return f'{workflow_id}/{wf_module_id}/{uuid.uuid1()}.dat'


# StoredObject is our persistence layer.
# Allows WfModules to store keyed, versioned binary objects
class StoredObject(models.Model):
    # delete stored data if WfModule deleted
    wf_module = models.ForeignKey('WfModule', related_name='stored_objects',
                                  on_delete=models.CASCADE)

    # identification for file backing store
    bucket = models.CharField(max_length=255, null=False, blank=True,
                              default='')
    key = models.CharField(max_length=255, null=False, blank=True, default='')
    stored_at = models.DateTimeField(default=timezone.now)

    # used only for stored tables
    hash = models.CharField(max_length=32)
    size = models.IntegerField(default=0)  # file size

    # keeping track of whether this version of the data has ever been loaded
    # and delivered to the frontend
    read = models.BooleanField(default=False)

    @staticmethod
    def create_table(wf_module, table):
        hash = hash_table(table)
        return StoredObject.__create_table_internal(wf_module, table, hash)

    # Create a new StoredObject if it's going to store different data than the
    # previous one. Otherwise null Fast; checks hash without loading file
    # contents
    @staticmethod
    def create_table_if_different(wf_module, old_so, table):
        if old_so is None:
            return StoredObject.create_table(wf_module, table)

        hash = hash_table(table)
        if hash != old_so.hash:
            old_table = old_so.get_table()
            if not old_table.equals(table):
                return StoredObject.__create_table_internal(wf_module, table,
                                                            hash)

        return None

    @staticmethod
    def __create_table_internal(wf_module, table, hash):
        # Write to minio bucket/key
        bucket = minio.StoredObjectsBucket
        key = _build_key(wf_module.workflow_id, wf_module.id)
        size = parquet.write(bucket, key, table)

        # Create the object that references the bucket/key
        return wf_module.stored_objects.create(
            bucket=minio.StoredObjectsBucket,
            key=key,
            size=size,
            hash=hash
        )

    def get_table(self):
        if not self.bucket or not self.key:
            # Old (obsolete) objects have no bucket/key, usually because
            # empty tables weren't being written.
            return pd.DataFrame()

        try:
            return parquet.read(self.bucket, self.key)
        except FileNotFoundError:
            # There was a pre-delete that never got committed; or maybe there's
            # some other, long-existing DB inconsistency.
            return pd.DataFrame()
        except parquet.FastparquetCouldNotHandleFile:
            return pd.DataFrame()  # empty table

    # make a deep copy for another WfModule
    def duplicate(self, to_wf_module):
        key = _build_key(to_wf_module.workflow_id, to_wf_module.id)
        minio.copy(self.bucket, key, f'{self.bucket}/{self.key}')

        return to_wf_module.stored_objects.create(
            stored_at=self.stored_at,
            hash=self.hash,
            bucket=self.bucket,
            key=key,
            size=self.size
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
