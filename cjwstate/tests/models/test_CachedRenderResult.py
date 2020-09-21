from dataclasses import replace
import pyarrow
from cjwkernel.tests.util import arrow_table, assert_render_result_equals
from cjwkernel.types import I18nMessage, RenderError, RenderResult
from cjwstate import minio
from cjwstate.models import Workflow
from cjwstate.models.commands import InitWorkflowCommand
from cjwstate.rendercache.io import (
    BUCKET,
    cache_render_result,
    open_cached_render_result,
    clear_cached_render_result_for_wf_module,
    crr_parquet_key,
)
from cjwstate.tests.utils import DbTestCase


class CachedRenderResultTests(DbTestCase):
    def setUp(self):
        super().setUp()
        self.workflow = Workflow.objects.create()
        self.delta = InitWorkflowCommand.create(self.workflow)
        self.tab = self.workflow.tabs.create(position=0)
        self.wf_module = self.tab.wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=self.delta.id
        )

    def test_none(self):
        self.assertIsNone(self.wf_module.cached_render_result)

    def test_delete_wfmodule(self):
        result = RenderResult(
            arrow_table({"A": [1]}), [RenderError(I18nMessage("X", []), [])], {}
        )
        cache_render_result(self.workflow, self.wf_module, self.delta.id, result)

        parquet_key = crr_parquet_key(self.wf_module.cached_render_result)
        self.wf_module.delete()
        self.assertFalse(minio.exists(BUCKET, parquet_key))
        # Note: we _don't_ test soft-delete. Soft-deleted modules aren't
        # extremely common, so it's not like we'll be preserving terabytes of
        # unused cached render results.
        #
        # If this assumption is wrong, by all means wipe the cache on
        # soft-delete.
        #
        # Longer-term, a better approach is to nix soft-deletion.

    def test_double_clear(self):
        result = RenderResult(
            arrow_table({"A": [1]}), [RenderError(I18nMessage("X", []), [])], {}
        )
        cache_render_result(self.workflow, self.wf_module, self.delta.id, result)
        clear_cached_render_result_for_wf_module(self.wf_module)
        clear_cached_render_result_for_wf_module(self.wf_module)  # don't crash

    def test_duplicate_copies_fresh_cache(self):
        # The cache's filename depends on workflow_id and wf_module_id.
        # Duplicating it would need more complex code :).
        result = RenderResult(
            arrow_table({"A": [1]}), [RenderError(I18nMessage("X", []), [])], {}
        )
        cache_render_result(self.workflow, self.wf_module, self.delta.id, result)

        workflow2 = Workflow.objects.create()
        tab2 = workflow2.tabs.create(position=0)
        InitWorkflowCommand.create(workflow2)
        dup = self.wf_module.duplicate_into_new_workflow(tab2)

        dup_cached_result = dup.cached_render_result
        self.assertEqual(
            dup_cached_result,
            replace(
                self.wf_module.cached_render_result,
                workflow_id=workflow2.id,
                delta_id=workflow2.last_delta_id,
                wf_module_id=dup.id,
            ),
        )
        with open_cached_render_result(dup_cached_result) as result2:
            assert_render_result_equals(result2, result)

    def test_duplicate_ignores_stale_cache(self):
        # The cache's filename depends on workflow_id and wf_module_id.
        # Duplicating it would need more complex code :).
        result = RenderResult(
            arrow_table({"A": [1]}), [RenderError(I18nMessage("X", []), [])], {}
        )
        cache_render_result(self.workflow, self.wf_module, self.delta.id, result)
        # Now simulate a new delta that hasn't been rendered
        self.wf_module.last_relevant_delta_id += 1
        self.wf_module.save(update_fields=["last_relevant_delta_id"])

        workflow2 = Workflow.objects.create()
        tab2 = workflow2.tabs.create(position=0)
        InitWorkflowCommand.create(workflow2)
        dup = self.wf_module.duplicate_into_new_workflow(tab2)

        dup_cached_result = dup.cached_render_result
        self.assertIsNone(dup_cached_result)
        self.assertEqual(dup.cached_render_result_status, None)
