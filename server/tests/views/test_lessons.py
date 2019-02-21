import asyncio
from typing import Any, Dict, List
from unittest.mock import patch
from server.models import Workflow, ModuleVersion, LoadedModule
from server.models.lesson import Lesson, LessonHeader, LessonFooter, \
        LessonInitialWorkflow
from server.tests.utils import DbTestCase, create_test_user


async def async_noop(*args, **kwargs):
    pass


future_none = asyncio.Future()
future_none.set_result(None)


class MockLoadedModule():
    """Make a valid migrate_params()"""
    def migrate_params(self, schema, params):
        return params


def create_module_version(id_name: str, parameters: List[Dict[str, Any]],
                          **kwargs):
    ModuleVersion.create_or_replace_from_spec({
        'id_name': id_name,
        'name': 'something',
        'category': 'Clean',
        'parameters': parameters,
        **kwargs
    })


@patch.object(LoadedModule, 'for_module_version_sync',
              lambda x: MockLoadedModule())
class LessonDetailTests(DbTestCase):
    def log_in(self):
        self.user = create_test_user()
        self.client.force_login(self.user)

    @property
    def other_user(self):
        # User created on first access
        if not hasattr(self, '_other_user'):
            self._other_user = create_test_user('attacker', 'bad@example.org',
                                                'alksjdghalskdjfh')
        return self._other_user

    def test_get_anonymous(self):
        response = self.client.get('/lessons/load-public-data/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed('workflow.html')
        self.assertEqual(Workflow.objects.count(), 1)

    def test_get_invalid_slug(self):
        self.log_in()
        response = self.client.get('/lessons/load-public-dat-whoops-a-typooo/')
        self.assertEqual(response.status_code, 404)

    def test_get_missing_workflow(self):
        self.log_in()

        # Add non-matching Workflows -- to test we _don't_ load them
        Workflow.objects.create(owner=self.user,
                                lesson_slug='some-other-lesson')
        Workflow.objects.create(owner=self.user, lesson_slug=None)
        Workflow.objects.create(owner=self.other_user,
                                lesson_slug='load-public-data', public=True)

        # This should create the workflow
        response = self.client.get('/lessons/load-public-data/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed('workflow.html')
        self.assertEqual(Workflow.objects.count(), 4)

    def test_get_lesson_with_workflow(self):
        self.log_in()

        Workflow.objects.create(owner=self.user,
                                lesson_slug='load-public-data')
        response = self.client.get('/lessons/load-public-data/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed('workflow.html')

    def test_get_course_lesson_with_workflow(self):
        self.log_in()

        Workflow.objects.create(
            owner=self.user,
            lesson_slug='intro-to-data-journalism/filter'
        )
        response = self.client.get('/courses/intro-to-data-journalism/filter')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed('workflow.html')

    def test_get_without_login(self):
        response = self.client.get('/lessons/load-public-data/')
        self.assertEqual(Workflow.objects.count(), 1)

    def test_get_with_existing(self):
        self.log_in()
        Workflow.objects.create(owner=self.user,
                                lesson_slug='load-public-data')
        response = self.client.get('/lessons/load-public-data/')
        self.assertEqual(Workflow.objects.count(), 1)  # don't create duplicate

    def test_get_without_existing(self):
        self.log_in()

        # Add non-matching Workflows -- to test we ignore them
        Workflow.objects.create(owner=self.user, lesson_slug='other-lesson')
        Workflow.objects.create(owner=self.user, lesson_slug=None)
        Workflow.objects.create(owner=self.other_user,
                                lesson_slug='load-public-data', public=True)

        response = self.client.post('/lessons/load-public-data/')
        self.assertEqual(Workflow.objects.count(), 4)  # create Workflow
        self.assertEqual(
            Workflow.objects.filter(lesson_slug='load-public-data').count(),
            2
        )
        workflow = Workflow.objects.get(lesson_slug='load-public-data',
                                        owner=self.user)
        # Assert the workflow is created with a valid Tab
        tab1 = workflow.tabs.first()
        self.assertEqual(tab1.slug, 'tab-1')
        self.assertEqual(tab1.name, 'Tab 1')

    # The next three tests are of GET /workflows/:id/. They're here, not there,
    # to keep canonical-URL tests in one file.
    #
    # We're testing that the rules are:
    # * GET /workflows/:id/ when the wf has lesson_slug=...: redirect to lesson (the user already started this lesson)
    # * GET /workflows/:id/ when the wf is not a lesson (lesson_slug==None): display wf as usual
    # * GET /lessons/:slug/ when there is a wf with that slug (user has already started lesson): display, with 'lesson'
    def test_get_workflow_with_lesson_slug(self):
        self.log_in()

        workflow = Workflow.objects.create(owner=self.user,
                                           lesson_slug='load-public-data')
        response = self.client.get(workflow.get_absolute_url())
        self.assertRedirects(response, '/lessons/load-public-data/')

    def test_get_public_workflow_with_lesson_slug(self):
        self.log_in()

        workflow = Workflow.objects.create(owner=self.other_user,
                                           lesson_slug='load-public-data',
                                           public=True)  # not 404
        workflow.save()
        response = self.client.get(workflow.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed('workflow.html')

    def test_get_workflow_with_missing_lesson_slug(self):
        self.log_in()

        workflow = Workflow.objects.create(owner=self.user,
                                           lesson_slug='missing-lesson')
        response = self.client.get(workflow.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed('workflow.html')

    def test_get_workflow_with_missing_course_lesson_slug(self):
        self.log_in()

        workflow = Workflow.objects.create(owner=self.user,
                                           lesson_slug='course/missing-lesson')
        response = self.client.get(workflow.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed('workflow.html')

    def test_get_workflow_with_course_slug(self):
        self.log_in()
        workflow = Workflow.objects.create(
            owner=self.user,
            lesson_slug='intro-to-data-journalism/filter'
        )
        response = self.client.get(workflow.get_absolute_url())
        self.assertRedirects(
            response,
            '/courses/intro-to-data-journalism/filter'
        )

    @patch('server.rabbitmq.queue_render')
    @patch.object(Lesson.objects, 'get')
    def test_create_initial_workflow(self, get, render):
        get.return_value = Lesson('slug',
                                  initial_workflow=LessonInitialWorkflow([
            {
                'name': 'Tab X',
                'wfModules': [
                    {
                        'module': 'amodule',
                        'params': {'foo': 'bar'},
                    },
                ],
            },
        ]))

        render.return_value = future_none

        create_module_version('amodule', [
            {'id_name': 'foo', 'type': 'string'},
        ], loads_data=False)

        self.log_in()
        response = self.client.get('/lessons/whatever')
        state = response.context_data['initState']
        tabs = state['tabs']
        tab1 = list(tabs.values())[0]
        self.assertEqual(tab1['slug'], 'tab-1')
        self.assertEqual(tab1['name'], 'Tab X')
        wf_modules = state['wfModules']
        wfm1 = list(wf_modules.values())[0]
        self.assertEqual(wfm1['module'], 'amodule')
        self.assertEqual(wfm1['params'], {'foo': 'bar'})
        self.assertEqual(wfm1['is_busy'], False)

        # We should be rendering the modules
        render.assert_called_with(state['workflow']['id'],
                                  wfm1['last_relevant_delta_id'])

    @patch('server.rabbitmq.queue_fetch')
    @patch('server.rabbitmq.queue_render')
    @patch.object(Lesson.objects, 'get')
    def test_fetch_initial_workflow(self, get, render, fetch):
        get.return_value = Lesson('slug',
                                  initial_workflow=LessonInitialWorkflow([
            {
                'name': 'Tab X',
                'wfModules': [
                    {
                        'module': 'amodule',
                        'params': {'foo': 'bar'},
                    },
                ],
            },
        ]))

        fetch.return_value = future_none

        create_module_version('amodule', [
            {'id_name': 'foo', 'type': 'string'},
        ], loads_data=True)

        self.log_in()
        response = self.client.get('/lessons/whatever')
        state = response.context_data['initState']
        wf_modules = state['wfModules']
        wfm1 = list(wf_modules.values())[0]
        self.assertEqual(wfm1['is_busy'], True)  # because we sent a fetch

        # We should be rendering the modules
        fetch.assert_called()
        self.assertEqual(fetch.call_args[0][0].id, wfm1['id'])
        render.assert_not_called()

    @patch.object(Lesson.objects, 'get')
    def test_fetch_initial_workflow_with_missing_module_throws_500(self, get):
        get.return_value = Lesson('slug',
                                  initial_workflow=LessonInitialWorkflow([
            {
                'name': 'Tab X',
                'wfModules': [
                    {
                        'module': 'amodule',  # does not exist
                        'params': {'foo': 'bar'},
                    },
                ],
            },
        ]))

        self.log_in()
        response = self.client.get('/lessons/whatever')
        self.assertEqual(response.status_code, 500)

    @patch.object(Lesson.objects, 'get')
    def test_fetch_initial_workflow_with_invalid_params_throws_500(self, get):
        get.return_value = Lesson('slug',
                                  initial_workflow=LessonInitialWorkflow([
            {
                'name': 'Tab X',
                'wfModules': [
                    {
                        'module': 'amodule',
                        'params': {'fooTYPO': 'bar'},  # typo
                    },
                ],
            },
        ]))

        create_module_version('amodule', [
            {'id_name': 'foo', 'type': 'string'},
        ])

        self.log_in()
        response = self.client.get('/lessons/whatever')
        self.assertEqual(response.status_code, 500)
