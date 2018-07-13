from django.utils import timezone
from server.models import WfModule
from server.versions import save_result_if_changed
from server import websockets
from .types import ProcessResult


# Base class for all modules. Really just a reminder of function signatures
class ModuleImpl:
    @staticmethod
    def render(wfmodule: WfModule, table):
        return table

    @staticmethod
    def event(wfm: WfModule, **kwargs):
        pass

    @staticmethod
    def commit_result(wf_module: WfModule, result: ProcessResult) -> None:
        """Store retrieved data table, if it is a change from wfm's existing data.

        Save the WfModule's `status` and `error_msg`.

        Set wfm.last_update_check, regardless.

        If there is no error and there is new data, create (and run) a
        ChangeDataVersionCommand.

        Notify the user.
        """
        if result.dataframe.empty and result.error:
            with wf_module.workflow.cooperative_lock():
                wf_module.last_update_check = timezone.now()
                wf_module.error_msg = result.error
                wf_module.status = WfModule.ERROR
                wf_module.save()
            websockets.ws_client_rerender_workflow(wf_module.workflow)
        else:
            save_result_if_changed(wf_module, result)
