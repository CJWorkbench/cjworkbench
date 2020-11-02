from cjwstate.models.workflow import Workflow
from cjwstate.tests.utils import DbTestCase


class BlockTest(DbTestCase):
    def test_duplicate_chart(self):
        workflow = Workflow.create_and_init()
        step1 = workflow.tabs.first().steps.create(order=0, slug="step-1")
        block = workflow.blocks.create(
            position=0, slug="block-1", block_type="Chart", step=step1
        )

        workflow2 = workflow.duplicate_anonymous("session-key")
        block2 = workflow2.blocks.first()
        self.assertEqual(block2.position, 0)
        self.assertEqual(block2.block_type, "Chart")
        self.assertEqual(block2.step.slug, "step-1")

    def test_duplicate_table(self):
        workflow = Workflow.create_and_init()
        tab1 = workflow.tabs.first()
        block = workflow.blocks.create(
            position=0, slug="block-1", block_type="Table", tab=tab1
        )

        workflow2 = workflow.duplicate_anonymous("session-key")
        block2 = workflow2.blocks.first()
        self.assertEqual(block2.position, 0)
        self.assertEqual(block2.block_type, "Table")
        self.assertEqual(block2.tab.slug, tab1.slug)

    def test_duplicate_text(self):
        workflow = Workflow.create_and_init()
        block = workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="hi"
        )

        workflow2 = workflow.duplicate_anonymous("session-key")
        block2 = workflow2.blocks.first()
        self.assertEqual(block2.position, 0)
        self.assertEqual(block2.block_type, "Text")
        self.assertEqual(block2.text_markdown, "hi")

    def test_duplicate_ignore_spurious_data(self):
        # The implementation is raw SQL. Make sure no joins incorporate
        # extra rows, regardless of slugs....
        workflow = Workflow.create_and_init()
        # Two tabs. If we don't join by slug, we'll get duplicates.
        tab2 = workflow.tabs.create(position=1, slug="tab-2")
        tab3 = workflow.tabs.create(position=2, slug="tab-3")
        # Two steps. If we don't join by slug, we'll get duplicates.
        step1 = tab3.steps.create(order=0, slug="step-1")
        step2 = tab3.steps.create(order=1, slug="step-2")
        block1 = workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="hi"
        )
        # Two of the same Chart. If we only join by slug, we'll get duplicates.
        block2 = workflow.blocks.create(
            position=1, slug="block-2", block_type="Chart", step_id=step1.id
        )
        block3 = workflow.blocks.create(
            position=2, slug="block-3", block_type="Chart", step_id=step1.id
        )
        # Two of the same table. If we only join by slug, we'll get duplicates.
        block4 = workflow.blocks.create(
            position=3, slug="block-4", block_type="Table", tab_id=tab2.id
        )
        block5 = workflow.blocks.create(
            position=4, slug="block-5", block_type="Table", tab_id=tab2.id
        )

        # ... and duplicates of everything, but in the wrong workflow! If we
        # don't filter by workflow, we'll get duplicates.
        bad_workflow = Workflow.create_and_init()
        bad_tab2 = bad_workflow.tabs.create(position=1, slug="tab-2")
        bad_tab3 = bad_workflow.tabs.create(position=2, slug="tab-3")
        bad_step1 = bad_tab3.steps.create(order=0, slug="step-1")
        bad_step2 = bad_tab3.steps.create(order=1, slug="step-2")
        bad_block1 = bad_workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="hi"
        )
        bad_block2 = bad_workflow.blocks.create(
            position=1, slug="block-2", block_type="Chart", step_id=bad_step1.id
        )
        bad_block3 = bad_workflow.blocks.create(
            position=2, slug="block-3", block_type="Chart", step_id=bad_step1.id
        )
        bad_block4 = bad_workflow.blocks.create(
            position=3, slug="block-4", block_type="Table", tab_id=bad_tab2.id
        )
        bad_block5 = bad_workflow.blocks.create(
            position=4, slug="block-5", block_type="Table", tab_id=bad_tab2.id
        )

        workflow2 = workflow.duplicate_anonymous("session-key")
        self.assertEqual(
            list(
                workflow2.blocks.values_list(
                    "position",
                    "slug",
                    "block_type",
                    "text_markdown",
                    "tab_id",
                    "step_id",
                )
            ),
            [
                (0, "block-1", "Text", "hi", None, None),
                (
                    1,
                    "block-2",
                    "Chart",
                    "",
                    None,
                    workflow2.tabs.get(slug="tab-3").steps.get(slug="step-1").id,
                ),
                (
                    2,
                    "block-3",
                    "Chart",
                    "",
                    None,
                    workflow2.tabs.get(slug="tab-3").steps.get(slug="step-1").id,
                ),
                (3, "block-4", "Table", "", workflow2.tabs.get(slug="tab-2").id, None),
                (4, "block-5", "Table", "", workflow2.tabs.get(slug="tab-2").id, None),
            ],
        )
