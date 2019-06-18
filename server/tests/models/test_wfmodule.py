import io
import pandas as pd
import uuid as uuidgen
from django.utils import timezone
from server import minio
from server.models import ModuleVersion, Workflow
from server.models.commands import InitWorkflowCommand
from server.tests.utils import DbTestCase, mock_csv_table


mock_csv_text2 = """Month,Amount,Name
Jan,10,Alicia Aliciason
Feb,666,Fred Frederson
"""
mock_csv_table2 = pd.read_csv(io.StringIO(mock_csv_text2))


# Set up a simple pipeline on test data
class WfModuleTests(DbTestCase):
    def test_retrieve_table_error_missing_version(self):
        '''
        If user selects a version and then the version disappers, no version is
        selected; return `None`.

        Returning `None` is kinda arbitrary. Another option is to return the
        latest version; but then, what if the caller also looks at
        wf_module.stored_data_version? The two values would be inconsistent.
        '''
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0)
        table1 = pd.DataFrame({'A': [1]})
        table2 = pd.DataFrame({'B': [2]})
        stored_object1 = wf_module.store_fetched_table(table1)
        wf_module.store_fetched_table(table2)
        wf_module.stored_data_version = stored_object1
        wf_module.save()
        wf_module.stored_objects.get(stored_at=stored_object1).delete()
        wf_module.refresh_from_db()
        self.assertIsNone(wf_module.retrieve_fetched_table())

    # test stored versions of data: create, retrieve, set, list, and views
    def test_wf_module_data_versions(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0)
        table1 = mock_csv_table
        table2 = mock_csv_table2

        # nothing ever stored
        nothing = wf_module.retrieve_fetched_table()
        self.assertIsNone(nothing)

        # save and recover data
        firstver = wf_module.store_fetched_table(table1)
        wf_module.save()
        wf_module.refresh_from_db()
        self.assertNotEqual(wf_module.stored_data_version, firstver) # should not switch versions by itself
        self.assertIsNone(wf_module.retrieve_fetched_table()) # no stored version, no table
        wf_module.stored_data_version = firstver
        wf_module.save()
        tableout1 = wf_module.retrieve_fetched_table()
        self.assertTrue(tableout1.equals(table1))

        # create another version
        secondver = wf_module.store_fetched_table(table2)
        self.assertNotEqual(wf_module.stored_data_version, secondver) # should not switch versions by itself
        self.assertNotEqual(firstver, secondver)
        wf_module.stored_data_version = secondver
        wf_module.save()
        tableout2 = wf_module.retrieve_fetched_table()
        self.assertTrue(tableout2.equals(table2))

        # change the version back
        wf_module.stored_data_version = firstver
        wf_module.save()
        tableout1 = wf_module.retrieve_fetched_table()
        self.assertTrue(tableout1.equals(table1))

        # list versions
        verlist = wf_module.list_fetched_data_versions()
        correct_verlist = [secondver, firstver] # sorted by creation date, latest first
        self.assertListEqual([ver[0] for ver in verlist], correct_verlist)

    def test_wf_module_store_table_if_different(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0)
        table1 = mock_csv_table
        table2 = mock_csv_table2

        # nothing ever stored
        nothing = wf_module.retrieve_fetched_table()
        self.assertIsNone(nothing)

        # save a table
        ver1 = wf_module.store_fetched_table(table1)
        wf_module.save()
        wf_module.refresh_from_db()
        self.assertNotEqual(wf_module.stored_data_version, ver1) # should not switch versions by itself
        self.assertEqual(len(wf_module.list_fetched_data_versions()), 1)

        # try saving it again, should be NOP
        verdup = wf_module.store_fetched_table_if_different(table1)
        self.assertIsNone(verdup)
        self.assertEqual(len(wf_module.list_fetched_data_versions()), 1)

        # save something different now, should create new version
        ver2 = wf_module.store_fetched_table_if_different(table2)
        wf_module.save()
        wf_module.refresh_from_db()
        self.assertNotEqual(ver2, ver1)
        self.assertNotEqual(wf_module.stored_data_version, ver2) # should not switch versions by itself
        self.assertEqual(len(wf_module.list_fetched_data_versions()), 2)
        wf_module.stored_data_version = ver2
        wf_module.save()
        tableout2 = wf_module.retrieve_fetched_table()
        self.assertTrue(tableout2.equals(table2))

    def test_wf_module_duplicate(self):
        workflow = Workflow.create_and_init()
        wfm1 = workflow.tabs.first().wf_modules.create(order=0)

        # store data to test that it is duplicated
        s1 = wfm1.store_fetched_table(mock_csv_table)
        s2 = wfm1.store_fetched_table(mock_csv_table2)
        wfm1.secrets = {'do not copy': {'name': 'evil', 'secret': 'evil'}}
        wfm1.stored_data_version = s2
        wfm1.save()
        self.assertEqual(len(wfm1.list_fetched_data_versions()), 2)

        # duplicate into another workflow, as we would do when duplicating a workflow
        workflow2 = Workflow.create_and_init()
        tab2 = workflow2.tabs.first()
        wfm1d = wfm1.duplicate(tab2)
        wfm1d.refresh_from_db()  # test what we actually have in the db

        self.assertEqual(wfm1d.workflow, workflow2)
        self.assertEqual(wfm1d.module_version, wfm1.module_version)
        self.assertEqual(wfm1d.order, wfm1.order)
        self.assertEqual(wfm1d.notes, wfm1.notes)
        self.assertEqual(wfm1d.last_update_check, wfm1.last_update_check)
        self.assertEqual(wfm1d.is_collapsed, wfm1.is_collapsed)
        self.assertEqual(wfm1d.stored_data_version, wfm1.stored_data_version)
        self.assertEqual(wfm1d.params, wfm1.params)
        self.assertEqual(wfm1d.secrets, {})

        # Stored data should contain a clone of content only, not complete version history
        self.assertIsNotNone(wfm1d.stored_data_version)
        self.assertEqual(wfm1d.stored_data_version, wfm1.stored_data_version)
        self.assertTrue(wfm1d.retrieve_fetched_table().equals(wfm1.retrieve_fetched_table()))
        self.assertEqual(len(wfm1d.list_fetched_data_versions()), 1)

    def test_wf_module_duplicate_disable_auto_update(self):
        """
        Duplicates should be lightweight by default: no auto-updating.
        """
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(order=0, auto_update_data=True,
                                          next_update=timezone.now(),
                                          update_interval=600)

        workflow2 = Workflow.create_and_init()
        InitWorkflowCommand.create(workflow2)
        tab2 = workflow2.tabs.create(position=0)
        wf_module2 = wf_module.duplicate(tab2)

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
            order=0,
            secrets={'auth': {'name': 'x', 'secret': 'y'}}
        )

        workflow2 = Workflow.create_and_init()
        tab2 = workflow2.tabs.first()
        wf_module2 = wf_module.duplicate(tab2)

        self.assertEqual(wf_module2.secrets, {})

    def test_wf_module_duplicate_copy_uploaded_file(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            module_id_name='upload',
        )
        uuid = str(uuidgen.uuid4())
        key = f'{wf_module.uploaded_file_prefix}{uuid}.csv'
        minio.put_bytes(minio.UserFilesBucket, key, b'1234567')
        # Write the uuid to the old module -- we'll check the new module points
        # to a valid file
        wf_module.params = {'file': uuid, 'has_header': True}
        wf_module.save(update_fields=['params'])
        uploaded_file = wf_module.uploaded_files.create(
            name='t.csv',
            uuid=uuid,
            bucket=minio.UserFilesBucket,
            key=key,
            size=7,
        )

        workflow2 = Workflow.create_and_init()
        tab2 = workflow2.tabs.first()
        wf_module2 = wf_module.duplicate(tab2)

        uploaded_file2 = wf_module2.uploaded_files.first()
        self.assertIsNotNone(uploaded_file2)
        # New file gets same uuid -- because it's the same file and we don't
        # want to edit params during copy
        self.assertEqual(uploaded_file2.uuid, uuid)
        self.assertEqual(wf_module2.params['file'], uuid)
        self.assertTrue(
            # The new file should be in a different path
            uploaded_file2.key.startswith(wf_module2.uploaded_file_prefix)
        )
        self.assertEqual(uploaded_file2.name, 't.csv')
        self.assertEqual(uploaded_file2.size, 7)
        self.assertEqual(uploaded_file2.created_at, uploaded_file.created_at)
        self.assertEqual(
            minio.get_object_with_data(uploaded_file2.bucket,
                                       uploaded_file2.key)['Body'],
            b'1234567'
        )

    def test_wf_module_duplicate_copy_only_selected_uploaded_file(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            module_id_name='upload',
        )
        uuid1 = str(uuidgen.uuid4())
        key1 = f'{wf_module.uploaded_file_prefix}{uuid1}.csv'
        minio.put_bytes(minio.UserFilesBucket, key1, b'1234567')
        uuid2 = str(uuidgen.uuid4())
        key2 = f'{wf_module.uploaded_file_prefix}{uuid2}.csv'
        minio.put_bytes(minio.UserFilesBucket, key2, b'7654321')
        uuid3 = str(uuidgen.uuid4())
        key3 = f'{wf_module.uploaded_file_prefix}{uuid3}.csv'
        minio.put_bytes(minio.UserFilesBucket, key3, b'9999999')
        uploaded_file1 = wf_module.uploaded_files.create(
            name='t1.csv',
            uuid=uuid1,
            bucket=minio.UserFilesBucket,
            key=key1,
            size=7,
        )
        uploaded_file2 = wf_module.uploaded_files.create(
            name='t2.csv',
            uuid=uuid2,
            bucket=minio.UserFilesBucket,
            key=key2,
            size=7,
        )
        uploaded_file3 = wf_module.uploaded_files.create(
            name='t3.csv',
            uuid=uuid3,
            bucket=minio.UserFilesBucket,
            key=key3,
            size=7,
        )
        # Write the _middle_ uuid to the old module -- proving that we aren't
        # selecting by ordering
        wf_module.params = {'file': uuid2, 'has_header': True}
        wf_module.save(update_fields=['params'])

        workflow2 = Workflow.create_and_init()
        tab2 = workflow2.tabs.first()
        wf_module2 = wf_module.duplicate(tab2)

        self.assertEqual(wf_module2.uploaded_files.count(), 1)
        new_uf = wf_module2.uploaded_files.first()
        self.assertEqual(new_uf.uuid, uuid2)

    def test_module_version_lookup(self):
        workflow = Workflow.create_and_init()
        module_version = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'floob',
            'name': 'Floob',
            'category': 'Clean',
            'parameters': []
        })
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name='floob'
        )
        self.assertEqual(wf_module.module_version, module_version)
        # white-box testing: test that we work even from cache
        self.assertEqual(wf_module.module_version, module_version)

    def test_module_version_missing(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name='floob'
        )
        self.assertIsNone(wf_module.module_version)

    def test_delete_inprogress_file_upload(self):
        workflow = Workflow.create_and_init()
        upload_id = minio.create_multipart_upload(minio.UserFilesBucket, 'key', 'file.csv')
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            inprogress_file_upload_id=upload_id,
            inprogress_file_upload_key='key',
            inprogress_file_upload_last_accessed_at=timezone.now(),
        )
        wf_module.delete()
        # Assert the upload is gone
        with self.assertRaises(minio.error.NoSuchUpload):
            minio.client.list_parts(Bucket=minio.UserFilesBucket, Key='key',
                                    UploadId=upload_id)

    def test_delete_ignore_inprogress_file_upload_not_on_s3(self):
        workflow = Workflow.create_and_init()
        upload_id = minio.create_multipart_upload(minio.UserFilesBucket, 'key', 'file.csv')
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            inprogress_file_upload_id=upload_id,
            inprogress_file_upload_key='key',
            inprogress_file_upload_last_accessed_at=timezone.now(),
        )
        # Delete from S3, and then delete.
        #
        # This mimics a behavior we want: upload timeouts. We can set up a
        # S3-side policy to delete old uploaded data; we need to expect that
        # data might be deleted when we delete the WfModule.
        minio.abort_multipart_upload(minio.UserFilesBucket, 'key', upload_id)
        wf_module.delete()  # do not crash

    def test_delete_remove_uploaded_data_by_prefix_in_case_model_missing(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0
        )
        uuid = str(uuidgen.uuid4())
        key = wf_module.uploaded_file_prefix + uuid
        minio.put_bytes(minio.UserFilesBucket, key, b'A\n1')
        # Don't create the UploadedFile. Simulates races during upload/delete
        # that could write a file on S3 but not in our database.
        #wf_module.uploaded_files.create(name='t.csv', size=3, uuid=uuid,
        #                                bucket=minio.UserFilesBucket, key=key)
        wf_module.delete()  # do not crash
        with self.assertRaises(FileNotFoundError):
            with minio.RandomReadMinioFile(minio.UserFilesBucket, key) as f:
                f.read()
