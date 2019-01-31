import json
from typing import Any, Dict, List, Union
import numpy as np
import pandas as pd
from .moduleimpl import ModuleImpl
from .types import ProcessResult


def _str_categories(series):
    """Build a Categories series (casting everything to category)."""
    # 1. Exit quickly when our input is sane
    if hasattr(series, 'cat'):
        return series

    # 2. Cast non-str to str
    if series.dtype != object:
        t = series.astype(str)
        t[series.isna()] = np.nan
        series = t

    # 3. Categorize str
    return series.astype('category')


class RefineSpec:
    """Describe how to modify a column.

    This is a set of instructions:

    1. `renames` renames every key to its value, _not_ recursively.
    """

    def __init__(self, renames: Dict[str, str]={}):
        self.renames = renames

    def apply_renames(self, series: pd.Series) -> pd.Series:
        """Build a series with changed categories."""
        # 1. Set new categories
        # 2. Copy all values that are in old _and_ new category list, leaving
        #    the rest as NA
        # (this is a one-liner in pandas)
        new_categories = set(series.cat.categories) \
            .difference(self.renames.keys()) \
            .union(self.renames.values())

        # Sort categories, simply to make unit tests pass. (They can't predict
        # category order otherwise, and assert_frame_equal() treats different
        # orders as different data frames.)
        #
        # This may be slow in some datasets.
        new_categories = sorted(new_categories)

        ret = series.cat.set_categories(new_categories)

        # 3. "Rename" by setting old-valued data to new values.
        #
        # This algorithm _should_ be fairly quick, but it hasn't been
        # benchmarked. For every "group" we're renaming _to_, select matching
        # _from_ rows from the original series and set their value.
        #
        # This amounts to G renames, each costing O(N). Total O(NG).
        grouped_renames = {}
        for k, v in self.renames.items():
            try:
                grouped_renames[v].append(k)
            except KeyError:
                grouped_renames[v] = [k]

        for new_value, old_values in grouped_renames.items():
            ret[series.isin(old_values)] = new_value

        return ret

    def apply(self, table, column):
        # 1. Turn into categories
        series = _str_categories(table[column])

        # 2. Rename all the categories
        series = self.apply_renames(series)
        table[column] = series

        return table

def migrate_params_v0_to_v1(column: str, refine: str) -> Dict[str, Any]:
    """
    Parse deprecated refine parameters.

    This deprecated format was an Array of instructions which were applied
    in sequence. That made for complex interactions: renaming A to B and
    then B to C would result in A being renamed to C; but renaming B to C
    and then A to B would not. There was no blacklist: there was a "select"
    operation, which toggles: the first appearance of a value meant
    "blacklist" and the second appearance meant "whitelist". Order
    mattered: [toggle A; rename A to B; toggle B] would wouldadvance

    `refine` is JSON-encoded and looks like this:

    [
        {'type': 'select', 'column': 'A', 'content': {'value': 'x'}},
        {'type': 'change', 'column': 'A',
         'content': {'fromVal': 'x', 'toVal': 'y'}},
    ]

    Rules:

    * Ignore anything with the wrong 'column'
    * Ignore blacklist for new module specs as of 1/29/2019
    * 'select' toggles a value onto and then off the blacklist
    * 'change' edits values
    """
    renames = {}

    for item in refine:
        if not isinstance(item, dict):
            raise ValueError('Not a dict')

        try:
            item_column = str(item['column'])
        except KeyError:
            raise ValueError('Change is missing "column" key')
        if item_column != column:
            continue

        try:
            item_type = str(item['type'])
        except KeyError:
            raise ValueError('Change is missing "type" key')

        try:
            # raise ValueError on non-dict
            item_content = dict(item['content'])
        except KeyError:
            raise ValueError('Change is missing "content" key')

        if item_type == 'change':
            try:
                from_val = str(item_content['fromVal'])
                to_val = str(item_content['toVal'])
            except KeyError:
                raise ValueError('Missing "content.fromVal" or '
                                 '"content.toVal"')

            renames2 = dict(renames)  # shallow copy
            # Edit every previous rename (x => y, y => z becomes x => z)
            for k, v in renames.items():
                if v == from_val:
                    if k == to_val:
                        del renames2[k]
                    else:
                        renames2[k] = to_val
            # Then include the user's rename
            renames2[from_val] = to_val

            renames = renames2

        # Filtering removed from Refine, previous blacklists now ignored -ER 1/29/2019
        elif item_type == 'select':
            continue

        else:
            raise ValueError(f'Invalid "type": {item_type}')

    return {
        'column': column,
        'refine': json.dumps({
            'renames': renames,
        }),
    }


def migrate_params_v1_to_v2(column: str,
                            refine: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-decode `refine`."""
    # Remove blacklist from 'refine' since module as of 1/29/2018 no longer filters
    new_refine = {'renames': refine['renames']}
    return {
        'column': column,
        'refine': new_refine,
    }


def migrate_params(params: Dict[str, Any]) -> Dict[str, Any]:
    # v0: 'column' (Column), 'refine' (JSON-encoded array of ops)
    try:
        column = params['column']
        refine = params['refine']
        refine_decoded = json.loads(refine)
        refine_decoded[0]
        is_v0 = True
    except (ValueError, KeyError, TypeError):
        # These all mean `params` aren't v0, so we should continue:
        #
        # ValueError: invalid JSON
        # TypeError: refine is not str (probably because it's a dict)
        # KeyError: refine_decoded is a dict, not an array
        is_v0 = False
    if is_v0:
        params = migrate_params_v0_to_v1(column, refine_decoded)

    # v1: 'column' (Column), 'refine' (JSON-encoded {renames, blacklist})
    try:
        column = params['column']
        refine = params['refine']
        refine_decoded = json.loads(refine)
        refine_decoded['renames']
        is_v1 = True
    except (ValueError, TypeError):
        # These all mean `params` aren't v0, so we should continue:
        #
        # ValueError: invalid JSON
        # TypeError: refine is not str (probably because it's a dict)
        is_v1 = False
    if is_v1:
        params = migrate_params_v1_to_v2(column, refine_decoded)

    # v2: 'column' (Column), 'refine' ({renames, blacklist} dict)
    return params


def render(params, table, **kwargs):
    # 'refine' holds the edits
    column: str = params['column']
    if not column:
        # No user input yet
        return ProcessResult(table)

    refine = params['refine']
    # Omit blacklist
    spec = RefineSpec(refine.get('renames', {}))
    table = spec.apply(table, column)

    return ProcessResult(table)
