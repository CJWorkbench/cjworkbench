import logging
import unittest
from unittest.mock import patch
import uuid
from django.contrib.auth.models import User
from cjwstate import commands, minio
from cjwstate.models.workflow import Workflow, DependencyGraph
from cjwstate.models.commands import InitWorkflow, AddStep, SetWorkflowTitle
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)


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
        return MockRequest(user, "user-" + user.username)

    @staticmethod
    def anonymous(session_key):
        return MockRequest(None, session_key)

    @staticmethod
    def uninitialized():
        return MockRequest(None, None)


class WorkflowTests(DbTestCaseWithModuleRegistryAndMockKernel):
    def setUp(self):
        super().setUp()

        self.alice = User.objects.create(username="a", email="a@example.org")
        self.bob = User.objects.create(username="b", email="b@example.org")

    def test_delete_with_report_blocks(self):
        workflow = Workflow.create_and_init(name="Foo", has_custom_report=True)
        tab = workflow.tabs.first()
        step = tab.steps.create(order=0, module_id_name="something")
        workflow.blocks.create(
            position=0, slug="block-tab", block_type="Table", tab_id=tab.id
        )
        workflow.blocks.create(
            position=1, slug="block-step", block_type="Chart", step_id=step.id
        )

        workflow.delete()

    def test_workflow_duplicate(self):
        # Create workflow with two Steps
        wf1 = Workflow.create_and_init(name="Foo")
        tab = wf1.tabs.first()
        tab.steps.create(order=0, slug="step-1", module_id_name="x")

        wf2 = wf1.duplicate(self.bob)

        self.assertNotEqual(wf1.id, wf2.id)
        self.assertEqual(wf2.owner, self.bob)
        self.assertEqual(wf2.name, "Copy of Foo")
        self.assertEqual(wf2.deltas.all().count(), 1)
        self.assertEqual(wf2.last_delta.command_name, InitWorkflow.__name__)
        self.assertFalse(wf2.public)
        self.assertEqual(wf1.tabs.first().steps.count(), wf2.tabs.first().steps.count())

    def test_duplicate_custom_report(self):
        workflow = Workflow.create_and_init(name="Foo", has_custom_report=True)
        tab = workflow.tabs.first()
        step = tab.steps.create(order=0, module_id_name="something")
        workflow.blocks.create(
            position=0, slug="block-text", block_type="Text", text_markdown="hi"
        )
        workflow.blocks.create(
            position=1, slug="block-tab", block_type="Table", tab_id=tab.id
        )
        workflow.blocks.create(
            position=2, slug="block-step", block_type="Chart", step_id=step.id
        )
        workflow2 = workflow.duplicate(self.bob)
        self.assertEqual(workflow2.has_custom_report, True)
        blocks = list(workflow2.blocks.all())
        self.assertEqual(blocks[0].text_markdown, "hi")
        self.assertEqual(blocks[1].tab_id, workflow2.tabs.first().id)
        self.assertEqual(blocks[2].step_id, workflow2.tabs.first().steps.first().id)

    def test_auth_shared_workflow(self):
        wf = Workflow.objects.create(owner=self.alice, public=True)

        # Read: anybody
        self.assertTrue(wf.request_authorized_read(MockRequest.logged_in(self.alice)))
        self.assertTrue(wf.request_authorized_read(MockRequest.logged_in(self.bob)))
        self.assertTrue(wf.request_authorized_read(MockRequest.anonymous("session1")))
        self.assertTrue(wf.request_authorized_read(MockRequest.uninitialized()))

        # Write: only owner
        self.assertTrue(wf.request_authorized_write(MockRequest.logged_in(self.alice)))
        self.assertFalse(wf.request_authorized_write(MockRequest.logged_in(self.bob)))
        self.assertFalse(wf.request_authorized_write(MockRequest.anonymous("session1")))
        self.assertFalse(wf.request_authorized_write(MockRequest.uninitialized()))

    def test_auth_private_workflow(self):
        wf = Workflow.objects.create(owner=self.alice, public=False)

        # Read: anybody
        self.assertTrue(wf.request_authorized_read(MockRequest.logged_in(self.alice)))
        self.assertFalse(wf.request_authorized_read(MockRequest.logged_in(self.bob)))
        self.assertFalse(wf.request_authorized_read(MockRequest.anonymous("session1")))
        self.assertFalse(wf.request_authorized_read(MockRequest.uninitialized()))

        # Write: only owner
        self.assertTrue(wf.request_authorized_write(MockRequest.logged_in(self.alice)))
        self.assertFalse(wf.request_authorized_write(MockRequest.logged_in(self.bob)))
        self.assertFalse(wf.request_authorized_write(MockRequest.anonymous("session1")))
        self.assertFalse(wf.request_authorized_write(MockRequest.uninitialized()))

    def test_auth_anonymous_workflow(self):
        wf = Workflow.objects.create(
            owner=None, anonymous_owner_session_key="session1", public=False
        )

        # Read: just the anonymous user, logged in or not
        self.assertTrue(wf.request_authorized_read(MockRequest.anonymous("session1")))
        self.assertTrue(wf.request_authorized_read(MockRequest(self.alice, "session1")))
        self.assertFalse(wf.request_authorized_read(MockRequest.logged_in(self.alice)))
        self.assertFalse(wf.request_authorized_read(MockRequest.anonymous("session2")))
        self.assertFalse(wf.request_authorized_read(MockRequest.uninitialized()))

        # Write: ditto
        self.assertTrue(wf.request_authorized_write(MockRequest.anonymous("session1")))
        self.assertTrue(
            wf.request_authorized_write(MockRequest(self.alice, "session1"))
        )
        self.assertFalse(wf.request_authorized_write(MockRequest.logged_in(self.alice)))
        self.assertFalse(wf.request_authorized_write(MockRequest.anonymous("session2")))
        self.assertFalse(wf.request_authorized_read(MockRequest.uninitialized()))

    @patch.object(commands, "queue_render", async_noop)
    @patch.object(commands, "websockets_notify", async_noop)
    def test_delete_deltas_without_init_delta(self):
        workflow = Workflow.objects.create(name="A")
        tab = workflow.tabs.create(position=0)
        workflow.delete()
        self.assertTrue(True)  # no crash

    def test_delete_remove_leaked_stored_objects_and_uploaded_files(self):
        workflow = Workflow.create_and_init()
        # If the user deletes a workflow, all data associated with that
        # workflow should disappear. Postgres handles DB objects; but Django's
        # ORM doesn't do a great job with StoredObjects and UploadedFiles.
        #
        # This test isn't about minutae. It's just: if the user deletes a
        # Workflow, make sure all data gets deleted.
        #
        # TODO fix all other bugs that leak data.
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="x"
        )

        # "Leak" a StoredObject by writing its file to S3 but neglecting to
        # write an accompanying StoredObject record.
        stored_object_key = f"{workflow.id}/{step.id}/1234.dat"
        minio.put_bytes(minio.StoredObjectsBucket, stored_object_key, b"1234")

        # Add UploadedFile, missing a DB entry. (Even if we fix all bugs that
        # leak an S3 object after deleting a DB entry [and 2019-06-03 there are
        # still more] we'll still need to handle missing DB entries from legacy
        # code.)
        uploaded_file_key = f"{step.uploaded_file_prefix}{uuid.uuid4()}.csv"
        minio.put_bytes(minio.UserFilesBucket, uploaded_file_key, b"A\nb")
        workflow.delete()
        self.assertFalse(minio.exists(minio.StoredObjectsBucket, stored_object_key))
        self.assertFalse(minio.exists(minio.UserFilesBucket, uploaded_file_key))


class SimpleDependencyGraphTests(unittest.TestCase):
    Graph = DependencyGraph
    Tab = Graph.Tab
    Step = Graph.Step

    def test_recursing_tab_finds_earlier_ids(self):
        graph = self.Graph(
            [self.Tab("tab-1", [1, 2, 3])],
            {1: self.Step(set()), 2: self.Step(set(["tab-1"])), 3: self.Step(set())},
        )
        result = graph.get_step_ids_depending_on_tab_slug("tab-1")
        self.assertEqual(result, [2, 3])

    def test_no_tab_dependencies(self):
        graph = self.Graph(
            [self.Tab("tab-1", [1]), self.Tab("tab-2", [2])],
            {1: self.Step(set()), 2: self.Step(set())},
        )
        result = graph.get_step_ids_depending_on_tab_slug("tab-1")
        self.assertEqual(result, [])

    def test_recurse(self):
        graph = self.Graph(
            [self.Tab("tab-1", [1]), self.Tab("tab-2", [2]), self.Tab("tab-3", [3])],
            {
                1: self.Step(set(["tab-2"])),
                2: self.Step(set(["tab-3"])),
                3: self.Step(set()),
            },
        )
        result = graph.get_step_ids_depending_on_tab_slug("tab-3")
        self.assertEqual(result, [1, 2])

    def test_recurse_cycle(self):
        graph = self.Graph(
            [self.Tab("tab-1", [1]), self.Tab("tab-2", [2]), self.Tab("tab-3", [3])],
            {
                1: self.Step(set(["tab-2"])),
                2: self.Step(set(["tab-3"])),
                3: self.Step(set(["tab-1"])),
            },
        )
        result = graph.get_step_ids_depending_on_tab_slug("tab-3")
        self.assertEqual(result, [1, 2, 3])

    def test_exclude_steps_before_dependent_one(self):
        graph = self.Graph(
            [self.Tab("tab-1", [1]), self.Tab("tab-2", [2, 3])],
            {1: self.Step(set()), 2: self.Step(set()), 3: self.Step(set(["tab-1"]))},
        )
        result = graph.get_step_ids_depending_on_tab_slug("tab-1")
        self.assertEqual(result, [3])

    def test_include_steps_after_dependent_one(self):
        graph = self.Graph(
            [self.Tab("tab-1", [1]), self.Tab("tab-2", [2, 3])],
            {1: self.Step(set()), 2: self.Step(set(["tab-1"])), 3: self.Step(set())},
        )
        result = graph.get_step_ids_depending_on_tab_slug("tab-1")
        self.assertEqual(result, [2, 3])


class DependencyGraphTests(DbTestCaseWithModuleRegistryAndMockKernel):
    def test_read_graph_happy_path(self):
        workflow = Workflow.objects.create()
        tab1 = workflow.tabs.create(position=0, slug="tab-1")
        tab2 = workflow.tabs.create(position=1, slug="tab-2")

        create_module_zipfile(
            "simple", spec_kwargs={"parameters": [{"id_name": "str", "type": "string"}]}
        )
        create_module_zipfile(
            "tabby", spec_kwargs={"parameters": [{"id_name": "tab", "type": "tab"}]}
        )

        step1 = tab1.steps.create(
            order=0, slug="step-1", module_id_name="simple", params={"str": "A"}
        )
        step2 = tab1.steps.create(
            order=1, slug="step-2", module_id_name="tabby", params={"tab": "tab-2"}
        )
        step3 = tab2.steps.create(
            order=0, slug="step-3", module_id_name="simple", params={"str": "B"}
        )

        self.kernel.migrate_params.side_effect = lambda m, p: p  # return input
        with self.assertLogs(level=logging.INFO):
            graph = DependencyGraph.load_from_workflow(workflow)
        self.assertEqual(
            graph.tabs,
            [
                DependencyGraph.Tab("tab-1", [step1.id, step2.id]),
                DependencyGraph.Tab("tab-2", [step3.id]),
            ],
        )
        self.assertEqual(
            graph.steps,
            {
                step1.id: DependencyGraph.Step(set()),
                step2.id: DependencyGraph.Step(set(["tab-2"])),
                step3.id: DependencyGraph.Step(set()),
            },
        )
