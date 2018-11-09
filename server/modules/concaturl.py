import pandas as pd
from .moduleimpl import ModuleImpl
from server.modules import utils
from .types import ProcessResult

_join_type_map = 'outer|inner|outer'.split('|')
_source_column_name = 'Source Workflow'


class ConcatURL(ModuleImpl):
    @staticmethod
    def render(params, table, *, fetch_result, **kwargs):
        if not fetch_result:
            return ProcessResult(table)

        if fetch_result.status == 'error':
            return ProcessResult(table, error=fetch_result.error)

        if fetch_result.dataframe.empty:
            return ProcessResult(table,
                                 error='The workflow you chose is empty')

        type = params.get_param_menu_idx('type')
        url = params.get_param_string('url').strip()
        source_columns = params.get_param_checkbox('source_columns')

        try:
            right_id = str(utils.workflow_url_to_id(url))
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

    # Load external workflow data
    @staticmethod
    async def fetch(wf_module):
        params = wf_module.get_params()
        url = params.get_param_string('url')

        if not url.strip():
            return None

        try:
            workflow_id = utils.workflow_url_to_id(url)
        except ValueError as err:
            return ProcessResult(error=str(err))

        return await utils.fetch_external_workflow(wf_module, workflow_id)
