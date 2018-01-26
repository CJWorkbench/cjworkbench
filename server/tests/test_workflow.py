from django.test import TestCase
from server.tests.utils import *


class WorkflowTests(LoggedInTestCase):
    def setUp(self):
        super(WorkflowTests, self).setUp()

        # Add another user, with one public and one private workflow
        self.otheruser = User.objects.create(username='user2', email='user2@users.com', password='password')
        self.other_workflow_private = Workflow.objects.create(name="Other workflow private", owner=self.otheruser)
        self.other_workflow_public = Workflow.objects.create(name="Other workflow public", owner=self.otheruser, public=True)

    def test_workflow_duplicate(self):
        # Create workflow with two WfModules
        wf1 = create_testdata_workflow()
        self.assertNotEqual(wf1.owner, self.otheruser) # should owned by user created by LoggedInTestCase
        module_version1 = add_new_module_version('Module 1')
        add_new_wf_module(wf1, module_version1, 1) # order=1
        self.assertEqual(WfModule.objects.filter(workflow=wf1).count(), 2)

        wf2 = wf1.duplicate(self.otheruser)

        self.assertNotEqual(wf1.id, wf2.id)
        self.assertEqual(wf2.owner, self.otheruser)
        self.assertEqual(wf2.name, "Copy of " + wf1.name)
        self.assertIsNone(wf2.last_delta)  # no undo history
        self.assertFalse(wf2.public)
        self.assertEqual(WfModule.objects.filter(workflow=wf1).count(), WfModule.objects.filter(workflow=wf2).count())
