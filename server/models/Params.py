import json
from typing import Any, Dict, List, Tuple
from .ParameterSpec import ParameterSpec


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

        specs = wf_module.parameter_specs.all()
        values = { 'param1': 1, 'param2': 'something', ... }
        secrets = { 'secret1': { 'name': '@adamhooper', 'secret': ... } }
        params = Params(specs, values, secrets)

    The accessor names here are all legacy. They could benefit from a redesign.
    """

    def __init__(self, specs: List[ParameterSpec], values: Dict[str, Any],
                 secrets: Dict[str, Any]):
        self.specs = specs
        self.specs_by_name = dict((spec.id_name, spec) for spec in specs)
        self.values = values
        self.secrets = secrets

    def get_param_typed(self, name, expected_type):
        """
        Return ParameterVal value, with a typecheck.

        Raise ValueError if expected type is wrong.

        Raise KeyError on invalid parameter.
        """
        pspec = self.specs_by_name[name]  # raises KeyError

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

    def get_param_secret_secret(self, name: str) -> Dict[str, str]:
        """Get a secret's "secret" data, or None."""
        try:
            secret = self.secrets[name]
        except KeyError:
            secret = None

        if secret is None:
            return None
        else:
            return secret['secret']

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
        value = self.get_param_typed(name, ParameterSpec.MULTICOLUMN)

        cols = value.split(',')
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
        ret = {}

        for pspec in self.specs:
            name = pspec.id_name
            if pspec.type == ParameterSpec.SECRET:
                try:
                    secret = self.secrets[name]
                except KeyError:
                    secret = None

                if secret:
                    ret[name] = {'name': secret['name']}
                else:
                    ret[name] = None
            else:
                ret[name] = self.values[name]

        return ret

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
        for pspec in self.specs:
            type = pspec.type
            id_name = pspec.id_name
            value = self.values[id_name]

            if type == ParameterSpec.SECRET:
                try:
                    secret = self.secrets[id_name]
                except KeyError:
                    secret = None

                if secret:
                    pdict[id_name] = {'name': secret['name']}
                else:
                    pdict[id_name] = None
            if type == ParameterSpec.COLUMN:
                pdict[id_name] = _sanitize_column_param(value, table.columns)
            elif type == ParameterSpec.MULTICOLUMN or id_name == 'colnames':
                pdict[id_name] = _sanitize_multicolumn_param(value,
                                                             table.columns)
            else:
                pdict[id_name] = value

        return pdict
