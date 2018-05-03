from django.test import Client, TestCase
from server.models import Lesson, Workflow
from server.tests.utils import create_test_user

class LessonDetailTests(TestCase):
    def log_in(self):
        self.user = create_test_user()
        self.client.force_login(self.user)

    @property
    def other_user(self):
        # User created on first access
        if not hasattr(self, '_other_user'):
            self._other_user = create_test_user('attacker', 'bad@example.org', 'alksjdghalskdjfh')
        return self._other_user

    def test_get_requires_login(self):
        response = self.client.get('/lessons/load-public-data/')
        self.assertEqual(response.status_code, 302)

    def test_get_invalid_slug(self):
        self.log_in()
        response = self.client.get('/lessons/load-public-dat-whoops-a-typoooooo/')
        self.assertEqual(response.status_code, 404)

    def test_get_missing_workflow(self):
        self.log_in()

        # Add non-matching Workflows -- to test we _don't_ load them
        Workflow.objects.create(owner=self.user, lesson_slug='some-other-lesson')
        Workflow.objects.create(owner=self.user, lesson_slug=None)
        Workflow.objects.create(owner=self.other_user, lesson_slug='load-public-data', public=True)

        response = self.client.get('/lessons/load-public-data/')
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(Workflow.objects.count(), 3) # don't create Workflow

    def test_get_with_workflow(self):
        self.log_in()

        Workflow.objects.create(owner=self.user, lesson_slug='load-public-data')
        response = self.client.get('/lessons/load-public-data/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed('workflow.html')

    def test_post_requires_login(self):
        response = self.client.post('/lessons/load-public-data/')
        self.assertEqual(response.status_code, 302)   # login redirect (we'd redirect even if logged in, though)
        self.assertEqual(Workflow.objects.count(), 0) # don't create Workflow

    def test_post_with_existing(self):
        self.log_in()
        Workflow.objects.create(owner=self.user, lesson_slug='load-public-data')
        response = self.client.post('/lessons/load-public-data/')
        self.assertRedirects(response, '/lessons/load-public-data/')
        self.assertEqual(Workflow.objects.count(), 1) # don't create duplicate Workflow

    def test_post_without_existing(self):
        self.log_in()

        # Add non-matching Workflows -- to test we ignore them
        Workflow.objects.create(owner=self.user, lesson_slug='other-lesson')
        Workflow.objects.create(owner=self.user, lesson_slug=None)
        Workflow.objects.create(owner=self.other_user, lesson_slug='load-public-data', public=True)

        response = self.client.post('/lessons/load-public-data/')
        self.assertRedirects(response, '/lessons/load-public-data/')
        self.assertEqual(Workflow.objects.count(), 4) # create Workflow
        self.assertEqual(Workflow.objects.filter(lesson_slug='load-public-data').count(), 2)

    # The next three tests are of GET /workflows/:id/. They're here, not there,
    # to keep canonical-URL tests in one file.
    #
    # We're testing that the rules are:
    # * GET /workflows/:id/ when there is a lesson: redirect to lesson
    # * GET /workflows/:id/ when there is no lesson: display
    # * GET /lessons/:slug/ when there is a workflow: display, with 'lesson' param
    def test_get_workflow_with_lesson_slug(self):
        self.log_in()

        workflow = Workflow.objects.create(owner=self.user, lesson_slug='load-public-data')
        response = self.client.get(workflow.get_absolute_url())
        self.assertRedirects(response, '/lessons/load-public-data/')

    def test_get_public_workflow_with_lesson_slug(self):
        self.log_in()

        workflow = Workflow.objects.create(owner=self.other_user, lesson_slug='load-public-data', public=True) # not 404
        workflow.save()
        response = self.client.get(workflow.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed('workflow.html')

    def test_get_workflow_with_invalid_lesson_slug(self):
        self.log_in()

        workflow = Workflow.objects.create(owner=self.user, lesson_slug='nonexistent-lesson-slug')
        response = self.client.get(workflow.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed('workflow.html')
