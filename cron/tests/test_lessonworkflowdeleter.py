import datetime
import logging

from cjwstate.models import Workflow
from cjwstate.tests.utils import DbTestCase
from cron import lessonworkflowdeleter


StaleTimedelta = datetime.timedelta(days=30.1)
FreshTimedelta = datetime.timedelta(days=29.1)


class LessonWorkflowDeleterTest(DbTestCase):
    def test_delete_stale_lesson_workflow(self):
        workflow = Workflow.create_and_init(
            last_viewed_at=(datetime.datetime.now() - StaleTimedelta),
            lesson_slug="analyze-live-twitter",
        )
        with self.assertLogs(lessonworkflowdeleter.__name__, logging.INFO):
            lessonworkflowdeleter.delete_stale_lesson_workflows()
        with self.assertRaises(Workflow.DoesNotExist):
            workflow.refresh_from_db()

    def test_ignore_non_lesson_workflow(self):
        workflow = Workflow.create_and_init(
            last_viewed_at=(datetime.datetime.now() - StaleTimedelta), lesson_slug=None
        )
        lessonworkflowdeleter.delete_stale_lesson_workflows()
        workflow.refresh_from_db()  # still exists

    def test_ignore_fresh_lesson_workflow(self):
        workflow = Workflow.create_and_init(
            last_viewed_at=(datetime.datetime.now() - FreshTimedelta),
            lesson_slug="analyze-live-twitter",
        )
        lessonworkflowdeleter.delete_stale_lesson_workflows()
        workflow.refresh_from_db()  # still exists
