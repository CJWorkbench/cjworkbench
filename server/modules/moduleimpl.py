import pandas as pd
from server.models import Params, WfModule
from .types import ProcessResult


# Base class for all modules. Really just a reminder of function signatures
class ModuleImpl:
    @staticmethod
    def render(params: Params, table: pd.DataFrame, **kwargs) -> ProcessResult:
        return ProcessResult(table)

    @staticmethod
    async def fetch(wfm: WfModule) -> None:
        pass
