from .moduleimpl import ModuleImpl
import json


class ReorderFromTable(ModuleImpl):
    @staticmethod
    def render(wf_module, table):
        # Error message for when reorder history is corrupted
        CORRUPT_HISTORY_ERROR = 'Reorder history is corrupted. Did you remove one of the input columns?'

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
            if from_idx >= len(columns) or to_idx >= len(columns):
                return CORRUPT_HISTORY_ERROR
            if columns[from_idx] != entry['column']:
                return CORRUPT_HISTORY_ERROR
            moved = columns.pop(from_idx)
            if to_idx < from_idx:
                columns.insert(to_idx, moved)
            else:
                columns.insert(to_idx - 1, moved)

        return table[columns]
