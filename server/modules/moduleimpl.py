from typing import Optional, Dict, Any
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
    async def event(wfm: WfModule, **kwargs):
        pass

    @staticmethod
    async def commit_result(wf_module: WfModule, result: ProcessResult,
                            stored_object_json: Optional[Dict[str, Any]]=None
                            ) -> None:
        """
        Store fetched result, if it is a change from wfm's existing data.

        Save the WfModule's `status` and `fetch_error`.

        Set wfm.last_update_check, regardless.

        If there is no error and there is new data, create (and run) a
        ChangeDataVersionCommand.

        Notify the user.
        """
        if result.dataframe.empty and result.error:
            workflow = wf_module.workflow
            with workflow.cooperative_lock():
                wf_module.last_update_check = timezone.now()
                wf_module.fetch_error = result.error
                wf_module.is_busy = False
                wf_module.save()
            await websockets.ws_client_rerender_workflow_async(workflow)
        else:
            await save_result_if_changed(
                wf_module,
                result,
                stored_object_json=stored_object_json
            )
