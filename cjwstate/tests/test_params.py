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
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name="yay",
            params={},
            cached_migrated_params={"foo": "bar"},
            cached_migrated_params_module_version=module_zipfile.version,
        )

        self.assertEqual(get_migrated_params(wf_module), {"foo": "bar"})
        self.kernel.migrate_params.assert_not_called()

    def test_internal_module_get_cached(self):
        workflow = Workflow.create_and_init()
        create_module_zipfile(
            module_id="testinternalmodulegetcached",  # unique across test suite
            version="internal",
            spec_kwargs={
                "parameters": [{"id_name": "foo", "type": "string"}],
                "parameters_version": 2,
            },
        )
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name="testinternalmodulegetcached",
            params={},
            cached_migrated_params={"foo": "bar"},
            cached_migrated_params_module_version="v2",
        )

        self.assertEqual(get_migrated_params(wf_module), {"foo": "bar"})
        self.kernel.migrate_params.assert_not_called()

    def test_wrong_cache_version_calls_migrate_params(self):
        workflow = Workflow.create_and_init()
        module_zipfile = create_module_zipfile(
            module_id="yay",
            spec_kwargs={
                "parameters": [{"id_name": "foo", "type": "string"}],
                "parameters_version": 2,
            },
        )
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name="yay",
            params={"foo": "bar"},
            cached_migrated_params={"foo": "bar"},
            cached_migrated_params_module_version=module_zipfile.version + "a",
        )

        self.kernel.migrate_params.return_value = {"foo": "baz"}
        with self.assertLogs(level=logging.INFO):
            self.assertEqual(get_migrated_params(wf_module), {"foo": "baz"})
        self.kernel.migrate_params.assert_called()

        # and assert we've cached things
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(
            wf_module.cached_migrated_params_module_version, module_zipfile.version
        )
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(
            wf_module.cached_migrated_params_module_version, module_zipfile.version
        )

    def test_internal_wrong_cache_version_calls_migrate_params(self):
        workflow = Workflow.create_and_init()
        create_module_zipfile(
            module_id="wrongcacheversioncallsmigrateparams",
            version="internal",
            spec_kwargs={
                "parameters": [{"id_name": "foo", "type": "string"}],
                "parameters_version": 3,
            },
        )
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name="wrongcacheversioncallsmigrateparams",  # unique
            params={"foo": "bar"},
            cached_migrated_params={"foo": "bar"},
            cached_migrated_params_module_version="v2",
        )

        self.kernel.migrate_params.return_value = {"foo": "baz"}
        with self.assertLogs(level=logging.INFO):
            self.assertEqual(get_migrated_params(wf_module), {"foo": "baz"})
        self.kernel.migrate_params.assert_called()

        # and assert we've cached things
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(wf_module.cached_migrated_params_module_version, "v3")
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(wf_module.cached_migrated_params_module_version, "v3")

    def test_no_cache_version_calls_migrate_params(self):
        workflow = Workflow.create_and_init()
        module_zipfile = create_module_zipfile(
            module_id="yay",
            spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]},
        )
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name="yay",
            params={"foo": "bar"},
            cached_migrated_params=None,
            cached_migrated_params_module_version=None,
        )

        self.kernel.migrate_params.return_value = {"foo": "baz"}
        with self.assertLogs(level=logging.INFO):
            self.assertEqual(get_migrated_params(wf_module), {"foo": "baz"})
        self.kernel.migrate_params.assert_called()

        # and assert we've cached things
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(
            wf_module.cached_migrated_params_module_version, module_zipfile.version
        )
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(
            wf_module.cached_migrated_params_module_version, module_zipfile.version
        )

    def test_module_error_raises(self):
        workflow = Workflow.create_and_init()
        create_module_zipfile(
            module_id="yay",
            spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]},
        )
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, module_id_name="yay", params={}
        )

        self.kernel.migrate_params.side_effect = ModuleError
        with self.assertRaises(ModuleError), self.assertLogs(level=logging.INFO):
            get_migrated_params(wf_module)

        # Assert we wrote nothing to cache
        self.assertIsNone(wf_module.cached_migrated_params)
        self.assertIsNone(wf_module.cached_migrated_params_module_version)
        wf_module.refresh_from_db()
        self.assertIsNone(wf_module.cached_migrated_params)
        self.assertIsNone(wf_module.cached_migrated_params_module_version)

    def test_no_validate_after_migrate_params(self):
        workflow = Workflow.create_and_init()
        create_module_zipfile(
            module_id="yay",
            spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]},
        )
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, module_id_name="yay", params={}
        )

        # We don't validate, because renderer/fetcher/frontend all do different
        # things when params are invalid.
        self.kernel.migrate_params.return_value = {"x": []}
        with self.assertLogs(level=logging.INFO):
            self.assertEqual(get_migrated_params(wf_module), {"x": []})

    def test_deleted_module(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name="yay",
            params={"foo": "bar"},
            cached_migrated_params={"foo": "bar"},
            cached_migrated_params_module_version="abc123",
        )

        # We don't validate, because renderer/fetcher/frontend all do different
        # things when params are invalid.
        with self.assertRaises(KeyError):
            get_migrated_params(wf_module)

        # Assert we did not modify the cache
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "bar"})
        self.assertEqual(wf_module.cached_migrated_params_module_version, "abc123")
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "bar"})
        self.assertEqual(wf_module.cached_migrated_params_module_version, "abc123")

    def test_deleted_wf_module_race(self):
        workflow = Workflow.create_and_init()
        module_zipfile = create_module_zipfile(
            module_id="yay",
            spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]},
        )
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, module_id_name="yay", params={}
        )
        wf_module.delete()

        self.kernel.migrate_params.return_value = {"foo": "bar"}
        with self.assertLogs(level=logging.INFO):
            self.assertEqual(get_migrated_params(wf_module), {"foo": "bar"})
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "bar"})
        self.assertEqual(
            wf_module.cached_migrated_params_module_version, module_zipfile.version
        )
        # ... even though the WfModule does not exist in the database
