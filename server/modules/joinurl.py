from .moduleimpl import ModuleImpl
from .types import ProcessResult
from .utils import store_external_workflow
from .types import _dtype_to_column_type
import numpy as np

#------ For now, only load workbench urls

_join_type_map = 'Left|Inner|Right'.lower().split('|')

# Prefixes for column matches (and not keys)
lsuffix='_source'
rsuffix='_imported'

def check_cols_right(right, keys, import_cols=None):
    diff = set(keys) - set(right.columns)
    if diff:
        raise Exception(
            f'Key columns not in target workflow: {diff}'
        )
    if import_cols:
        diff = set(import_cols) - set(right.columns)
        if diff:
            raise Exception(
                f'Import columns not in target workflow: {diff}'
            )
    return


#TODO: Check that types match, maybe cast if necessary (or user requests)
def check_key_types(left_dtypes, right_dtypes):
    for key in left_dtypes.index:
        l_type = _dtype_to_column_type(left_dtypes.loc[key])
        r_type = _dtype_to_column_type(right_dtypes.loc[key])
        if l_type != r_type:
            raise TypeError(f"Types do not match for key column '{key}' ({l_type} and {r_type}). " \
                            f'Please use a type conversion module to make these column types consistent.')

# If column types are numeric but do not match (ie. int and float) cast as float to match
def cast_numerical_types(left_table, right_table, keys):
    for key in keys:
        if np.issubdtype(left_table[key].dtype, np.number):
            if left_table[key].dtype != right_table[key].dtype:
                left_table[key] = left_table[key].astype(np.float64)
                right_table[key] = right_table[key].astype(np.float64)

# Insert new duplicate column next to matching source column for legibility
def sort_columns(og_columns, new_columns):
    result = list(new_columns)
    for column in og_columns:
        new_left = column + lsuffix
        new_right = column + rsuffix
        if new_left in new_columns and new_right in new_columns:
            result.pop(result.index(new_right))
            result.insert(result.index(new_left) + 1, new_right)
    return result

class JoinURL(ModuleImpl):
    @staticmethod
    def render(wf_module, table):
        try:
            right_table = wf_module.retrieve_fetched_table()
        except Exception:
            right_table = None

        if right_table is None or right_table.empty:
            return ProcessResult(table,
                                 wf_module.error_msg)

        key_cols = wf_module.get_param_string('colnames')
        join_type_idx = wf_module.get_param('type', 'menu')
        join_type = _join_type_map[join_type_idx]

        if key_cols == '':
            return ProcessResult(table)

        key_cols = key_cols.split(',')

        try:
            # Check if import columns exists in right table
            if wf_module.get_param_string('importcols').strip():
                import_cols = wf_module.get_param_string('importcols').strip().split(',')
                check_cols_right(right_table, key_cols, import_cols)
                right_table = right_table[key_cols + import_cols]
            else:
                check_cols_right(right_table, key_cols)

            check_key_types(table[key_cols].dtypes, right_table[key_cols].dtypes)
            cast_numerical_types(table, right_table, key_cols)
            new_table = table.join(right_table.set_index(key_cols), on=key_cols, how=join_type, lsuffix=lsuffix, rsuffix=rsuffix)
        except Exception as err:
            return ProcessResult(table, error=(str(err.args[0])))

        new_table = new_table[sort_columns(table.columns, new_table.columns)]

        return ProcessResult(new_table)

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
