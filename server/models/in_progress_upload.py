import datetime
import re
from pathlib import PurePath
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from cjwstate import minio


class InProgressUpload(models.Model):
    """
    An upload that is waiting upon a user.

    This is an allocation of a UUID and a key within S3.

    DO NOT delete this model without first calling delete_s3_data().

    There's a state transition to follow here:

        1. Created: User can call generate_upload_parameters() and upload....
        2. Completed: an UploadedFile was created; now, this is just a token
           that indicates the user has the ability to upload unwanted files.
        3. Deleted (happens in cronjob): all unwanted S3 data is deleted. There
           is no credential out there that will let the user upload unwanted
           files.

    We may skip from Created to Deleted without passing through Completed.
    Regardless, the minimum lifetime of an InProgressUpload is Excepti
    """

    class Meta:
        db_table = "server_inprogressupload"

    Bucket = minio.UserFilesBucket
    """
    S3 bucket where in-progress uploads happen.
    """

    MaxCredentialAge = datetime.timedelta(hours=12)
    """
    How long credentials returned by generate_upload_parameters() are valid.

    As long as credentials are valid, the user may create multipart uploads and
    upload files to our key -- wanted or unwanted.
    """

    MaxAge = datetime.timedelta(hours=13)
    """
    How long an InProgressUpload may exist.

    We generate 12-hour upload credentials, and we delay expiry for 13 hours.
    That avoids a race: if users begin a request before credentials expire, the
    request may continue until after credentials expire -- meaning we must make
    sure this InProgressUpload continues to exist.
    """

    UuidFromKeyRegex = re.compile(
        r"\Awf-\d+/wfm-\d+/upload_([a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12})\Z"
    )
    """
    Regex for extracting a valid UUID from the key.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    """
    Primary key and filename stem.
    """

    wf_module = models.ForeignKey(
        "WfModule", related_name="in_progress_uploads", on_delete=models.CASCADE
    )

    updated_at = models.DateTimeField(default=timezone.now, db_index=True)
    """
    The last time the user interacted with this upload.

    This staves off expiry. A cronjob will delete expired file uploads to
    reclaim disk space.
    """

    is_completed = models.BooleanField(default=False)
    """
    Whether an UploadedFile was created for this InProgressUpload.

    An InProgressUpload has no meaning after its UploadedFile is created; but
    the user still holds upload credentials and could still conceivably put
    files there. So the InProgressUpload must stick around in the database until
    after we're certain the user won't upload anything more (i.e., the user's
    credentials expire).

    Most callers should behave as though completed InProgressUploads do not
    exist. Only the deletion cronjob needs to see them.
    """

    def get_upload_key(self):
        """
        Calculate the key where the end user can store this file.

        This takes a database query.
        """
        return self.wf_module.uploaded_file_prefix + "upload_" + str(self.id)

    @classmethod
    def upload_key_to_uuid(cls, key: str) -> uuid.UUID:
        """
        Extract a UUID from the return value of `get_upload_key()`.

        Raise ValueError if the string was obviously not generated by
        `get_upload_key()`.

        The returned UUID isn't guaranteed to be in the database. It's
        just guaranteed to be a UUID.
        """
        result = cls.UuidFromKeyRegex.match(key)
        if not result:
            raise ValueError(
                "This key does not match the regex " + str(cls.UuidFromKeyRegex)
            )
        return uuid.UUID(result.group(1))

    def delete_s3_data(self):
        """
        Delete all data from S3 that is part of this upload.

        Call this within a Workflow.cooperative_lock().

        This always leaves S3 and the database in a consistent state.
        """
        key = self.get_upload_key()
        minio.abort_multipart_uploads_by_prefix(self.Bucket, key)
        minio.remove(self.Bucket, key)

        if not self.wf_module.uploaded_files.filter(uuid=str(self.id)).count():
            # If there's no UploadedFile even though we copied this file to where the
            # UploadedFile _should_ point, then we've leaked that copy. Delete. See
            # "tricky leak here" in convert_to_uploaded_file().
            final_key_prefix = self.wf_module.uploaded_file_prefix + str(self.id)
            # no ".xlsx"-type suffix
            minio.remove_by_prefix(minio.UserFilesBucket, final_key_prefix)

    def generate_upload_parameters(self):
        """
        Create new S3 credentials and parameters to send to the client.

        Raise AssertionError if is_completed. The caller should pretend
        completed uploads do not exist.

        Overwrite `updated_at`, to end after the credentials expire.

        The response looks like:

            {
                "endpoint": <S3 service>,
                "region": "us-east-1",
                "bucket": <bucket>,
                "key": <key>,
                "credentials": {
                    "accessKeyId": <...>,
                    "secretAccessKey": <...>,
                    "sessionToken": <...>,
                }
            }
        """
        assert not self.is_completed  # this InProgressUpload should not be visible

        key = self.get_upload_key()
        credentials = minio.assume_role_to_write(
            self.Bucket, key, duration_seconds=self.MaxCredentialAge.seconds
        )
        self.updated_at = timezone.now()
        self.save(update_fields=["updated_at"])
        return {
            "endpoint": settings.MINIO_EXTERNAL_URL,
            "region": "us-east-1",
            "bucket": self.Bucket,
            "key": key,
            "credentials": credentials,
        }

    def convert_to_uploaded_file(self, filename):
        """
        Generate an UploadedFile and delete this InProgressUpload.

        Raise FileNotFoundError if the user never finished uploading. That's
        right: we throw an exception if the _end user_ doesn't do what we want.
        The user is meant to upload the file (putObject or multipart) and
        _then_ convert it. Callers should handle the case in which the end user
        asks to convert the file before the upload is complete.
        """
        assert not self.is_completed  # this InProgressUpload should not be visible

        key = self.get_upload_key()
        suffix = PurePath(filename).suffix
        final_key = self.wf_module.uploaded_file_prefix + str(self.id) + suffix
        try:
            minio.copy(
                minio.UserFilesBucket,
                final_key,
                f"{self.Bucket}/{key}",
                ACL="private",
                MetadataDirective="REPLACE",
                ContentDisposition=minio.encode_content_disposition(filename),
                ContentType="application/octet-stream",
            )
        except minio.error.NoSuchKey:
            raise FileNotFoundError
        # Potential tricky leak here: if there's an exception, then final_key
        # is in S3 but nothing in the database refers to it. Careful coding of
        # delete_s3_data() solves this.
        size = minio.stat(minio.UserFilesBucket, final_key).size
        uploaded_file = self.wf_module.uploaded_files.create(
            name=filename,
            size=size,
            uuid=str(self.id),
            bucket=minio.UserFilesBucket,
            key=final_key,
        )
        self.is_completed = True
        self.save(update_fields=["is_completed"])
        self.delete_s3_data()
        return uploaded_file
