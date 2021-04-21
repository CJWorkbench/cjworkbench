from dataclasses import replace

import pyarrow
from cjwmodule.types import I18nMessage, RenderError
from cjwmodule.arrow.testing import assert_arrow_table_equals, make_column, make_table

from cjwstate import s3
from cjwstate.models import Workflow
from cjwstate.rendercache.io import (
    BUCKET,
    open_cached_render_result,
    clear_cached_render_result_for_step,
    crr_parquet_key,
)
from cjwstate.rendercache.testing import write_to_rendercache
from cjwstate.tests.utils import DbTestCase


class CachedRenderResultTests(DbTestCase):
    def setUp(self):
        super().setUp()
        self.workflow = Workflow.objects.create()
        self.tab = self.workflow.tabs.create(position=0)
        self.step = self.tab.steps.create(
            order=0, slug="step-1", last_relevant_delta_id=1
        )

    def test_none(self):
        self.assertIsNone(self.step.cached_render_result)

    def test_delete_step(self):
        write_to_rendercache(
            self.workflow,
            self.step,
            1,
            table=make_table(make_column("A", [1])),
            errors=[RenderError(I18nMessage("X", {}, None), [])],
            json={"foo": "bar"},
        )

        parquet_key = crr_parquet_key(self.step.cached_render_result)
        self.step.delete()
        self.assertFalse(s3.exists(BUCKET, parquet_key))
        # Note: we _don't_ test soft-delete. Soft-deleted modules aren't
        # extremely common, so it's not like we'll be preserving terabytes of
        # unused cached render results.
        #
        # If this assumption is wrong, by all means wipe the cache on
        # soft-delete.
        #
        # Longer-term, a better approach is to nix soft-deletion.

    def test_double_clear(self):
        write_to_rendercache(
            self.workflow, self.step, 1, make_table(make_column("A", [1]))
        )
        clear_cached_render_result_for_step(self.step)
        clear_cached_render_result_for_step(self.step)  # don't crash

    def test_duplicate_copies_fresh_cache(self):
        # The cache's filename depends on workflow_id and step_id.
        # Duplicating it would need more complex code :).
        table = make_table(make_column("A", [1], format="${:,.2f}"))
        write_to_rendercache(
            self.workflow,
            self.step,
            1,
            table=table,
            errors=[RenderError(I18nMessage("X", {}, None))],
            json={"foo": "bar"},
        )

        workflow2 = Workflow.objects.create()
        tab2 = workflow2.tabs.create(position=0)
        dup = self.step.duplicate_into_new_workflow(tab2)

        dup_cached_result = dup.cached_render_result
        self.assertEqual(
            dup_cached_result,
            replace(
                self.step.cached_render_result,
                workflow_id=workflow2.id,
                step_id=dup.id,
                delta_id=0,
            ),
        )
        with open_cached_render_result(dup_cached_result) as result2:
            assert_arrow_table_equals(result2.table, table)
            self.assertEqual(result2.errors, [RenderError(I18nMessage("X", {}, None))])
            self.assertEqual(result2.json, {"foo": "bar"})

    def test_duplicate_ignores_stale_cache(self):
        # write to the wrong delta ID: "stale"
        write_to_rendercache(
            self.workflow, self.step, 5, make_table(make_column("A", [1]))
        )

        workflow2 = Workflow.objects.create()
        tab2 = workflow2.tabs.create(position=0)
        dup = self.step.duplicate_into_new_workflow(tab2)

        dup_cached_result = dup.cached_render_result
        self.assertIsNone(dup_cached_result)
        self.assertEqual(dup.cached_render_result_status, None)
