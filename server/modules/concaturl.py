from .moduleimpl import ModuleImpl
from .types import ProcessResult
from .utils import store_external_workflow, get_id_from_url
import pandas as pd

_type_map = "Only include this workflow's columns|Only include matching columns|Include columns from both workflows".lower().split('|')
_join_type_map = 'outer|inner|outer'.split('|')
_source_column_name = 'Source Workflow'

class ConcatURL(ModuleImpl):
    @staticmethod
    def render(wf_module, table):
        try:
            right_table = wf_module.retrieve_fetched_table()
        except Exception:
            right_table = None

        if right_table is None or right_table.empty or table is None:
            return ProcessResult(table,
                                 wf_module.error_msg)

        type = wf_module.get_param_menu_idx('type')
        url = wf_module.get_param_string('url').strip()
        source_columns = wf_module.get_param_checkbox('source_columns')

        try:
            right_id = get_id_from_url(url)
            concat_table = pd.concat([table, right_table], keys=['Current', right_id], join=_join_type_map[type], sort=False)
        except Exception as err:
            return ProcessResult(table, error=str(err.args[0]))

        # Default, only includes columns of left table
        if type == 0:
            concat_table = concat_table[table.columns]

        if source_columns:
            # Allow duplicates set to True because sanitize handles name collisions
            source_series = concat_table.reset_index()['level_0']
            concat_table.insert(0, _source_column_name, source_series.values, allow_duplicates=True)

        return ProcessResult(concat_table)

    # Load external workflow and store
    @staticmethod
    def event(wf_module, **kwargs):
        url = wf_module.get_param_string('url').strip()
        if not url:
            return

        try:
            store_external_workflow(wf_module, url)
        except Exception as err:
            ModuleImpl.commit_result(wf_module, ProcessResult(error=str(err.args[0])))
            return
