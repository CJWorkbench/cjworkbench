import json
from typing import Any, Dict
import numpy as np
import pandas as pd


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
    2. If `blacklist` is non-empty, the results from step 2 are filtered so
       blacklisted values are missing.
    """

    def __init__(self, renames: Dict[str, str] = {}):
        self.renames = renames

    def apply_renames(self, series: pd.Series) -> pd.Series:
        """Build a series with changed categories."""
        # 1. Build list of new_categories from old_categories and renames
        old_categories = set(series.cat.categories)
        # filter self.renames: ignore renames of categories that don't exist.
        # (They can happen if the input changes after the user sets params.)
        renames = {k: v for k, v in self.renames.items()
                   if k in old_categories}
        new_categories = set(series.cat.categories) \
            .difference(renames.keys()) \
            .union(renames.values())
        # Sort categories, simply to make unit tests pass. (They can't predict
        # category order otherwise, and assert_frame_equal() treats different
        # orders as different data frames.)
        #
        # This may be slow in some datasets.
        new_categories = sorted(new_categories)

        # 2. Build "code_map", a translation table from old "code" to new
        # "code". (A Categorical series is an array of integer codes and object
        # categories.)
        new_categories_lookup = {c: i for i, c in enumerate(new_categories)}
        code_map = series.cat.categories.map(lambda c: (
            new_categories_lookup[renames[c]] if c in renames
            else new_categories_lookup[c]
        ))

        # 3. Find "new_codes" -- given series.cat.categories, which index into
        # series.cat.categories, find codes that would index into
        # new_categories.
        new_codes = series.cat.codes.map(
            lambda x: -1 if x == -1 else code_map[x]
        )

        # 4. Cast to a Series.
        return pd.Series(pd.Categorical.from_codes(new_codes, new_categories))

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
    * 'select' toggles a value onto and then off the blacklist
    * 'change' edits values -- and the blacklist applies to the new value,
      not the old one
    """
    renames = {}
    blacklist = set()

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

            # Bug: this sequence:
            # 1. Toggle 'A' into blacklist
            # 2. Rename 'A' to 'B', where 'B' is not in the blacklist
            # Expected results: is 'B' blacklisted? Before, it would depend
            # on the table: if 'B' was present in the table and not
            # blacklisted, no. If 'B' was missing before the rename, then
            # yes.
            #
            # We don't look at the table any more, so we can't
            # differentiate. The best approach is probably, 'if B is
            # blacklisted, keep it blacklisted; otherwise don't.'
            blacklist.discard(from_val)  # adopt to_val's state

        elif item_type == 'select':
            try:
                value = str(item_content['value'])
            except KeyError:
                raise ValueError('Missing "content.value"')

                # Toggle
            try:
                blacklist.remove(value)
            except KeyError:
                blacklist.add(value)

        else:
            raise ValueError(f'Invalid "type": {item_type}')

    return {
        'column': column,
        'refine': json.dumps({
            'renames': renames,
            'blacklist': list(blacklist),
        }),
    }


def migrate_params_v1_to_v2(column: str,
                            refine: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-decode `refine`."""
    return {
        'column': column,
        'refine': refine,
    }


def migrate_params_v2_to_v3(column: str,
                            refine: Dict[str, Any]) -> Dict[str, Any]:
    """v3 of `refine` does not filter, so blacklist can be ignored"""
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
        if refine == '':
            refine_decoded = {'renames': {}, 'blacklist': []}
        else:
            refine_decoded = json.loads(refine)
        refine_decoded['renames']
        refine_decoded['blacklist']
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
    try:
        refine = params['refine']
        refine['blacklist']
        is_v2 = True
    except (KeyError):
        # These all mean `params` aren't v2, so we should continue:
        #
        # KeyError: 'blacklist' not in params, already v3
        is_v2 = False
    if is_v2:
        params = migrate_params_v2_to_v3(column, refine)
    # v3: 'column' (Column), 'refine' ({renames} dict)

    return params


def render(table, params, **kwargs):
    # 'refine' holds the edits
    column: str = params['column']
    if not column:
        # No user input yet
        return table

    refine = params['refine']
    spec = RefineSpec(refine.get('renames', {}))
    table = spec.apply(table, column)

    return table
