from typing import Awaitable, Callable
from django.contrib.auth.models import User
import pandas as pd
from server.models import Params
from .types import ProcessResult


# Base class for all modules. Really just a reminder of function signatures
class ModuleImpl:
    @staticmethod
    def render(table: pd.DataFrame, params: Params, **kwargs) -> ProcessResult:
        return ProcessResult(table)

    @staticmethod
    async def fetch(
        params: Params,
        *,
        workflow_id: int,
        get_input_dataframe: Callable[[], Awaitable[pd.DataFrame]],
        get_stored_dataframe: Callable[[], Awaitable[pd.DataFrame]],
        get_workflow_owner: Callable[[], Awaitable[User]]
    ) -> ProcessResult:
        pass
