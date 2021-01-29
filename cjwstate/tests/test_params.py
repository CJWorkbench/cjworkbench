import logging
from cjwkernel.errors import ModuleError
from cjwstate.models import Workflow
from cjwstate.params import get_migrated_params
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)


class GetMigratedParamsTest(DbTestCaseWithModuleRegistryAndMockKernel):
    def test_get_cached(self):
        workflow = Workflow.create_and_init()
        module_zipfile = create_module_zipfile(
            "yay", spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]}
        )
        step = workflow.tabs.first().steps.create(
            order=0,
            module_id_name="yay",
            params={},
            cached_migrated_params={"foo": "bar"},
            cached_migrated_params_module_version=module_zipfile.version,
        )

        self.assertEqual(get_migrated_params(step), {"foo": "bar"})
        self.kernel.migrate_params.assert_not_called()

    def test_wrong_cache_version_calls_migrate_params(self):
        workflow = Workflow.create_and_init()
        module_zipfile = create_module_zipfile(
            module_id="yay",
            spec_kwargs={
                "parameters": [{"id_name": "foo", "type": "string"}],
            },
        )
        step = workflow.tabs.first().steps.create(
            order=0,
            module_id_name="yay",
            params={"foo": "bar"},
            cached_migrated_params={"foo": "bar"},
            cached_migrated_params_module_version=module_zipfile.version + "a",
        )

        self.kernel.migrate_params.return_value = {"foo": "baz"}
        with self.assertLogs(level=logging.INFO):
            self.assertEqual(get_migrated_params(step), {"foo": "baz"})
        self.kernel.migrate_params.assert_called()

        # and assert we've cached things
        self.assertEqual(step.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(
            step.cached_migrated_params_module_version, module_zipfile.version
        )
        step.refresh_from_db()
        self.assertEqual(step.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(
            step.cached_migrated_params_module_version, module_zipfile.version
        )

    def test_no_cache_version_calls_migrate_params(self):
        workflow = Workflow.create_and_init()
        module_zipfile = create_module_zipfile(
            module_id="yay",
            spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]},
        )
        step = workflow.tabs.first().steps.create(
            order=0,
            module_id_name="yay",
            params={"foo": "bar"},
            cached_migrated_params=None,
            cached_migrated_params_module_version=None,
        )

        self.kernel.migrate_params.return_value = {"foo": "baz"}
        with self.assertLogs(level=logging.INFO):
            self.assertEqual(get_migrated_params(step), {"foo": "baz"})
        self.kernel.migrate_params.assert_called()

        # and assert we've cached things
        self.assertEqual(step.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(
            step.cached_migrated_params_module_version, module_zipfile.version
        )
        step.refresh_from_db()
        self.assertEqual(step.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(
            step.cached_migrated_params_module_version, module_zipfile.version
        )

    def test_module_error_raises(self):
        workflow = Workflow.create_and_init()
        create_module_zipfile(
            module_id="yay",
            spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]},
        )
        step = workflow.tabs.first().steps.create(
            order=0, module_id_name="yay", params={}
        )

        self.kernel.migrate_params.side_effect = ModuleError
        with self.assertRaises(ModuleError), self.assertLogs(level=logging.INFO):
            get_migrated_params(step)

        # Assert we wrote nothing to cache
        self.assertIsNone(step.cached_migrated_params)
        self.assertIsNone(step.cached_migrated_params_module_version)
        step.refresh_from_db()
        self.assertIsNone(step.cached_migrated_params)
        self.assertIsNone(step.cached_migrated_params_module_version)

    def test_no_validate_after_migrate_params(self):
        workflow = Workflow.create_and_init()
        create_module_zipfile(
            module_id="yay",
            spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]},
        )
        step = workflow.tabs.first().steps.create(
            order=0, module_id_name="yay", params={}
        )

        # We don't validate, because renderer/fetcher/frontend all do different
        # things when params are invalid.
        self.kernel.migrate_params.return_value = {"x": []}
        with self.assertLogs(level=logging.INFO):
            self.assertEqual(get_migrated_params(step), {"x": []})

    def test_deleted_module(self):
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            module_id_name="yay",
            params={"foo": "bar"},
            cached_migrated_params={"foo": "bar"},
            cached_migrated_params_module_version="abc123",
        )

        # We don't validate, because renderer/fetcher/frontend all do different
        # things when params are invalid.
        with self.assertRaises(KeyError):
            get_migrated_params(step)

        # Assert we did not modify the cache
        self.assertEqual(step.cached_migrated_params, {"foo": "bar"})
        self.assertEqual(step.cached_migrated_params_module_version, "abc123")
        step.refresh_from_db()
        self.assertEqual(step.cached_migrated_params, {"foo": "bar"})
        self.assertEqual(step.cached_migrated_params_module_version, "abc123")

    def test_deleted_step_race(self):
        workflow = Workflow.create_and_init()
        module_zipfile = create_module_zipfile(
            module_id="yay",
            spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]},
        )
        step = workflow.tabs.first().steps.create(
            order=0, module_id_name="yay", params={}
        )
        step.delete()

        self.kernel.migrate_params.return_value = {"foo": "bar"}
        with self.assertLogs(level=logging.INFO):
            self.assertEqual(get_migrated_params(step), {"foo": "bar"})
        self.assertEqual(step.cached_migrated_params, {"foo": "bar"})
        self.assertEqual(
            step.cached_migrated_params_module_version, module_zipfile.version
        )
        # ... even though the Step does not exist in the database
