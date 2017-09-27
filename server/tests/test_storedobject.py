from django.test import TestCase
from server.models import StoredObject
from server.tests.utils import *

class StoredObjectTests(TestCase):

    def setUp(self):
        self.workflow = create_testdata_workflow()
        self.wfm1 = WfModule.objects.first()
        self.wfm2 = add_new_wf_module(self.workflow, ModuleVersion.objects.first(), 1)  # order = 1

    def test_duplicate(self):
        # Duplicate from one wfm to another, tests the typical WfModule duplication case
        so1 = StoredObject.create(self.wfm1, "Stored Text")
        so2 = so1.duplicate(self.wfm2)

        # new StoredObject should have same time, different file with same contents
        self.assertEqual(so1.stored_at, so2.stored_at)
        self.assertNotEqual(so1.file, so2.file)
        self.assertEqual(so1.get_data(), so2.get_data())
