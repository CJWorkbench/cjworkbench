import os
import tempfile
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
    file = models.FileField(null=True)  # DEPRECATED
    bucket = models.CharField(max_length=255, null=True)
    key = models.CharField(max_length=255, null=True)
    stored_at = models.DateTimeField(default=timezone.now)

    # used only for stored tables
    hash = models.CharField(max_length=32)
    metadata = models.CharField(default=None, max_length=255, null=True)
    size = models.IntegerField(default=0)  # file size

    # keeping track of whether this version of the data has ever been loaded
    # and delivered to the frontend
    read = models.BooleanField(default=False)

    @staticmethod
    def create_table(wf_module, table, metadata=None):
        hash = hash_table(table)
        return StoredObject.__create_table_internal(wf_module, table,
                                                    metadata, hash)

    # Create a new StoredObject if it's going to store different data than the
    # previous one. Otherwise null Fast; checks hash without loading file
    # contents
    @staticmethod
    def create_table_if_different(wf_module, old_so, table, metadata=None):
        if old_so is None:
            return StoredObject.create_table(wf_module, table,
                                             metadata=metadata)

        hash = hash_table(table)
        if hash != old_so.hash:
            old_table = old_so.get_table()
            if not old_table.equals(table):
                return StoredObject.__create_table_internal(wf_module, table,
                                                            metadata, hash)

        return None

    @staticmethod
    def __create_table_internal(wf_module, table, metadata, hash):
        # Write to minio bucket/key
        bucket = minio.StoredObjectsBucket
        key = _build_key(wf_module.workflow_id, wf_module.id)
        with tempfile.NamedTemporaryFile() as tf:
            parquet.write(tf.name, table)
            size = tf.seek(0, os.SEEK_END)
            tf.seek(0)
            minio.minio_client.put_object(bucket, key, tf, length=size)

        # Create the object that references the bucket/key
        return wf_module.stored_objects.create(
            metadata=metadata,
            bucket=minio.StoredObjectsBucket,
            key=key,
            size=size,
            hash=hash
        )

    def get_table(self):
        if self.bucket and self.key:
            with minio.temporarily_download(self.bucket, self.key) as tf:
                try:
                    return parquet.read(tf.name)
                except parquet.FastparquetCouldNotHandleFile:
                    return pd.DataFrame()  # empty table

        if not self.file:
            # Before 2018-11-09, we did not write empty data frames.
            #
            # We changed this because #160865813 shows that zero-row Parquet
            # files still contain important data: column information.
            return pd.DataFrame()

        try:
            return parquet.read(self.file.path)
        except (FileNotFoundError, parquet.FastparquetCouldNotHandleFile):
            # Spotted on production for a duplicated workflow dated
            # 2018-08-01. [adamhooper, 2018-09-20] I can think of no harm in
            # returning an empty dataframe here.
            return pd.DataFrame()  # empty table

    def ensure_using_s3(self):
        """
        Ensure self.file is None.

        self.file is deprecated
        """
        if not self.file:
            return

        path = self.file.path

        self.bucket = minio.StoredObjectsBucket
        self.key = _build_key(self.wf_module.workflow_id,
                              self.wf_module.id)
        try:
            minio.minio_client.fput_object(self.bucket, self.key, path)
            self.file = None
            self.save(update_fields=['bucket', 'key', 'file'])

            os.remove(path)
        except FileNotFoundError:
            self.file = None
            self.save(update_fields=['bucket', 'key', 'file'])

    # make a deep copy for another WfModule
    def duplicate(self, to_wf_module):
        if to_wf_module == self.wf_module:
            # Filename would clash, therefore we can't do that
            raise ValueError(
                'Cannot duplicate a StoredObject to same WfModule'
            )

        self.ensure_using_s3()
        key = _build_key(to_wf_module.workflow_id, to_wf_module.id)
        minio.minio_client.copy_object(self.bucket, key,
                                       f'/{self.bucket}/{self.key}')

        new_so = to_wf_module.stored_objects.create(
            stored_at=self.stored_at,
            hash=self.hash,
            metadata=self.metadata,
            bucket=self.bucket,
            key=key,
            size=self.size
        )
        return new_so


@receiver(pre_delete, sender=StoredObject)
def _delete_from_s3_pre_delete(sender, instance, **kwargs):
    """
    Delete file from S3, pre-delete.

    Why pre-delete and not post-delete? Because our user expects the file to be
    _gone_, completely, forever -- that's what "delete" means to the user. If
    deletion fails, we need the link to remain in our database -- that's how
    the user will know it isn't deleted.
    """
    try:
        minio.minio_client.remove_object(instance.bucket, instance.key)
    except minio.errors.NoSuchKey:
        pass
