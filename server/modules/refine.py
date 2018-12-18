from typing import Any, Dict, List, Union
import pandas as pd
import numpy as np
from .moduleimpl import ModuleImpl
from .types import ProcessResult
import json


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

    def __init__(self, renames: Dict[str, str]={}, blacklist: List[str]=[]):
        self.renames = renames
        self.blacklist = blacklist

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

    def filter_table(self, table: pd.DataFrame,
                     series: pd.Series) -> pd.DataFrame:
        """
        Filter dataframe by blacklist.

        Arguments:

        table -- table to filter
        series -- already-renamed categories series
        """
        if self.blacklist:
            blacklist = series.cat.categories.intersection(self.blacklist)
            mask = ~series.isin(blacklist)
            table[series.name] = series.cat.remove_categories(blacklist)
            return table[mask]
        else:
            # common case
            return table

    def apply(self, table, column):
        # 1. Turn into categories
        series = _str_categories(table[column])

        # 2. Rename all the categories
        series = self.apply_renames(series)
        table[column] = series

        # 3. Filter
        return self.filter_table(table, series)

    @staticmethod
    def parse_v0(column: str, arr: List[Dict[str, Any]]) -> 'RefineSpec':
        """
        Parse deprecated refine parameters.

        This deprecated format was an Array of instructions which were applied
        in sequence. That made for complex interactions: renaming A to B and
        then B to C would result in A being renamed to C; but renaming B to C
        and then A to B would not. There was no blacklist: there was a "select"
        operation, which toggles: the first appearance of a value meant
        "blacklist" and the second appearance meant "whitelist". Order
        mattered: [toggle A; rename A to B; toggle B] would wouldadvance

        Input looks like this:

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

        for item in arr:
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

        return RefineSpec(renames, list(blacklist))

    @staticmethod
    def parse_v1(edits: Dict[str, Any]) -> 'RefineSpec':
        """Parse a RefineSpec from JSON-decoded data."""
        try:
            renames = edits['renames']
        except KeyError:
            raise ValueError('Missing "renames"')

        try:
            blacklist = edits['blacklist']
        except KeyError:
            raise ValueError('Missing "blacklist"')

        try:
            renames = dict([(str(k), str(v)) for k, v in renames.items()])
        except AttributeError:
            raise ValueError('"renames" must be a dict from old value to new')

        try:
            blacklist = list([str(v) for v in blacklist])
        except TypeError:
            raise ValueError('"blacklist" must be a list of values')

        return RefineSpec(renames, blacklist)

    @staticmethod
    def parse(column: str, edits: Union[Dict[str, Any],
                                        List[Dict[str, Any]]]) -> 'RefineSpec':
        """
        Parse a RefineSpec from JSON-decoded data.

        If 'edits' is a List, then it's a v0 spec and we'll use `parse_v0()`.
        """
        if isinstance(edits, list):
            return RefineSpec.parse_v0(column, edits)
        else:
            return RefineSpec.parse_v1(edits)


class Refine(ModuleImpl):
    @staticmethod
    def render(params, table, **kwargs):
        # 'refine' holds the edits
        edits = params.get_param_json('refine')
        column = params.get_param_column('column', table)

        if not edits or not column:
            # No user input yet
            return ProcessResult(table)

        try:
            spec = RefineSpec.parse(column, edits)
        except ValueError as err:
            return ProcessResult(error=f'Internal error: {str(err)}')

        table = spec.apply(table, column)

        return ProcessResult(table)
