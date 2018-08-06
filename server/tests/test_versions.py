from django.conf import settings
from django.test import TestCase, override_settings
from server.models.StoredObject import StoredObject
from server.modules.types import ProcessResult
from server.tests.utils import load_and_add_module, mock_csv_table
from server.versions import save_result_if_changed


class VersionTests(TestCase):
    def setUp(self):
        self.wfm = load_and_add_module('loadurl')

    def test_store_if_changed(self):
        table = mock_csv_table.copy()
        save_result_if_changed(self.wfm, ProcessResult(table))
        self.assertEqual(StoredObject.objects.count(), 1)

        # store same table again, should not create a new one
        save_result_if_changed(self.wfm, ProcessResult(table))
        self.assertEqual(StoredObject.objects.count(), 1)

        # changed table should create new
        table = table.append(table, ignore_index=True)
        save_result_if_changed(self.wfm, ProcessResult(table))
        self.assertEqual(StoredObject.objects.count(), 2)

    @override_settings(MAX_STORAGE_PER_MODULE=1000)
    def test_storage_limits(self):
        table = mock_csv_table
        stored_objects = self.wfm.stored_objects  # not queried yet

        for i in range(0, 4):
            # double table size, mimicking real-world growth of a table (but
            # faster)
            table = table.append(table, ignore_index=True)
            save_result_if_changed(self.wfm, ProcessResult(table))

            total_size = sum(stored_objects.values_list('size', flat=True))
            self.assertLessEqual(total_size, settings.MAX_STORAGE_PER_MODULE)

        n_objects = stored_objects.count()
        # test should have made the able big enoug to force there to be only
        # one version, eventually.
        # if not, increase table size/loop iterations, or decrease limit
        self.assertEqual(n_objects, 1)
