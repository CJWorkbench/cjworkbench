from uuid import uuid1
from cjwstate import minio
from cjwstate.models import Workflow
from cjwstate.tests.utils import DbTestCase, get_minio_object_with_data


class StoredObjectTests(DbTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.create_and_init()
        self.step1 = self.workflow.tabs.first().steps.create(order=0, slug="step-1")

    def test_duplicate_bytes(self):
        key = f"{self.workflow.id}/{self.step1.id}/{uuid1()}"
        minio.put_bytes(minio.StoredObjectsBucket, key, b"12345")
        self.step2 = self.step1.tab.steps.create(order=1, slug="step-2")
        so1 = self.step1.stored_objects.create(key=key, size=5)
        so2 = so1.duplicate(self.step2)

        # new StoredObject should have same time,
        # different file with same contents
        self.assertEqual(so2.stored_at, so1.stored_at)
        self.assertEqual(so2.size, so1.size)
        self.assertNotEqual(so2.key, so1.key)
        self.assertEqual(
            get_minio_object_with_data(minio.StoredObjectsBucket, so2.key)["Body"],
            b"12345",
        )

    def test_delete_workflow_deletes_from_s3(self):
        minio.put_bytes(minio.StoredObjectsBucket, "test.dat", b"abcd")
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")
        step.stored_objects.create(size=4, key="test.dat")
        workflow.delete()
        self.assertFalse(minio.exists(minio.StoredObjectsBucket, "test.dat"))

    def test_delete_tab_deletes_from_s3(self):
        minio.put_bytes(minio.StoredObjectsBucket, "test.dat", b"abcd")
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.create(position=1)
        step = tab.steps.create(order=0, slug="step-1")
        step.stored_objects.create(size=4, key="test.dat")
        tab.delete()
        self.assertFalse(minio.exists(minio.StoredObjectsBucket, "test.dat"))

    def test_delete_step_deletes_from_s3(self):
        minio.put_bytes(minio.StoredObjectsBucket, "test.dat", b"abcd")
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")
        step.stored_objects.create(size=4, key="test.dat")
        step.delete()
        self.assertFalse(minio.exists(minio.StoredObjectsBucket, "test.dat"))

    def test_delete_deletes_from_s3(self):
        minio.put_bytes(minio.StoredObjectsBucket, "test.dat", b"abcd")
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")
        so = step.stored_objects.create(size=4, key="test.dat")
        so.delete()
        self.assertFalse(minio.exists(minio.StoredObjectsBucket, "test.dat"))

    def test_delete_ignores_file_missing_from_s3(self):
        """
        First delete fails after S3 remove_object? Recover.
        """
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")
        so = step.stored_objects.create(size=4, key="missing-key")
        so.delete()
