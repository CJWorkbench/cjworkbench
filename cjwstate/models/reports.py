import logging
from typing import FrozenSet, List

from .block import Block
from .step import Step
from .module_registry import MODULE_REGISTRY
from .workflow import Workflow


logger = logging.getLogger(__name__)


Report = List[Block]


def _get_charty_module_id_names() -> FrozenSet[str]:
    module_id_names = []
    for module_id_name, module_zipfile in MODULE_REGISTRY.all_latest().items():
        try:
            if module_zipfile.get_spec().html_output:
                module_id_names.append(module_id_name)
        except Exception:
            logger.exception(
                "Module registry returned invalid module %s; ignoring", module_id_name
            )
    return frozenset(module_id_names)


def build_auto_report_for_workflow(workflow: Workflow) -> Report:
    """Build an 'auto-report' for the Workflow.

    An 'auto-report' comprises all the Charts a workflow can possibly have, in
    the order of Tabs/Steps in the workflow.

    To transition from auto-report to customizable report, the caller should
    set `workflow.has_custom_report = True` and save all the blocks.
    """
    module_id_names = _get_charty_module_id_names()
    blocks = [
        Block(
            workflow=workflow,
            position=position,
            slug=f"block-auto-{step.slug}",
            block_type="Chart",
            step=step,
        )
        for position, step in enumerate(
            step
            for step in Step.live_in_workflow(workflow)
            if step.module_id_name in module_id_names
        )
    ]
    return blocks


def build_custom_report_for_workflow(workflow: Workflow) -> Report:
    """Query the custom report for the Workflow."""
    return list(workflow.blocks.prefetch_related("step", "tab").all())


def build_report_for_workflow(workflow: Workflow) -> Report:
    """Query or build a report for the Workflow.

    If `workflow.has_custom_report == True`, then this looks up the existing
    `workflow.blocks`. Otherwise, it calls `build_auto_report_for_workflow()`.
    """
    if workflow.has_custom_report:
        return build_custom_report_for_workflow(workflow)
    else:
        return build_auto_report_for_workflow(workflow)
