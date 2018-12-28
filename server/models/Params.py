import json
from typing import Any, Dict, List, Tuple
from .ParameterSpec import ParameterSpec
from .ParameterVal import ParameterVal


def _sanitize_column_param(value, table_cols):
    if value in table_cols:
        return value
    else:
        return ''


def _sanitize_multicolumn_param(value, table_cols):
    cols = value.split(',')
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
        params = Params.from_parameter_vals(vals)

    The accessor names here are all legacy. They could benefit from a redesign.
    """

    def __init__(self, specs: List[ParameterSpec], values: Dict[str, Any],
                 secrets: Dict[str, Any]):
        self.specs = specs
        self.values = values
        self.secrets = secrets

    @classmethod
    def from_parameter_vals(cls, parameter_vals: List[ParameterVal]):
        """
        DEPRECATED. We'd win by nixing Parameter(Val|Spec) DB models.

        https://www.pivotaltracker.com/story/show/162704742
        """
        specs = {}
        values = {}
        secrets = {}

        for pval in parameter_vals:
            spec = pval.parameter_spec
            name = spec.id_name

            specs[name] = spec

            if spec.type == ParameterSpec.SECRET:
                if pval.value:
                    parsed = json.loads(pval.value)
                    values[name] = {'name': parsed['name']}
                    secrets[name] = parsed['secret']
                else:
                    values[name] = None
                    secrets[name] = None
            else:
                values[name] = spec.str_to_value(pval.value)

        return cls(specs, values, secrets)

    def get_param_typed(self, name, expected_type):
        """
        Return ParameterVal value, with a typecheck.

        Raise ValueError if expected type is wrong.

        Raise KeyError on invalid parameter.
        """
        pspec = self.specs[name]  # raises KeyError

        if expected_type and pspec.type != expected_type:
            raise ValueError(
                f'Request for {expected_type} parameter {name} '
                f'but actual type is {pspec.type}'
            )

        return self.get_param(name)

    def get_param(self, name) -> Any:
        """
        Return ParameterVal value, of the parameter's type.

        Raise KeyError on invalid parameter.
        """
        return self.values[name]  # raises KeyError

    def get_param_string(self, name: str) -> str:
        return self.get_param_typed(name, ParameterSpec.STRING)

    def get_param_integer(self, name: str) -> int:
        return self.get_param_typed(name, ParameterSpec.INTEGER)

    def get_param_float(self, name: str) -> float:
        return self.get_param_typed(name, ParameterSpec.FLOAT)

    def get_param_checkbox(self, name: str) -> bool:
        return self.get_param_typed(name, ParameterSpec.CHECKBOX)

    def get_param_radio_idx(self, name: str) -> int:
        return self.get_param_typed(name, ParameterSpec.RADIO)

    def get_param_menu_idx(self, name: str) -> int:
        return self.get_param_typed(name, ParameterSpec.MENU)

    def get_param_secret_secret(self, id_name: str) -> Dict[str, str]:
        """Get a secret's "secret" data, or None."""
        return self.secrets[id_name]

    def get_param_column(self, name, table) -> str:
        """
        Get a string, or '' if unselected or if `table` doesn't have it.

        It's easy for a user to select a missing column: just add a rename
        or column-select before the module that selected a valid column.
        """
        value = self.get_param_typed(name, ParameterSpec.COLUMN)
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

        Sometimes, database values are already JSON. Other times, they're
        stored as ``str``. When given ``str``, we decode here (or raise
        ValueError on invalid JSON).

        TODO nix the duality. That way, users can store strings....
        """
        value = self.get_param(name)
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

    def as_dict(self):
        """Present parameters as a dict."""
        return self.values

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
        for pspec in self.specs.values():
            type = pspec.type
            id_name = pspec.id_name
            value = self.values[id_name]

            # Do not worry about ParameterSpec.SECRET: we only use
            # to_painful_dict() for external modules, and none of those have
            # secrets.
            if type == ParameterSpec.COLUMN:
                pdict[id_name] = _sanitize_column_param(value, table.columns)
            elif type == ParameterSpec.MULTICOLUMN or id_name == 'colnames':
                pdict[id_name] = _sanitize_multicolumn_param(value,
                                                             table.columns)
            else:
                pdict[id_name] = value

        return pdict
