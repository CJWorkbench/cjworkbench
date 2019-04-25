from typing import Any, Dict
from .param_dtype import ParamDTypeDict


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

    def get_param(self, name) -> Any:
        """
        Return value, of the parameter's type.

        Raise KeyError on invalid parameter.
        """
        return self.values[name]  # raises KeyError

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
            **self.secrets,
        }
