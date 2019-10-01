from unittest.mock import patch
from cjwkernel.errors import ModuleError
from cjwstate.models import ModuleVersion, Workflow
from cjwstate.modules.loaded_module import LoadedModule
from cjwstate.params import get_migrated_params
from cjwstate.tests.utils import DbTestCase


class GetMigratedParamsTest(DbTestCase):
    @patch.object(LoadedModule, "for_module_version_sync")
    def test_get_cached(self, load_module):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name="yay",
            params={},
            cached_migrated_params={"foo": "bar"},
            cached_migrated_params_module_version="abc123",
        )
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "yay",
                "name": "Yay",
                "category": "Clean",
                "parameters": [{"id_name": "foo", "type": "string"}],
            },
            source_version_hash="abc123",
        )

        self.assertEqual(get_migrated_params(wf_module), {"foo": "bar"})
        load_module.assert_not_called()

    @patch.object(LoadedModule, "for_module_version_sync")
    def test_internal_module_get_cached(self, load_module):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name="yay",
            params={},
            cached_migrated_params={"foo": "bar"},
            cached_migrated_params_module_version="v2",
        )
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "yay",
                "name": "Yay",
                "category": "Clean",
                "parameters_version": 2,
                "parameters": [{"id_name": "foo", "type": "string"}],
            },
            source_version_hash="internal",
        )

        self.assertEqual(get_migrated_params(wf_module), {"foo": "bar"})
        load_module.assert_not_called()

    @patch.object(LoadedModule, "for_module_version_sync")
    def test_wrong_cache_version_calls_migrate_params(self, load_module):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name="yay",
            params={"foo": "bar"},
            cached_migrated_params={"foo": "bar"},
            cached_migrated_params_module_version="abc123",
        )
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "yay",
                "name": "Yay",
                "category": "Clean",
                "parameters": [{"id_name": "foo", "type": "string"}],
            },
            source_version_hash="newversion",
        )

        load_module.return_value.migrate_params.return_value = {"foo": "baz"}
        self.assertEqual(get_migrated_params(wf_module), {"foo": "baz"})
        load_module.assert_called()

        # and assert we've cached things
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(wf_module.cached_migrated_params_module_version, "newversion")
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(wf_module.cached_migrated_params_module_version, "newversion")

    @patch.object(LoadedModule, "for_module_version_sync")
    def test_internal_wrong_cache_version_calls_migrate_params(self, load_module):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name="yay",
            params={"foo": "bar"},
            cached_migrated_params={"foo": "bar"},
            cached_migrated_params_module_version="v2",
        )
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "yay",
                "name": "Yay",
                "category": "Clean",
                "parameters_version": 3,
                "parameters": [{"id_name": "foo", "type": "string"}],
            },
            source_version_hash="internal",  # magic string
        )

        load_module.return_value.migrate_params.return_value = {"foo": "baz"}
        self.assertEqual(get_migrated_params(wf_module), {"foo": "baz"})
        load_module.assert_called()

        # and assert we've cached things
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(wf_module.cached_migrated_params_module_version, "v3")
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(wf_module.cached_migrated_params_module_version, "v3")

    @patch.object(LoadedModule, "for_module_version_sync")
    def test_no_cache_version_calls_migrate_params(self, load_module):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name="yay",
            params={"foo": "bar"},
            cached_migrated_params=None,
            cached_migrated_params_module_version=None,
        )
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "yay",
                "name": "Yay",
                "category": "Clean",
                "parameters": [{"id_name": "foo", "type": "string"}],
            },
            source_version_hash="abc123",
        )

        load_module.return_value.migrate_params.return_value = {"foo": "baz"}
        self.assertEqual(get_migrated_params(wf_module), {"foo": "baz"})
        load_module.assert_called()

        # and assert we've cached things
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(wf_module.cached_migrated_params_module_version, "abc123")
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "baz"})
        self.assertEqual(wf_module.cached_migrated_params_module_version, "abc123")

    @patch.object(LoadedModule, "for_module_version_sync")
    def test_module_error_raises(self, load_module):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, module_id_name="yay", params={}
        )
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "yay",
                "name": "Yay",
                "category": "Clean",
                "parameters": [{"id_name": "foo", "type": "string"}],
            },
            source_version_hash="abc123",
        )

        load_module.return_value.migrate_params.side_effect = ModuleError
        with self.assertRaises(ModuleError):
            get_migrated_params(wf_module)

        # Assert we wrote nothing to cache
        self.assertIsNone(wf_module.cached_migrated_params)
        self.assertIsNone(wf_module.cached_migrated_params_module_version)
        wf_module.refresh_from_db()
        self.assertIsNone(wf_module.cached_migrated_params)
        self.assertIsNone(wf_module.cached_migrated_params_module_version)

    @patch.object(LoadedModule, "for_module_version_sync")
    def test_no_validate_after_migrate_params(self, load_module):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, module_id_name="yay", params={}
        )
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "yay",
                "name": "Yay",
                "category": "Clean",
                "parameters": [{"id_name": "foo", "type": "string"}],
            },
            source_version_hash="abc123",
        )

        # We don't validate, because renderer/fetcher/frontend all do different
        # things when params are invalid.
        load_module.return_value.migrate_params.return_value = {"x": []}
        self.assertEqual(get_migrated_params(wf_module), {"x": []})

    def test_deleted_module_version(self):
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
        self.assertEqual(get_migrated_params(wf_module), {})

        # Assert we did not modify the cache
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "bar"})
        self.assertEqual(wf_module.cached_migrated_params_module_version, "abc123")
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "bar"})
        self.assertEqual(wf_module.cached_migrated_params_module_version, "abc123")

    @patch.object(LoadedModule, "for_module_version_sync")
    def test_deleted_wf_module_race(self, load_module):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, module_id_name="yay", params={}
        )
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "yay",
                "name": "Yay",
                "category": "Clean",
                "parameters": [{"id_name": "foo", "type": "string"}],
            },
            source_version_hash="abc123",
        )

        load_module.return_value.migrate_params.return_value = {"foo": "bar"}
        self.assertEqual(get_migrated_params(wf_module), {"foo": "bar"})
        self.assertEqual(wf_module.cached_migrated_params, {"foo": "bar"})
        self.assertEqual(wf_module.cached_migrated_params_module_version, "abc123")
        # ... even though the WfModule does not exist in the database
