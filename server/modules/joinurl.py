from .moduleimpl import ModuleImpl
from .types import ProcessResult
from server.modules import utils
from .types import _dtype_to_column_type
import numpy as np

#------ For now, only load workbench urls

_join_type_map = 'Left|Inner|Right'.lower().split('|')

# Prefixes for column matches (and not keys)
lsuffix='_source'
rsuffix='_imported'

#TODO: Check that types match, maybe cast if necessary (or user requests)
def check_key_types(left_dtypes, right_dtypes):
    for key in left_dtypes.index:
        l_type = _dtype_to_column_type(left_dtypes.loc[key])
        r_type = _dtype_to_column_type(right_dtypes.loc[key])
        if l_type != r_type:
            raise TypeError(f'Types do not match for key column "{key}" ({l_type} and {r_type}). ' \
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
    def render(params, table, *, fetch_result, **kwargs):
        if not fetch_result:
            # User hasn't fetched yet
            return ProcessResult()

        if fetch_result.status == 'error':
            return fetch_result

        right_table = fetch_result.dataframe

        key_cols, errs = params.get_param_multicolumn('colnames', table)

        if errs:
            return ProcessResult(error=(
                'Key columns not in this workflow: '
                + ', '.join(errs)
            ))

        if not key_cols:
            return ProcessResult(table)

        _, errs = params.get_param_multicolumn('colnames', right_table)
        if errs:
            return ProcessResult(error=(
                'Key columns not in target workflow: '
                + ', '.join(errs)
            ))

        join_type_idx = params.get_param('type', 'menu')
        join_type = _join_type_map[join_type_idx]
        select_columns = params.get_param_checkbox('select_columns')

        if select_columns:
            import_cols, errs = params.get_param_multicolumn('importcols',
                                                             right_table)
            if errs:
                return ProcessResult(error=(
                    'Selected columns not in target workflow: '
                    + ', '.join(errs)
                ))
            right_table = right_table[key_cols + import_cols]

        try:
            check_key_types(table[key_cols].dtypes,
                            right_table[key_cols].dtypes)
            cast_numerical_types(table, right_table, key_cols)
            new_table = table.join(right_table.set_index(key_cols),
                                   on=key_cols, how=join_type,
                                   lsuffix=lsuffix, rsuffix=rsuffix)
        except Exception as err:  # TODO catch something specific
            return ProcessResult(error=(str(err.args[0])))

        new_table = new_table[sort_columns(table.columns, new_table.columns)]

        return ProcessResult(new_table)

    # Load external workflow data
    @staticmethod
    async def fetch(wf_module):
        params = wf_module.get_params()
        url = params.get_param_string('url')

        if not url.strip():
            return None

        try:
            workflow_id = utils.workflow_url_to_id(url)
        except ValueError as err:
            return ProcessResult(error=str(err))

        return await utils.fetch_external_workflow(wf_module, workflow_id)
