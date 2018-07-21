from .moduleimpl import ModuleImpl
import json


class ReorderFromTable(ModuleImpl):
    @staticmethod
    def render(wf_module, table):
        history = wf_module.get_param_raw('reorder-history', 'custom')

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

            # Our original input columns can get moved or deleted, but we'll give it a shot if indices are in range
            if from_idx >= len(columns) or to_idx >= len(columns):
                continue

            moved = columns.pop(from_idx)
            columns.insert(to_idx, moved)

        return table[columns]
