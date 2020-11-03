from cjwstate.models import reports
from cjwstate.models.block import Block
from cjwstate.models.workflow import Workflow
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)


class ReportsTest(DbTestCaseWithModuleRegistryAndMockKernel):
    def assert_report_equals(self, lhs: reports.Report, rhs: reports.Report) -> None:
        # Compare block _data_ for equality. Django.model __eq__ always
        # compares id=None as False, even when models are equal.
        field_names = [f.name for f in Block._meta.get_fields()]
        self.assertEqual(
            [tuple(getattr(b, f) for f in field_names) for b in lhs],
            [tuple(getattr(b, f) for f in field_names) for b in rhs],
        )

    def test_build_auto_report_for_workflow_empty(self):
        workflow = Workflow.create_and_init()
        self.assert_report_equals(reports.build_auto_report_for_workflow(workflow), [])

    def test_build_auto_report_for_workflow(self):
        create_module_zipfile("charty", spec_kwargs={"html_output": True})
        create_module_zipfile("nochart", spec_kwargs={"html_output": False})

        workflow = Workflow.create_and_init()
        tab1 = workflow.tabs.first()
        tab2 = workflow.tabs.create(position=1, slug="tab-2")

        tab1.steps.create(order=0, module_id_name="nochart", slug="step-1-ignore")
        step2 = tab1.steps.create(order=1, module_id_name="charty", slug="step-2")
        step3 = tab1.steps.create(order=2, module_id_name="charty", slug="step-3")
        step4 = tab2.steps.create(order=0, module_id_name="charty", slug="step-4")
        tab2.steps.create(order=1, module_id_name="nochart", slug="step-5-ignore")

        self.assert_report_equals(
            reports.build_auto_report_for_workflow(workflow),
            [
                Block(
                    workflow=workflow,
                    position=0,
                    slug="block-auto-step-2",
                    block_type="Chart",
                    step=step2,
                ),
                Block(
                    workflow=workflow,
                    position=1,
                    slug="block-auto-step-3",
                    block_type="Chart",
                    step=step3,
                ),
                Block(
                    workflow=workflow,
                    position=2,
                    slug="block-auto-step-4",
                    block_type="Chart",
                    step=step4,
                ),
            ],
        )

    def test_build_auto_report_omit_soft_deleted_step(self):
        create_module_zipfile("charty", spec_kwargs={"html_output": True})

        workflow = Workflow.create_and_init()
        tab1 = workflow.tabs.first()
        tab2 = workflow.tabs.create(position=1, slug="tab-2")

        tab1.steps.create(
            order=0, module_id_name="charty", slug="step-1-deleted", is_deleted=True
        )

        self.assert_report_equals(reports.build_auto_report_for_workflow(workflow), [])

    def test_build_auto_report_omit_soft_deleted_tab(self):
        create_module_zipfile("charty", spec_kwargs={"html_output": True})

        workflow = Workflow.create_and_init()
        tab1 = workflow.tabs.first()
        tab2 = workflow.tabs.create(position=1, slug="tab-2-deleted", is_deleted=True)

        tab2.steps.create(order=0, module_id_name="charty", slug="step-1")

        self.assert_report_equals(reports.build_auto_report_for_workflow(workflow), [])

    def test_build_report_for_workflow_auto(self):
        create_module_zipfile("charty", spec_kwargs={"html_output": True})

        workflow = Workflow.create_and_init(has_custom_report=False)
        tab1 = workflow.tabs.first()
        step1 = tab1.steps.create(order=0, module_id_name="charty", slug="step-1")

        self.assert_report_equals(
            reports.build_report_for_workflow(workflow),
            [
                Block(
                    workflow=workflow,
                    position=0,
                    slug="block-auto-step-1",
                    block_type="Chart",
                    step=step1,
                )
            ],
        )

    def test_build_report_for_workflow_custom_empty(self):
        create_module_zipfile("charty", spec_kwargs={"html_output": True})

        workflow = Workflow.create_and_init(has_custom_report=True)
        tab1 = workflow.tabs.first()
        # Create a step. It shouldn't show up in the report because there is no
        # auto-report.
        step1 = tab1.steps.create(order=0, module_id_name="charty", slug="step-1")

        self.assert_report_equals(reports.build_report_for_workflow(workflow), [])

    def test_build_report_for_workflow_custom(self):
        workflow = Workflow.create_and_init(has_custom_report=True)
        # Just some typical report....
        tab1 = workflow.tabs.first()
        step1 = tab1.steps.create(order=0, slug="step-1")
        block1 = workflow.blocks.create(
            position=0, slug="block-1", block_type="Chart", step=step1
        )
        block2 = workflow.blocks.create(
            position=1, slug="block-2", block_type="Text", text_markdown="Hi!"
        )

        self.assert_report_equals(
            reports.build_report_for_workflow(workflow),
            [block1, block2],
        )
