from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Union
from .param_dtype import ParamDType

# See also: param_dtype, which is the JSON storage format of params.

@dataclass(frozen=True)
class ParamSpec:
    """
    The specification of a module form field that will appear to the user.

    The module author specifies this in `parameters` in the module-spec file.

    This class does not represent values: just the module author's
    specification.
    
    ParamFields are immutable objects created as needed, in
    ModuleVersion.param_fields.

    A ParamSpec defines exactly one ParamDType, the "data type", which defines
    how values are stored in JSON and selected by JavaScript components. The
    DType is the schema of `WfModule.params`. The ParamSpec is what the module
    author writes in the module specification, and it describes the component
    we display in JavaScript.
    """

    class ParamType(Enum):
        """Parameter type specified by module author and displayed to the user"""
        STATICTEXT = 'statictext'
        STRING = 'string'
        NUMBERFORMAT = 'numberformat'
        INTEGER = 'integer'
        FLOAT = 'float'
        CHECKBOX = 'checkbox'
        MENU = 'menu'               # menu like HTML <select>
        BUTTON = 'button'
        COLUMN = 'column'
        RADIO = 'radio'
        MULTICOLUMN = 'multicolumn'
        MULTICHARTSERIES = 'multichartseries'
        TAB = 'tab'
        MULTITAB = 'multitab'
        SECRET = 'secret'
        CUSTOM = 'custom'           # rendered in front end
        LIST = 'list'

        def __str__(self):
            return self.value

    id_name: str
    param_type: ParamSpec.ParamType
    name: str = ''
    items: str = ''  # deprecated menu/radio items
    options: Optional[List[Union[str, Dict[str, str]]]] = None  # menu/radio
    multiline: bool = False  # for strings
    placeholder: str = ''
    tab_parameter: str = ''
    default: Any = None
    visible_if: Optional[Dict[str, Dict[str, Any]]] = None
    column_types: Optional[FrozenSet[str]] = None
    child_parameters: Optional[List[Dict[str, Any]]] = None # only for List type

    @classmethod
    def from_dict(self, d: Dict[str, Any]) -> 'ParamField':
        column_types = d.get('column_types')
        if isinstance(column_types, list):
            column_types = frozenset(column_types)

        return ParamSpec(
            id_name=d['id_name'],
            param_type=ParamSpec.ParamType(d['type']),
            name=d.get('name', ''),
            items=d.get('menu_items', d.get('radio_items', '')),
            options=d.get('options'),
            multiline=d.get('multiline', False),
            placeholder=d.get('placeholder', ''),
            tab_parameter=d.get('tab_parameter', ''),
            visible_if=d.get('visible_if'),
            column_types=column_types,
            child_parameters=d.get('child_parameters', []),
            default=d.get('default')
        )

    @property
    def dtype(self) -> Optional[ParamDType]:
        T = ParamSpec.ParamType

        if (
            self.param_type == T.STATICTEXT
            or self.param_type == T.SECRET
            or self.param_type == T.BUTTON
        ):
            # These don't show up in wf_module.params
            return None
        elif (
            self.param_type == T.STRING
            or self.param_type == T.NUMBERFORMAT
            or self.param_type == T.CUSTOM
        ):
            kwargs = {}
            if self.default is not None:
                # TODO nix cast here: validate in module_version
                kwargs['default'] = str(self.default)
            return ParamDType.String(**kwargs)
        elif self.param_type == T.COLUMN:
            return ParamDType.Column(
                column_types=self.column_types,
                tab_parameter=self.tab_parameter or None
            )
        elif self.param_type == T.MULTICOLUMN:
            return ParamDType.Multicolumn(
                column_types=self.column_types,
                tab_parameter=self.tab_parameter or None
            )
        elif self.param_type == T.MULTICHARTSERIES:
            return ParamDType.Multichartseries()
        elif self.param_type == T.TAB:
            return ParamDType.Tab()
        elif self.param_type == T.MULTITAB:
            return ParamDType.Multitab()
        elif self.param_type == T.INTEGER:
            kwargs = {}
            if self.default is not None:
                # TODO nix cast here: validate in module_version
                kwargs['default'] = int(self.default)
            return ParamDType.Integer(**kwargs)
        elif self.param_type == T.FLOAT:
            kwargs = {}
            if self.default is not None:
                # TODO nix cast here: validate in module_version
                kwargs['default'] = float(self.default)
            return ParamDType.Float(**kwargs)
        elif self.param_type == T.CHECKBOX:
            kwargs = {}
            if self.default is not None:
                # TODO nix cast here: validate in module_version
                kwargs['default'] = str(self.default).lower() == 'true'
            return ParamDType.Boolean(**kwargs)
        elif (
            self.param_type == T.MENU
            or self.param_type == T.RADIO
        ):
            if self.items:
                # deprecated menu/radio
                # Menu values are integers. Ick, eh?
                choices = frozenset(range(len(self.items.split('|'))))
                default = int(self.default or 0) or 0
            else:
                # normal menu/radio
                values = list(o['value']
                              for o in self.options
                              if isinstance(o, dict))  # skip separators
                choices = frozenset(values)
                # This won't support value=None
                default = values[0] if self.default is None else self.default

            return ParamDType.Enum(choices, default)
        elif (self.param_type == T.LIST):

            # This must match logic in ModuleVersion.param_schema so that child parameters
            # are stored the same way as the top level params
            param_dtypes = dict((p['id_name'], ParamSpec.from_dict(p).dtype) for p in self.child_parameters)
            param_dtypes = {k: v for k, v in param_dtypes.items() if v} # remove None dtypes, e.g. button

            # A list of repeating groups of parameters
            return ParamDType.List(ParamDType.Dict(param_dtypes))

        else:
            raise ValueError('Unknown param_type %r' % self.param_type)
