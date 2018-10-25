import pandas as pd
from .moduleimpl import ModuleImpl
from .utils import store_external_workflow, get_id_from_url
from .types import ProcessResult

_type_map = "Only include this workflow's columns|Only include matching columns|Include columns from both workflows".lower().split('|')
_join_type_map = 'outer|inner|outer'.split('|')
_source_column_name = 'Source Workflow'

class ConcatURL(ModuleImpl):
    @staticmethod
    def render(params, table, *, fetch_result, **kwargs):
        if not fetch_result:
            return ProcessResult(table)

        if fetch_result.status == 'error':
            return ProcessResult(
                table,
                error=f'The workflow you chose has an error: {fetch_result.error}'
            )

        if fetch_result.dataframe.empty:
            return ProcessResult(table,
                                 error='The workflow you chose is empty')

        type = params.get_param_menu_idx('type')
        url = params.get_param_string('url').strip()
        source_columns = params.get_param_checkbox('source_columns')

        try:
            right_id = str(get_id_from_url(url))
            concat_table = pd.concat([table, fetch_result.dataframe],
                                     keys=['Current', right_id],
                                     join=_join_type_map[type], sort=False)
        except Exception as err:  # TODO specify which errors
            return ProcessResult(table, error=str(err.args[0]))

        # Default, only includes columns of left table
        if type == 0:
            concat_table = concat_table[table.columns]

        if source_columns:
            # Allow duplicates set to True because sanitize handles name
            # collisions
            source_series = concat_table.reset_index()['level_0']
            concat_table.insert(0, _source_column_name,
                                source_series.values, allow_duplicates=True)

        return ProcessResult(concat_table)

    # Load external workflow and store
    @staticmethod
    async def fetch(wf_module):
        params = wf_module.get_params()
        url = params.get_param_string('url').strip()
        if not url:
            return

        try:
            result = store_external_workflow(wf_module, url)
        except Exception as err:
            result = ProcessResult(error=str(err))

        await ModuleImpl.commit_result(wf_module, result)
