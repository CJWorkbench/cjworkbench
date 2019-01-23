from server.models import Lesson, Workflow, ModuleVersion
from server.tests.utils import DbTestCase, create_test_user
from server.tests.models.test_Lesson import lesson_text_with_initial_workflow
from unittest.mock import patch

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

    def test_get_with_workflow(self):
        self.log_in()

        Workflow.objects.create(owner=self.user,
                                lesson_slug='load-public-data')
        response = self.client.get('/lessons/load-public-data/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed('workflow.html')

    def test_post_without_login(self):
        response = self.client.post('/lessons/load-public-data/', follow=True)
        self.assertRedirects(response, '/lessons/load-public-data/')
        self.assertEqual(Workflow.objects.count(), 1)

    def test_post_with_existing(self):
        self.log_in()
        Workflow.objects.create(owner=self.user,
                                lesson_slug='load-public-data')
        response = self.client.post('/lessons/load-public-data/')
        self.assertRedirects(response, '/lessons/load-public-data/')
        self.assertEqual(Workflow.objects.count(), 1)  # don't create duplicate

    def test_post_without_existing(self):
        self.log_in()

        # Add non-matching Workflows -- to test we ignore them
        Workflow.objects.create(owner=self.user, lesson_slug='other-lesson')
        Workflow.objects.create(owner=self.user, lesson_slug=None)
        Workflow.objects.create(owner=self.other_user,
                                lesson_slug='load-public-data', public=True)

        response = self.client.post('/lessons/load-public-data/')
        self.assertRedirects(response, '/lessons/load-public-data/')
        self.assertEqual(Workflow.objects.count(), 4)  # create Workflow
        self.assertEqual(Workflow.objects
                         .filter(lesson_slug='load-public-data').count(), 2)

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

    def test_get_workflow_with_invalid_lesson_slug(self):
        self.log_in()

        workflow = Workflow.objects.create(owner=self.user,
                                           lesson_slug='missing-lesson-slug')
        response = self.client.get(workflow.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed('workflow.html')


    # Check that lesson initial workflow json gets rehydrated into a real workflow with multiple tabs
    @patch.object(Lesson.objects, 'get')
    def test_initial_workflow_from_json(self, get):

        initial_workflow_json = """
            {
              "tabs": [
                {
                  "name": "Tab X",
                  "wfModules": [
                    {
                      "module": "loadurl",
                      "params": {
                        "url": "http://foo.com",
                        "has_header": true
                      }
                    }
                  ]
                }
              ]
            }
        """
        get.return_value = Lesson.parse('a-slug', lesson_text_with_initial_workflow(initial_workflow_json))

        load_module_spec = {
          "name": "Add from URL",
          "id_name": "loadurl" ,
          "category" : "Add data",
          "parameters": [
            {
              "name": "",
              "id_name" : "url",
              "type": "string",
            }
          ]
        }
        ModuleVersion.create_or_replace_from_spec(load_module_spec)

        self.log_in()
        response = self.client.get('/lessons/whatever')
        tabs = response.context_data['initState']['tabs']
        keys=list(tabs.keys())
        self.assertEqual(tabs[keys[0]]['name'], 'Tab X')


