from .add_step import AddStep
from .add_tab import AddTab
from .delete_step import DeleteStep
from .delete_tab import DeleteTab
from .duplicate_tab import DuplicateTab
from .init_workflow import InitWorkflow
from .reorder_steps import ReorderSteps
from .reorder_tabs import ReorderTabs
from .set_step_data_version import SetStepDataVersion
from .set_step_note import SetStepNote
from .set_step_params import SetStepParams
from .set_tab_name import SetTabName
from .set_workflow_title import SetWorkflowTitle

# Delta.command uses NAME_TO_COMMAND. So if you change a class name, the DB
# field changes. (Changing a class name will make Django prompt the dev to
# add a migration.)
NAME_TO_COMMAND = {
    cls.__name__: cls()  # instantiated! A singleton object per command
    for cls in (
        AddStep,
        AddTab,
        DeleteStep,
        DeleteTab,
        DuplicateTab,
        InitWorkflow,
        ReorderSteps,
        ReorderTabs,
        SetStepDataVersion,
        SetStepNote,
        SetStepParams,
        SetTabName,
        SetWorkflowTitle,
    )
}
