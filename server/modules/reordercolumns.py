import json
from typing import Any, Dict


def parse_json_param(value) -> Dict[str, Any]:
    """
    Parse a JSON param.

    Sometimes, database values are already JSON. Other times, they're
    stored as ``str``. When given ``str``, we decode here (or raise
    ValueError on invalid JSON).

    TODO nix the duality. That way, users can store strings....
    """
    if isinstance(value, str):
        if value:
            return json.loads(value)  # raises ValueError
        else:
            # [2018-12-28] `None` seems more appropriate, but `{}` is
            # backwards-compatibile. TODO migrate database to nix this
            # ambiguity.
            return {}
    else:
        return value


def render(table, params):
    # Entries should appear in chronological order as new
    # operations are appended to the end of the stack
    history_entries = parse_json_param(params['reorder-history'])

    if not history_entries:
        return table  # no reorders

    columns = table.columns.tolist()

    for entry in history_entries:
        from_idx = int(entry['from'])
        to_idx = int(entry['to'])

        # Our original input columns can get moved or deleted, but we'll
        # give it a shot if indices are in range
        if from_idx >= len(columns) or to_idx >= len(columns):
            continue

        moved = columns.pop(from_idx)
        columns.insert(to_idx, moved)

    return table[columns]
