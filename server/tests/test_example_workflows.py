from server.tests.utils import *
from server.models import User, Workflow

class ExecuteTests(TestCase):

    def test_example_workflows(self):
        wf = create_testdata_workflow()

        # Creating a test workflow also created a user, because you can't have a wf without a user
        # But that shouldn't have copied anything, yet
        self.assertEqual(Workflow.objects.count(), 1)

        # Creating a new user... should also not create any new wf, yet
        user2 = User.objects.create_user(username='user2', password='user2_password')
        self.assertEqual(Workflow.objects.count(), 1)

        # Now we set this wf to public and ensure we get a copy when a new account is created
        wf.example = True
        wf.save()
        user3 = User.objects.create_user(username='user3', password='user3_password')
        self.assertEqual(Workflow.objects.count(), 2)
        u3wf = Workflow.objects.filter(owner=user3).first()
        self.assertEqual(u3wf.name, wf.name)  # should not have 'Copy of'

