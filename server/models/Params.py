import json
from typing import Any, Dict, List, Tuple
from .param_field import ParamDTypeString, ParamDTypeInteger, \
        ParamDTypeFloat, ParamDTypeBoolean, ParamDTypeEnum, \
        ParamDTypeColumn, ParamDTypeMulticolumn, ParamDTypeDict


class Params:
    """
    Wrap params and secrets to pass to module `fetch` and `render`.

    To initialize:

        schema = wf_module.module_version.param_schema
        values = { 'param1': 1, 'param2': 'something', ... }
        secrets = { 'secret1': { 'name': '@adamhooper', 'secret': ... } }
        params = Params(schema, values, secrets)

    The accessor names here are all legacy. They could benefit from a redesign.
    """

    def __init__(self, schema: ParamDTypeDict, values: Dict[str, Any],
                 secrets: Dict[str, Any]):
        self.schema = schema
        self.values = values
        self.secrets = secrets

    def __getitem__(self, name):
        """
        Return parameter value.

        Raise KeyError on invalid parameter.
        """
        return self.values[name]  # raises KeyError

    def get(self, value, default=None):
        """
        Return parameter value.

        Return default on invalid parameter.
        """
        return self.values.get(value, default)

    def get_param_typed(self, name, expected_type):
        """
        Return value value, with a typecheck.

        Raise ValueError if expected type is wrong.

        Raise KeyError on invalid parameter.
        """
        if expected_type:
            dtype = self.schema.properties[name]  # raises KeyError
            if not isinstance(dtype, expected_type):
                raise ValueError(
                    f'Request for {expected_type} parameter {name} '
                    f'but actual type is {dtype}'
                )

        return self.get_param(name)  # raises KeyError

    def get_param(self, name) -> Any:
        """
        Return value, of the parameter's type.

        Raise KeyError on invalid parameter.
        """
        return self.values[name]  # raises KeyError

    def get_param_string(self, name: str) -> str:
        return self.get_param_typed(name, ParamDTypeString)

    def get_param_integer(self, name: str) -> int:
        return self.get_param_typed(name, ParamDTypeInteger)

    def get_param_float(self, name: str) -> float:
        return self.get_param_typed(name, ParamDTypeFloat)

    def get_param_checkbox(self, name: str) -> bool:
        return self.get_param_typed(name, ParamDTypeBoolean)

    def get_param_radio_idx(self, name: str) -> int:
        return self.get_param_typed(name, ParamDTypeEnum)

    def get_param_menu_idx(self, name: str) -> int:
        return self.get_param_typed(name, ParamDTypeEnum)

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
        value = self.get_param_typed(name, ParamDTypeColumn)
        if value in table.columns:
            return value
        else:
            return ''

    def get_param_multicolumn(self, name,
                              table,
                              ignore_type=False
                              ) -> Tuple[List[str], List[str]]:
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
        if ignore_type:
            value = self.get_param(name)
        else:
            value = self.get_param_typed(name, ParamDTypeMulticolumn)

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

    @property
    def secret_metadata(self):
        metadata = {}
        for key, value in self.secrets.items():
            if value:
                metadata[key] = {'name': value['name']}
            else:
                metadata[key] = None
        return metadata

    def as_dict(self):
        """Present parameters as a dict (including secret metadata)."""
        return {
            **self.values,
            **self.secret_metadata,
        }

    def to_painful_dict(self, table):
        """
        Present parameters as a dict, with some inconsistent munging.

        A `column` parameter that refers to an invalid column will be renamed
        to the empty string.

        A `multicolumn` parameter will have its values `strip()`ed and have
        invalid columns removed.

        TODO present an interface with fewer surprises.
        """
        return {
            **self.schema.omit_missing_table_columns(self.values,
                                                     set(table.columns)),
            **self.secret_metadata,
        }
