from .moduleimpl import ModuleImpl
import json


class ReorderFromTable(ModuleImpl):
    def render(wf_module, table):
        history = wf_module.get_param_raw('history', 'custom')

        # NOP if history is empty
        if len(history.strip()) == 0:
            return table

        # Entries should appear in chronological order as new
        # operations are appended to the end of the stack
        history_entries = json.loads(history)

        columns = table.columns.tolist()

        for entry in history_entries:
            from_idx = int(entry['from'])
            to_idx = int(entry['to'])
            moved = columns.pop(from_idx)
            if to_idx < from_idx:
                columns.insert(to_idx, moved)
            else:
                columns.insert(to_idx - 1, moved)

        return table[columns]