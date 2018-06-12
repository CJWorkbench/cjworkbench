from .moduleimpl import ModuleImpl
import json


class RenameFromTable(ModuleImpl):

    # Rename entry structure: Dictionary of {old_name: new_name}

    @staticmethod
    def render(wf_module, table):
        entries_json = wf_module.get_param_raw('rename-entries', 'custom')
        entries = {}
        try:
            entries = json.loads(entries_json)
        except:
            return table

        og_columns = table.columns.tolist()
        new_columns = [entries.get(col, col) for col in og_columns]
        table.columns = new_columns
        return table
