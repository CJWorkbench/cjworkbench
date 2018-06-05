from .moduleimpl import ModuleImpl
import json


class RenameFromTable(ModuleImpl):

    @staticmethod
    def render(wf_module, table):
        history_json = wf_module.get_param_raw('rename-entries', 'custom')
        history = {}
        try:
            history = json.loads(history_json)
        except:
            return table

        og_columns = table.columns.tolist()
        new_columns = [history.get(col, col) for col in og_columns]
        table.columns = new_columns
        return table
