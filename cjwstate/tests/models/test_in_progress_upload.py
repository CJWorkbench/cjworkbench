import time
from cjwstate import minio
from cjwstate.models import Workflow
from cjwstate.tests.utils import DbTestCase


class InProgressUploadTest(DbTestCase):
    def test_delete_s3_data_multipart_upload(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="x"
        )
        ipu = wf_module.in_progress_uploads.create()
        minio.client.create_multipart_upload(
            Bucket=ipu.Bucket, Key=ipu.get_upload_key()
        )

        # precondition: there's an incomplete multipart upload. minio is a bit
        # different from S3 here, so we add a .assertIn to verify that the data
        # is there _before_ we abort.
        response = minio.client.list_multipart_uploads(
            Bucket=minio.UserFilesBucket, Prefix=ipu.get_upload_key()
        )
        self.assertIn("Uploads", response)

        ipu.delete_s3_data()

        # And now the upload is gone
        response = minio.client.list_multipart_uploads(
            Bucket=minio.UserFilesBucket, Prefix=ipu.get_upload_key()
        )
        self.assertNotIn("Uploads", response)

    def test_delete_s3_data_leaked_file(self):
        # Delete a file with our UUID but without an UploadedFile.
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="x"
        )
        ipu = wf_module.in_progress_uploads.create()
        key = wf_module.uploaded_file_prefix + str(ipu.id) + ".xlsx"
        minio.put_bytes(minio.UserFilesBucket, key, b"1234567")
        ipu.delete_s3_data()
        self.assertFalse(minio.exists(minio.UserFilesBucket, key))

    def test_delete_s3_data_ignore_non_leaked_file(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="x"
        )
        ipu = wf_module.in_progress_uploads.create()
        key = wf_module.uploaded_file_prefix + str(ipu.id) + ".xlsx"
        minio.put_bytes(minio.UserFilesBucket, key, b"1234567")
        wf_module.uploaded_files.create(
            name="text.xlsx", size=7, uuid=str(self.id), key=key
        )
        ipu.delete_s3_data()
        self.assertFalse(minio.exists(minio.UserFilesBucket, key))

    def test_convert_to_uploaded_file_file_not_found_error(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="x"
        )
        ipu = wf_module.in_progress_uploads.create()
        with self.assertRaises(FileNotFoundError):
            ipu.convert_to_uploaded_file("test.csv")

    def test_convert_to_uploaded_file_happy_path(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="x"
        )
        ipu = wf_module.in_progress_uploads.create()
        minio.put_bytes(ipu.Bucket, ipu.get_upload_key(), b"1234567")
        uploaded_file = ipu.convert_to_uploaded_file("test sheet.xlsx")
        self.assertEqual(uploaded_file.uuid, str(ipu.id))
        final_key = wf_module.uploaded_file_prefix + str(ipu.id) + ".xlsx"
        # New file on S3 has the right bytes and metadata
        self.assertEqual(
            minio.get_object_with_data(minio.UserFilesBucket, final_key)["Body"],
            b"1234567",
        )
        self.assertEqual(
            minio.client.head_object(Bucket=minio.UserFilesBucket, Key=final_key)[
                "ContentDisposition"
            ],
            "attachment; filename*=UTF-8''test%20sheet.xlsx",
        )
        # InProgressUpload is completed
        self.assertEqual(ipu.is_completed, True)
        ipu.refresh_from_db()
        self.assertEqual(ipu.is_completed, True)  # also on DB
        # Uploaded file is deleted
        self.assertFalse(minio.exists(minio.UserFilesBucket, ipu.get_upload_key()))

    def test_integration_happy_path(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="x"
        )
        ipu = wf_module.in_progress_uploads.create()
        updated_at1 = ipu.updated_at
        time.sleep(0.000001)  # so updated_at changes
        params = ipu.generate_upload_parameters()
        ipu.refresh_from_db()  # ensure we wrote updated_at
        updated_at2 = ipu.updated_at
        self.assertGreater(updated_at2, updated_at1)

        # Upload using a separate S3 client
        # Import _after_ we've imported minio -- so cjwstate.minio's monkey-patch
        # takes effect.
        import boto3

        credentials = params["credentials"]
        session = boto3.session.Session(
            aws_access_key_id=credentials["accessKeyId"],
            aws_secret_access_key=credentials["secretAccessKey"],
            aws_session_token=credentials["sessionToken"],
            region_name=params["region"],
        )
        client = session.client("s3", endpoint_url=params["endpoint"])
        client.put_object(Bucket=ipu.Bucket, Key=ipu.get_upload_key(), Body=b"1234567")

        # Complete the upload
        uploaded_file = ipu.convert_to_uploaded_file("test.csv")
        self.assertEqual(
            minio.get_object_with_data(minio.UserFilesBucket, uploaded_file.key)[
                "Body"
            ],
            b"1234567",
        )
