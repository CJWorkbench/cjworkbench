import io
import pandas as pd
import uuid as uuidgen
from django.utils import timezone
from cjwstate import minio
from cjwstate.storedobjects import create_stored_object
from cjwstate.models import ModuleVersion, Workflow
from cjwstate.models.commands import InitWorkflowCommand
from cjwstate.tests.utils import DbTestCase


mock_csv_text2 = """Month,Amount,Name
Jan,10,Alicia Aliciason
Feb,666,Fred Frederson
"""
mock_csv_table2 = pd.read_csv(io.StringIO(mock_csv_text2))


# Set up a simple pipeline on test data
class WfModuleTests(DbTestCase):
    def test_list_data_versions(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0, slug="step-1")
        so1 = wf_module.stored_objects.create(read=False)
        so2 = wf_module.stored_objects.create(read=True)

        result = wf_module.list_fetched_data_versions()
        self.assertEqual(result, [(so2.stored_at, True), (so1.stored_at, False)])

    def test_wf_module_duplicate(self):
        workflow = Workflow.create_and_init()
        wfm1 = workflow.tabs.first().wf_modules.create(order=0, slug="step-1")

        # store data to test that it is duplicated
        create_stored_object(workflow, wfm1, pd.DataFrame({"A": [1, 2]}), "hash1")
        so2 = create_stored_object(workflow, wfm1, pd.DataFrame({"B": [2, 3]}), "hash2")
        wfm1.secrets = {"do not copy": {"name": "evil", "secret": "evil"}}
        wfm1.stored_data_version = so2.stored_at
        wfm1.save(update_fields=["stored_data_version"])

        # duplicate into another workflow, as we would do when duplicating a workflow
        workflow2 = Workflow.create_and_init()
        tab2 = workflow2.tabs.first()
        wfm1d = wfm1.duplicate_into_new_workflow(tab2)
        wfm1d.refresh_from_db()  # test what we actually have in the db

        self.assertEqual(wfm1d.slug, "step-1")
        self.assertEqual(wfm1d.workflow, workflow2)
        self.assertEqual(wfm1d.module_version, wfm1.module_version)
        self.assertEqual(wfm1d.order, wfm1.order)
        self.assertEqual(wfm1d.notes, wfm1.notes)
        self.assertEqual(wfm1d.last_update_check, wfm1.last_update_check)
        self.assertEqual(wfm1d.is_collapsed, wfm1.is_collapsed)
        self.assertEqual(wfm1d.params, wfm1.params)
        self.assertEqual(wfm1d.secrets, {})

        # Stored data should contain a clone of content only, not complete version history
        self.assertEqual(wfm1d.stored_objects.count(), 1)
        self.assertEqual(wfm1d.stored_data_version, wfm1.stored_data_version)
        so2d = wfm1d.stored_objects.first()
        # The StoredObject was copied byte for byte into a different file
        self.assertNotEqual(so2d.key, so2.key)
        self.assertEqual(
            minio.get_object_with_data(so2d.bucket, so2d.key)["Body"],
            minio.get_object_with_data(so2.bucket, so2.key)["Body"],
        )

    def test_wf_module_duplicate_disable_auto_update(self):
        """
        Duplicates should be lightweight by default: no auto-updating.
        """
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            auto_update_data=True,
            next_update=timezone.now(),
            update_interval=600,
        )

        workflow2 = Workflow.create_and_init()
        InitWorkflowCommand.create(workflow2)
        tab2 = workflow2.tabs.create(position=0)
        wf_module2 = wf_module.duplicate_into_new_workflow(tab2)

        self.assertEqual(wf_module2.auto_update_data, False)
        self.assertIsNone(wf_module2.next_update)
        self.assertEqual(wf_module2.update_interval, 600)

    def test_wf_module_duplicate_clear_secrets(self):
        """
        Duplicates get new owners, so they should not copy secrets.
        """
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0, slug="step-1", secrets={"auth": {"name": "x", "secret": "y"}}
        )

        workflow2 = Workflow.create_and_init()
        tab2 = workflow2.tabs.first()
        wf_module2 = wf_module.duplicate_into_new_workflow(tab2)

        self.assertEqual(wf_module2.secrets, {})

    def test_wf_module_duplicate_copy_uploaded_file(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0, slug="step-1", module_id_name="upload"
        )
        uuid = str(uuidgen.uuid4())
        key = f"{wf_module.uploaded_file_prefix}{uuid}.csv"
        minio.put_bytes(minio.UserFilesBucket, key, b"1234567")
        # Write the uuid to the old module -- we'll check the new module points
        # to a valid file
        wf_module.params = {"file": uuid, "has_header": True}
        wf_module.save(update_fields=["params"])
        uploaded_file = wf_module.uploaded_files.create(
            name="t.csv", uuid=uuid, bucket=minio.UserFilesBucket, key=key, size=7
        )

        workflow2 = Workflow.create_and_init()
        tab2 = workflow2.tabs.first()
        wf_module2 = wf_module.duplicate_into_new_workflow(tab2)

        uploaded_file2 = wf_module2.uploaded_files.first()
        self.assertIsNotNone(uploaded_file2)
        # New file gets same uuid -- because it's the same file and we don't
        # want to edit params during copy
        self.assertEqual(uploaded_file2.uuid, uuid)
        self.assertEqual(wf_module2.params["file"], uuid)
        self.assertTrue(
            # The new file should be in a different path
            uploaded_file2.key.startswith(wf_module2.uploaded_file_prefix)
        )
        self.assertEqual(uploaded_file2.name, "t.csv")
        self.assertEqual(uploaded_file2.size, 7)
        self.assertEqual(uploaded_file2.created_at, uploaded_file.created_at)
        self.assertEqual(
            minio.get_object_with_data(uploaded_file2.bucket, uploaded_file2.key)[
                "Body"
            ],
            b"1234567",
        )

    def test_wf_module_duplicate_copy_only_selected_uploaded_file(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0, slug="step-1", module_id_name="upload"
        )
        uuid1 = str(uuidgen.uuid4())
        key1 = f"{wf_module.uploaded_file_prefix}{uuid1}.csv"
        minio.put_bytes(minio.UserFilesBucket, key1, b"1234567")
        uuid2 = str(uuidgen.uuid4())
        key2 = f"{wf_module.uploaded_file_prefix}{uuid2}.csv"
        minio.put_bytes(minio.UserFilesBucket, key2, b"7654321")
        uuid3 = str(uuidgen.uuid4())
        key3 = f"{wf_module.uploaded_file_prefix}{uuid3}.csv"
        minio.put_bytes(minio.UserFilesBucket, key3, b"9999999")
        wf_module.uploaded_files.create(
            name="t1.csv", uuid=uuid1, bucket=minio.UserFilesBucket, key=key1, size=7
        )
        wf_module.uploaded_files.create(
            name="t2.csv", uuid=uuid2, bucket=minio.UserFilesBucket, key=key2, size=7
        )
        wf_module.uploaded_files.create(
            name="t3.csv", uuid=uuid3, bucket=minio.UserFilesBucket, key=key3, size=7
        )
        # Write the _middle_ uuid to the old module -- proving that we aren't
        # selecting by ordering
        wf_module.params = {"file": uuid2, "has_header": True}
        wf_module.save(update_fields=["params"])

        workflow2 = Workflow.create_and_init()
        tab2 = workflow2.tabs.first()
        wf_module2 = wf_module.duplicate_into_new_workflow(tab2)

        self.assertEqual(wf_module2.uploaded_files.count(), 1)
        new_uf = wf_module2.uploaded_files.first()
        self.assertEqual(new_uf.uuid, uuid2)

    def test_module_version_lookup(self):
        workflow = Workflow.create_and_init()
        module_version = ModuleVersion.create_or_replace_from_spec(
            {"id_name": "floob", "name": "Floob", "category": "Clean", "parameters": []}
        )
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="floob"
        )
        self.assertEqual(wf_module.module_version, module_version)
        # white-box testing: test that we work even from cache
        self.assertEqual(wf_module.module_version, module_version)

    def test_get_params_on_deleted_module(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="deleted_module", params={"a": "b"}
        )
        self.assertEqual(wf_module.get_params(), {})

    def test_module_version_missing(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="floob"
        )
        self.assertIsNone(wf_module.module_version)

    def test_delete_inprogress_file_upload(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="x"
        )
        ipu = wf_module.in_progress_uploads.create()
        key = ipu.get_upload_key()
        minio.client.create_multipart_upload(Bucket=ipu.Bucket, Key=key)
        wf_module.delete()
        # Assert the upload is gone
        response = minio.client.list_multipart_uploads(Bucket=ipu.Bucket, Prefix=key)
        self.assertNotIn("Uploads", response)

    def test_delete_remove_uploaded_data_by_prefix_in_case_model_missing(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0, slug="step-1")
        uuid = str(uuidgen.uuid4())
        key = wf_module.uploaded_file_prefix + uuid
        minio.put_bytes(minio.UserFilesBucket, key, b"A\n1")
        # Don't create the UploadedFile. Simulates races during upload/delete
        # that could write a file on S3 but not in our database.
        # wf_module.uploaded_files.create(name='t.csv', size=3, uuid=uuid,
        #                                bucket=minio.UserFilesBucket, key=key)
        wf_module.delete()  # do not crash
        with self.assertRaises(FileNotFoundError):
            with minio.RandomReadMinioFile(minio.UserFilesBucket, key) as f:
                f.read()
