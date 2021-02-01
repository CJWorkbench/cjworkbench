import datetime
import logging

from cjwstate.models import Workflow
from cjwstate.tests.utils import DbTestCase
from cron import lessonautoupdatedisabler


StaleTimedelta = datetime.timedelta(days=7.1)
FreshTimedelta = datetime.timedelta(days=1.1)


class LessonAutoupdateDisablerTest(DbTestCase):
    def test_disable_auto_update_on_stale_lesson(self):
        workflow = Workflow.create_and_init(
            last_viewed_at=(datetime.datetime.now() - StaleTimedelta),
            lesson_slug="analyze-live-twitter",
        )
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="fetcher",
            auto_update_data=True,
            next_update=datetime.datetime.now(),
        )
        with self.assertLogs(lessonautoupdatedisabler.__name__, logging.INFO):
            lessonautoupdatedisabler.disable_stale_auto_update()
        step.refresh_from_db()
        self.assertEqual(step.auto_update_data, False)
        self.assertIsNone(step.next_update)

    def test_ignore_non_auto_update_step(self):
        workflow = Workflow.create_and_init(
            last_viewed_at=(datetime.datetime.now() - StaleTimedelta),
            lesson_slug="analyze-live-twitter",
        )
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="fetcher",
            auto_update_data=False,
            next_update=None,
        )
        with self.assertLogs(lessonautoupdatedisabler.__name__, logging.INFO):
            lessonautoupdatedisabler.disable_stale_auto_update()
        step.refresh_from_db()
        self.assertEqual(step.auto_update_data, False)
        self.assertIsNone(step.next_update)

    def test_ignore_deleted_step(self):
        workflow = Workflow.create_and_init(
            last_viewed_at=(datetime.datetime.now() - StaleTimedelta),
            lesson_slug="analyze-live-twitter",
        )
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="fetcher",
            auto_update_data=True,
            next_update=datetime.datetime.now(),
            is_deleted=True,
        )
        with self.assertLogs(lessonautoupdatedisabler.__name__, logging.INFO):
            lessonautoupdatedisabler.disable_stale_auto_update()
        step.refresh_from_db()
        self.assertEqual(step.auto_update_data, True)
        self.assertIsNotNone(step.next_update)

    def test_ignore_deleted_tab(self):
        workflow = Workflow.create_and_init(
            last_viewed_at=(datetime.datetime.now() - StaleTimedelta),
            lesson_slug="analyze-live-twitter",
        )
        tab = workflow.tabs.create(position=1, slug="tab-deleted", is_deleted=True)
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="fetcher",
            auto_update_data=True,
            next_update=datetime.datetime.now(),
        )
        with self.assertLogs(lessonautoupdatedisabler.__name__, logging.INFO):
            lessonautoupdatedisabler.disable_stale_auto_update()
        step.refresh_from_db()
        self.assertEqual(step.auto_update_data, True)
        self.assertIsNotNone(step.next_update)

    def test_ignore_fresh_lesson(self):
        workflow = Workflow.create_and_init(
            last_viewed_at=(datetime.datetime.now() - FreshTimedelta),
            lesson_slug="analyze-live-twitter",
        )
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="fetcher",
            auto_update_data=True,
            next_update=datetime.datetime.now(),
            is_deleted=True,
        )
        with self.assertLogs(lessonautoupdatedisabler.__name__, logging.INFO):
            lessonautoupdatedisabler.disable_stale_auto_update()
        step.refresh_from_db()
        self.assertEqual(step.auto_update_data, True)
        self.assertIsNotNone(step.next_update)

    def test_ignore_stale_non_lesson(self):
        workflow = Workflow.create_and_init(
            last_viewed_at=(datetime.datetime.now() - StaleTimedelta), lesson_slug=None
        )
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="fetcher",
            auto_update_data=True,
            next_update=datetime.datetime.now(),
            is_deleted=True,
        )
        with self.assertLogs(lessonautoupdatedisabler.__name__, logging.INFO):
            lessonautoupdatedisabler.disable_stale_auto_update()
        step.refresh_from_db()
        self.assertEqual(step.auto_update_data, True)
        self.assertIsNotNone(step.next_update)
