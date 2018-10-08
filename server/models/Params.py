import json
from typing import Any, Dict, List, Tuple
from .ParameterSpec import ParameterSpec
from .ParameterVal import ParameterVal


def _sanitize_column_param(pval, table_cols):
    col = pval.get_value()
    if col in table_cols:
        return col
    else:
        return ''


def _sanitize_multicolumn_param(pval, table_cols):
    cols = pval.get_value().split(',')
    cols = [c.strip() for c in cols]
    cols = [c for c in cols if c in table_cols]

    return ','.join(cols)


class Params:
    """
    Easy lookup methods for ParameterVals.

    These lookups are guaranteed to not result in any database queries as long
    as you supply ParmeterVals with `parameter_spec` prefetched. You won't need
    to lock anything here to prevent races.

    To initialize:

        vals = self.parameter_vals.prefetch_related('parameter_spec').all()
        params = Params(vals)

    The accessor names here are all legacy. They could benefit from a redesign.
    """

    def __init__(self, parameter_vals: List[ParameterVal]):
        self.vals = dict((pv.parameter_spec.id_name, pv)
                         for pv in parameter_vals)

    def get_parameter_val(self, name, expected_type=None):
        try:
            pval = self.vals[name]
        except KeyError:
            raise KeyError(
                f'Request for non-existent {expected_type} parameter {name}'
            )

        if expected_type and pval.parameter_spec.type != expected_type:
            raise ValueError(
                f'Request for {expected_type} parameter {name} '
                f'but actual type is {pval.parameter_spec.type}'
            )

        return pval

    # Retrieve current parameter values.
    # Should never throw ValueError on type conversions because
    # ParameterVal.set_value coerces
    def get_param_raw(self, name, expected_type) -> Any:
        pval = self.get_parameter_val(name, expected_type)
        return pval.value

    def get_param(self, name: str, expected_type) -> Any:
        pval = self.get_parameter_val(name, expected_type)
        return pval.get_value()

    def get_param_string(self, name: str) -> str:
        return self.get_param(name, ParameterSpec.STRING)

    def get_param_integer(self, name: str) -> int:
        return self.get_param(name, ParameterSpec.INTEGER)

    def get_param_float(self, name: str) -> float:
        return self.get_param(name, ParameterSpec.FLOAT)

    def get_param_checkbox(self, name: str) -> bool:
        return self.get_param(name, ParameterSpec.CHECKBOX)

    def get_param_radio_idx(self, name: str) -> int:
        return self.get_param(name, ParameterSpec.RADIO)

    def get_param_radio_string(self, name: str) -> str:
        pval = self.get_parameter_val(name, ParameterSpec.RADIO)
        return pval.selected_radio_item_string()

    def get_param_menu_idx(self, name: str) -> int:
        return self.get_param(name, ParameterSpec.MENU)

    def get_param_menu_string(self, name: str) -> str:
        pval = self.get_parameter_val(name, ParameterSpec.MENU)
        return pval.selected_menu_item_string()

    def get_param_secret_secret(self, id_name: str) -> Dict[str, str]:
        """Get a secret's "secret" data, or None."""
        pval = self.get_parameter_val(id_name, ParameterSpec.SECRET)

        # Don't use get_value(), since it hides the secret. (We're paranoid
        # about leaking users' secrets.)
        return pval.get_secret()

    def get_param_column(self, name, table) -> str:
        """
        Get a string, or '' if unselected or if `table` doesn't have it.

        It's easy for a user to select a missing column: just add a rename
        or column-select before the module that selected a valid column.
        """
        value = self.get_param(name, ParameterSpec.COLUMN)
        if value in table.columns:
            return value
        else:
            return ''

    def get_param_multicolumn(self, name,
                              table) -> Tuple[List[str], List[str]]:
        """
        Get (valid_colnames, invalid_colnames) lists in `table`.

        It's easy for a user to select a missing column: just add a rename
        or column-select before the module that selected a valid column.

        Columns will be ordered as they are ordered in `table`.
        """
        # multicolumn params have had a horrible hack, until at least
        # 2018-10-08 (when this comment is written and the problem is still
        # not solved). The param 'colnames' is a hidden string and the actual
        # multi-column selector doesn't have a value. So when testing types, we
        # test that the parameter name is 'colnames', _not_ the parameter type
        # (which we assume is STRING).
        try:
            pval = self.vals[name]
        except KeyError:
            raise KeyError(
                f'Request for non-existent multicolumn parameter {name}'
            )

        if (
            pval.parameter_spec.type != ParameterSpec.MULTICOLUMN
            and pval.parameter_spec.id_name != 'colnames'
        ):
            raise ValueError(
                f'Request for multicolumn parameter {name} '
                f'but actual type is {pval.parameter_spec.type}'
            )

        cols = pval.value.split(',')
        cols = [c.strip() for c in cols if c.strip()]

        table_columns = list(table.columns)

        valid = [c for c in table.columns if c in cols]
        invalid = [c for c in cols if c not in table_columns]

        return (valid, invalid)

    def get_param_json(self, name) -> Dict[str, Any]:
        """
        Parse a JSON param.

        TODO store as JSON in the database instead of parsing all the time.
        There are potential errors we don't consider here.
        """
        pval = self.get_parameter_val(name)
        s = str(pval.value)
        if s:
            return json.loads(s)
        else:
            return {}

    def to_painful_dict(self, table):
        """
        Present parameters as a dict, with some inconsistent munging.

        A `column` parameter that refers to an invalid column will be renamed
        to the empty string.

        A `multicolumn` parameter will have its values `strip()`ed and have
        invalid columns removed.

        TODO present an interface with fewer surprises.
        """
        pdict = {}
        for p in self.vals.values():
            type = p.parameter_spec.type
            id_name = p.parameter_spec.id_name

            if type == ParameterSpec.COLUMN:
                pdict[id_name] = _sanitize_column_param(p, table.columns)
            elif type == ParameterSpec.MULTICOLUMN or id_name == 'colnames':
                pdict[id_name] = _sanitize_multicolumn_param(p, table.columns)
            else:
                pdict[id_name] = p.get_value()

        return pdict
