from django.test import TestCase
from server.versions import *
from server.tests.utils import  *
from django.conf import settings
from django.test import override_settings

class VersionTests(TestCase):

    def setUp(self):
        self.wfm = load_and_add_module('loadurl')

    def test_store_if_changed(self):
        table = mock_csv_table.copy()
        save_fetched_table_if_changed(self.wfm, table)
        self.assertEqual(StoredObject.objects.count(), 1)

        # store same table again, should not create a new one
        save_fetched_table_if_changed(self.wfm, table)
        self.assertEqual(StoredObject.objects.count(), 1)

        # changed table should create new
        table = table.append(table, ignore_index=True)
        save_fetched_table_if_changed(self.wfm, table)
        self.assertEqual(StoredObject.objects.count(), 2)


    @override_settings(MAX_STORAGE_PER_MODULE=10000)
    def test_storage_limits(self):
        table = mock_csv_table.copy()

        for i in range(0, 10):
            save_fetched_table_if_changed(self.wfm, table)

            # make the table bigger, forcing a new object to be created and mimicking real world usage
            table = table.append(table, ignore_index=True)

            total_size = sum(StoredObject.objects.filter(wf_module=self.wfm).values_list('size', flat=True))

            # we can break the limit if there is only one SO, because we always allow the last verion to be stored
            count = StoredObject.objects.count()
            if count > 1:
                self.assertLessEqual(total_size, settings.MAX_STORAGE_PER_MODULE)

            # this test should always end up creating more than one stored object at some point
            if i==1:
                self.assertEqual(count, 2)

        # test should have made the able big enoug to force there to be only one version, eventually
        # if not, increase table size/loop iterations, or decrease limit
        self.assertEqual(StoredObject.objects.count(), 1)