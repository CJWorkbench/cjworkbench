from unittest.mock import patch
from cjworkbench.types import ProcessResult
from server.models import Workflow
from server.tests.utils import DbTestCase
from renderer.execute.wf_module import execute_wfmodule


async def noop(*args, **kwargs):
    return


class WfModuleTests(DbTestCase):
    @patch("server.websockets.ws_client_send_delta_async", noop)
    def test_deleted_module(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="deleted_module",
            last_relevant_delta_id=workflow.last_delta_id,
        )
        result = self.run_with_async_db(
            execute_wfmodule(workflow, wf_module, {}, tab.name, ProcessResult(), {})
        )
        expected = "Please delete this step: an administrator uninstalled its code."
        self.assertEqual(result.error, expected)
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.cached_render_result_error, expected)
