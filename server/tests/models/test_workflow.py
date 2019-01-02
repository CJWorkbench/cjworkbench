from unittest.mock import patch
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from server.models import ModuleVersion, Workflow
from server.models.commands import InitWorkflowCommand, AddModuleCommand, \
        ChangeWorkflowTitleCommand
from server.models.loaded_module import LoadedModule
from server.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


class MockSession:
    def __init__(self, session_key):
        self.session_key = session_key


class MockRequest:
    def __init__(self, user, session_key):
        self.user = user
        self.session = MockSession(session_key)

    @staticmethod
    def logged_in(user):
        return MockRequest(user, 'user-' + user.username)

    @staticmethod
    def anonymous(session_key):
        return MockRequest(None, session_key)

    @staticmethod
    def uninitialized():
        return MockRequest(None, None)


class WorkflowTests(DbTestCase):
    def setUp(self):
        super().setUp()

        self.alice = User.objects.create(username='a', email='a@example.org')
        self.bob = User.objects.create(username='b', email='b@example.org')

    def test_workflow_duplicate(self):
        # Create workflow with two WfModules
        wf1 = Workflow.create_and_init(name='Foo')
        tab = wf1.tabs.first()
        tab.wf_modules.create(order=0, module_id_name='x')

        wf2 = wf1.duplicate(self.bob)

        self.assertNotEqual(wf1.id, wf2.id)
        self.assertEqual(wf2.owner, self.bob)
        self.assertEqual(wf2.name, 'Copy of Foo')
        self.assertEqual(wf2.deltas.all().count(), 1)
        self.assertIsInstance(wf2.last_delta, InitWorkflowCommand)
        self.assertFalse(wf2.public)
        self.assertEqual(wf1.tabs.first().wf_modules.count(),
                         wf2.tabs.first().wf_modules.count())

    def test_auth_shared_workflow(self):
        wf = Workflow.objects.create(owner=self.alice, public=True)

        # Read: anybody
        self.assertTrue(wf.request_authorized_read(MockRequest.logged_in(self.alice)))
        self.assertTrue(wf.request_authorized_read(MockRequest.logged_in(self.bob)))
        self.assertTrue(wf.request_authorized_read(MockRequest.anonymous('session1')))
        self.assertTrue(wf.request_authorized_read(MockRequest.uninitialized()))

        # Write: only owner
        self.assertTrue(wf.request_authorized_write(MockRequest.logged_in(self.alice)))
        self.assertFalse(wf.request_authorized_write(MockRequest.logged_in(self.bob)))
        self.assertFalse(wf.request_authorized_write(MockRequest.anonymous('session1')))
        self.assertFalse(wf.request_authorized_write(MockRequest.uninitialized()))

    def test_auth_private_workflow(self):
        wf = Workflow.objects.create(owner=self.alice, public=False)

        # Read: anybody
        self.assertTrue(wf.request_authorized_read(MockRequest.logged_in(self.alice)))
        self.assertFalse(wf.request_authorized_read(MockRequest.logged_in(self.bob)))
        self.assertFalse(wf.request_authorized_read(MockRequest.anonymous('session1')))
        self.assertFalse(wf.request_authorized_read(MockRequest.uninitialized()))

        # Write: only owner
        self.assertTrue(wf.request_authorized_write(MockRequest.logged_in(self.alice)))
        self.assertFalse(wf.request_authorized_write(MockRequest.logged_in(self.bob)))
        self.assertFalse(wf.request_authorized_write(MockRequest.anonymous('session1')))
        self.assertFalse(wf.request_authorized_write(MockRequest.uninitialized()))

    def test_auth_anonymous_workflow(self):
        wf = Workflow.objects.create(owner=None,
                                     anonymous_owner_session_key='session1',
                                     public=False)

        # Read: just the anonymous user, logged in or not
        self.assertTrue(wf.request_authorized_read(MockRequest.anonymous('session1')))
        self.assertTrue(wf.request_authorized_read(MockRequest(self.alice, 'session1')))
        self.assertFalse(wf.request_authorized_read(MockRequest.logged_in(self.alice)))
        self.assertFalse(wf.request_authorized_read(MockRequest.anonymous('session2')))
        self.assertFalse(wf.request_authorized_read(MockRequest.uninitialized()))

        # Write: ditto
        self.assertTrue(wf.request_authorized_write(MockRequest.anonymous('session1')))
        self.assertTrue(wf.request_authorized_write(MockRequest(self.alice, 'session1')))
        self.assertFalse(wf.request_authorized_write(MockRequest.logged_in(self.alice)))
        self.assertFalse(wf.request_authorized_write(MockRequest.anonymous('session2')))
        self.assertFalse(wf.request_authorized_read(MockRequest.uninitialized()))

    @patch('server.rabbitmq.queue_render', async_noop)
    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync',
           lambda *args: LoadedModule('', ''))
    def test_delete_deltas_without_init_delta(self):
        workflow = Workflow.objects.create(name='A')
        tab = workflow.tabs.create(position=0)
        async_to_sync(ChangeWorkflowTitleCommand.create)(
            workflow=workflow,
            new_value='B'
        )
        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x',
            'name': 'x',
            'category': 'x',
            'parameters': [],
        })
        async_to_sync(AddModuleCommand.create)(workflow=workflow, tab=tab,
                                               module_id_name='x', position=0,
                                               param_values={})
        async_to_sync(ChangeWorkflowTitleCommand.create)(
            workflow=workflow,
            new_value='C'
        )
        workflow.delete()
        self.assertTrue(True)  # no crash
