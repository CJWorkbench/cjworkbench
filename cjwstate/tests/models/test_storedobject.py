from uuid import uuid1
from cjwstate import minio
from cjwstate.models import Workflow
from cjwstate.tests.utils import DbTestCase


class StoredObjectTests(DbTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.create_and_init()
        self.wfm1 = self.workflow.tabs.first().wf_modules.create(order=0, slug="step-1")

    def test_duplicate_bytes(self):
        key = f"{self.workflow.id}/{self.wfm1.id}/{uuid1()}"
        minio.put_bytes(minio.StoredObjectsBucket, key, b"12345")
        self.wfm2 = self.wfm1.tab.wf_modules.create(order=1, slug="step-2")
        so1 = self.wfm1.stored_objects.create(
            bucket=minio.StoredObjectsBucket, key=key, size=5
        )
        so2 = so1.duplicate(self.wfm2)

        # new StoredObject should have same time,
        # different file with same contents
        self.assertEqual(so1.stored_at, so2.stored_at)
        self.assertEqual(so1.size, so2.size)
        self.assertEqual(so1.bucket, so2.bucket)
        self.assertNotEqual(so1.key, so2.key)
        self.assertEqual(
            minio.get_object_with_data(so2.bucket, so2.key)["Body"], b"12345"
        )

    def test_delete_workflow_deletes_from_s3(self):
        minio.put_bytes(minio.StoredObjectsBucket, "test.dat", b"abcd")
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0, slug="step-1")
        wf_module.stored_objects.create(
            size=4, bucket=minio.StoredObjectsBucket, key="test.dat"
        )
        workflow.delete()
        self.assertFalse(minio.exists(minio.StoredObjectsBucket, "test.dat"))

    def test_delete_tab_deletes_from_s3(self):
        minio.put_bytes(minio.StoredObjectsBucket, "test.dat", b"abcd")
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.create(position=1)
        wf_module = tab.wf_modules.create(order=0, slug="step-1")
        wf_module.stored_objects.create(
            size=4, bucket=minio.StoredObjectsBucket, key="test.dat"
        )
        tab.delete()
        self.assertFalse(minio.exists(minio.StoredObjectsBucket, "test.dat"))

    def test_delete_wf_module_deletes_from_s3(self):
        minio.put_bytes(minio.StoredObjectsBucket, "test.dat", b"abcd")
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0, slug="step-1")
        wf_module.stored_objects.create(
            size=4, bucket=minio.StoredObjectsBucket, key="test.dat"
        )
        wf_module.delete()
        self.assertFalse(minio.exists(minio.StoredObjectsBucket, "test.dat"))

    def test_delete_deletes_from_s3(self):
        minio.put_bytes(minio.StoredObjectsBucket, "test.dat", b"abcd")
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0, slug="step-1")
        so = wf_module.stored_objects.create(
            size=4, bucket=minio.StoredObjectsBucket, key="test.dat"
        )
        so.delete()
        self.assertFalse(minio.exists(minio.StoredObjectsBucket, "test.dat"))

    def test_delete_ignores_file_missing_from_s3(self):
        """
        First delete fails after S3 remove_object? Recover.
        """
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0, slug="step-1")
        so = wf_module.stored_objects.create(
            size=4, bucket=minio.StoredObjectsBucket, key="missing-key"
        )
        so.delete()
