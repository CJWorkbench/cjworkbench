from enum import Enum
from typing import Any, Dict, Optional, Set


class ParamDType:
    """
    User-visible data type of a parameter.

    This type applies to user-input data. Since the user may input _anything_
    (even invalid data, especially across multiple versions of a module), we
    provide `coerce()` and `validate()` to ensure type-safety.

    Parameter types are _user-visible_: we need to explain each data type's
    semantics to our users. It's crucial we don't add complexity we don't need.
    """

    def coerce(self, value: Any) -> Any:
        """
        Convert `value` to something valid.

        This cannot raise: it must return _something_ instead. In effect, types
        must have sensible "zero" values (e.g., a String's zero value is "").
        """
        raise NotImplementedError

    def validate(self, value: Any) -> Any:
        """
        Raise `ValueError` if `value` is not valid.
        """
        raise NotImplementedError

    def omit_missing_table_columns(self, value: Any, columns: Set[str]) -> Any:
        """
        Recursively nix `value`'s column references that aren't in `columns`.

        For example: remove any `ParamDTypeColumn` nested within a
        `ParamDTypeList` if that column value isn't in `columns`.

        Assumes `value` is valid.
        """
        # default implementation: no-op. Most dtypes aren't nested or columnar
        return value

    @classmethod
    def _from_plain_data(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    def parse(cls, json_value):
        json_type = json_value['type']
        dtype = cls.JsonTypeToDType[json_type]

        kwargs = {**json_value}
        del kwargs['type']

        return dtype._from_plain_data(**kwargs)


class ParamDTypeString(ParamDType):
    def __init__(self, default=''):
        super().__init__()
        self.default = default

    def __repr__(self):
        return 'ParamDTypeString()'

    def coerce(self, value):
        if value is None:
            return self.default
        else:
            return str(value)

    def validate(self, value):
        if not isinstance(value, str):
            raise ValueError('Value %r is not a string' % value)


class ParamDTypeInteger(ParamDType):
    def __init__(self, default=0):
        super().__init__()
        self.default = default

    def __repr__(self):
        return 'ParamDTypeInteger()'

    def coerce(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return self.default

    def validate(self, value):
        if not isinstance(value, int):
            raise ValueError('Value %r is not an integer' % value)


class ParamDTypeFloat(ParamDType):
    def __init__(self, default=0.0):
        super().__init__()
        self.default = default

    def __repr__(self):
        return 'ParamDTypeFloat()'

    def coerce(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return self.default

    def validate(self, value):
        if not isinstance(value, float):
            raise ValueError('Value %r is not a float' % value)

    @classmethod
    def _from_plain_data(cls, default=0.0):
        # JSON won't differentiate between int and float
        default = float(default)
        return cls(default=default)


class ParamDTypeBoolean(ParamDType):
    def __init__(self, default=False):
        super().__init__()
        self.default = default

    def __repr__(self):
        return 'ParamDTypeBoolean()'

    def coerce(self, value):
        if value is None:
            return self.default
        elif isinstance(value, str):
            return value.lower() == 'true'
        else:
            try:
                return bool(value)
            except (TypeError, ValueError):
                return self.default

    def validate(self, value):
        if not isinstance(value, bool):
            raise ValueError('Value %r is not a boolean' % value)


class ParamDTypeColumn(ParamDTypeString):
    def __repr__(self):
        return 'ParamDTypeColumn()'

    def omit_missing_table_columns(self, value, columns):
        if value not in columns:
            return ''
        else:
            return value


class ParamDTypeMulticolumn(ParamDTypeString):
    def __repr__(self):
        return 'ParamDTypeMulticolumn()'

    def omit_missing_table_columns(self, value, columns):
        valid = [c for c in value.split(',') if c in columns]
        return ','.join(valid)


class ParamDTypeEnum(ParamDType):
    def __init__(self, choices: Set[Any], default: Any):
        super().__init__()
        if default not in choices:
            raise ValueError(
                'Default %(default)r is not in choices %(choices)r'
                % {'default': default, 'choices': choices}
            )
        self.choices = choices
        self.default = default

    def __repr__(self):
        return 'ParamDTypeEnum' + repr((self.choices, self.default))

    def coerce(self, value):
        if value in self.choices:
            return value
        else:
            return self.default

    def validate(self, value):
        if value not in self.choices:
            raise ValueError(
                'Value %(value)r is not in choices %(choices)r'
                % {'value': value, 'choices': self.choices}
            )


class ParamDTypeList(ParamDType):
    def __init__(self, inner_dtype: ParamDType, default=[]):
        super().__init__()
        self.inner_dtype = inner_dtype
        self.default = default

    def __repr__(self):
        return 'ParamDTypeList' + repr((self.inner_dtype,))

    def coerce(self, value):
        if value is None:
            return self.default

        if not hasattr(value, '__iter__'):
            value = [value]

        return [self.inner_dtype.coerce(v) for v in value]

    def validate(self, value):
        if not isinstance(value, list):
            raise ValueError('Value %r is not a list' % value)

        for v in value:
            self.inner_dtype.validate(v)

    def omit_missing_table_columns(self, value, columns):
        return [self.inner_dtype.omit_missing_table_columns(v, columns)
                for v in value]

    @classmethod
    def _from_plain_data(cls, *, inner_dtype, **kwargs):
        inner_dtype = cls.parse(inner_dtype)
        return cls(inner_dtype=inner_dtype, **kwargs)


class ParamDTypeDict(ParamDType):
    def __init__(self, properties: Dict[str, ParamDType], default=None):
        super().__init__()
        self.properties = properties
        if default is None:
            default = dict((name, dtype.coerce(None))
                           for name, dtype in self.properties.items())
        self.default = default

    def __repr__(self):
        return 'ParamDTypeDict' + repr((self.properties,))

    def coerce(self, value):
        if not isinstance(value, dict):
            return self.default

        return dict((name, dtype.coerce(value.get(name)))
                    for name, dtype in self.properties.items())

    def validate(self, value):
        if not isinstance(value, dict):
            raise ValueError('Value %r is not a dict' % value)

        expect_keys = set(self.properties.keys())
        actual_keys = set(value.keys())
        if expect_keys != actual_keys:
            raise ValueError(
                'Value %(value)r has wrong names: expected names %(names)r'
                % {'value': value, 'names': expect_keys}
            )

        for name, dtype in self.properties.items():
            dtype.validate(value[name])

    def omit_missing_table_columns(self, value, columns):
        return dict(
            (k, self.properties[k].omit_missing_table_columns(v, columns))
            for k, v in value.items()
        )

    @classmethod
    def _from_plain_data(cls, *, properties, **kwargs):
        properties = dict((k, cls.parse(v)) for k, v in properties.items())
        return cls(properties=properties, **kwargs)


# Aliases to help with import. e.g.:
# from server.models.param_field import ParamDType
# dtype = ParamDType.String()
ParamDType.String = ParamDTypeString
ParamDType.Integer = ParamDTypeInteger
ParamDType.Float = ParamDTypeFloat
ParamDType.Boolean = ParamDTypeBoolean
ParamDType.Enum = ParamDTypeEnum
ParamDType.List = ParamDTypeList
ParamDType.Dict = ParamDTypeDict
ParamDType.Column = ParamDTypeColumn
ParamDType.Multicolumn = ParamDTypeMulticolumn

ParamDType.JsonTypeToDType = {
    'string': ParamDTypeString,
    'integer': ParamDTypeInteger,
    'float': ParamDTypeFloat,
    'boolean': ParamDTypeBoolean,
    'enum': ParamDTypeEnum,
    'list': ParamDTypeList,
    'dict': ParamDTypeDict,
    'column': ParamDTypeColumn,
    'multicolumn': ParamDTypeMulticolumn,
}


class ParamField:
    """
    A form field for entering a param.

    This is what the user sees.
    """
    class FType(Enum):
        """Type of form field to display to the user"""
        STATICTEXT = 'statictext'
        STRING = 'string'
        INTEGER = 'integer'
        FLOAT = 'float'
        CHECKBOX = 'checkbox'
        MENU = 'menu'               # menu like HTML <select>
        BUTTON = 'button'
        COLUMN = 'column'
        RADIO = 'radio'
        MULTICOLUMN = 'multicolumn'
        SECRET = 'secret'
        CUSTOM = 'custom'           # rendered in front end

        def __str__(self):
            return self.value

    def __init__(self, *, id_name: str, ftype: 'ParamField.FType',
                 name: str = '', items: str = '', multiline: bool = False,
                 placeholder: str = '',
                 visible_if: Optional[Dict[str, Dict[str, Any]]] = None,
                 default: Any = None):
        self.id_name = id_name
        self.ftype = ftype
        self.name = name
        self.items = items
        self.multiline = multiline
        self.placeholder = placeholder
        self.visible_if = visible_if
        self.default = default

    def __repr__(self):
        return ''.join((
            'ParamField(',
            'id_name=', repr(self.id_name),
            'ftype=', repr(self.ftype),
            'default=', repr(self.default),
        ))

    @classmethod
    def from_dict(self, d: Dict[str, Any]) -> 'ParamField':
        return ParamField(
            id_name=d['id_name'],
            ftype=ParamField.FType(d['type']),
            name=d.get('name', ''),
            items=d.get('menu_items', d.get('radio_items', '')),
            multiline=d.get('multiline', False),
            placeholder=d.get('placeholder', ''),
            visible_if=d.get('visible_if'),
            default=d.get('default')
        )

    @property
    def dtype(self) -> Optional[ParamDType]:
        T = ParamField.FType

        if (
            self.ftype == T.STATICTEXT
            or self.ftype == T.SECRET
            or self.ftype == T.BUTTON
        ):
            # These don't show up in wf_module.params
            return None
        elif (
            self.ftype == T.STRING
            or self.ftype == T.CUSTOM
        ):
            kwargs = {}
            if self.default is not None:
                # TODO nix cast here: validate in module_version
                kwargs['default'] = str(self.default)
            return ParamDTypeString(**kwargs)
        elif self.ftype == T.COLUMN:
            return ParamDTypeColumn()
        elif self.ftype == T.MULTICOLUMN:
            return ParamDTypeMulticolumn()
        elif self.ftype == T.INTEGER:
            kwargs = {}
            if self.default is not None:
                # TODO nix cast here: validate in module_version
                kwargs['default'] = int(self.default)
            return ParamDTypeInteger(**kwargs)
        elif self.ftype == T.FLOAT:
            kwargs = {}
            if self.default is not None:
                # TODO nix cast here: validate in module_version
                kwargs['default'] = float(self.default)
            return ParamDTypeFloat(**kwargs)
        elif self.ftype == T.CHECKBOX:
            kwargs = {}
            if self.default is not None:
                # TODO nix cast here: validate in module_version
                kwargs['default'] = str(self.default).lower() == 'true'
            return ParamDTypeBoolean(**kwargs)
        elif (
            self.ftype == T.MENU
            or self.ftype == T.RADIO
        ):
            kwargs = {}
            if self.default is not None:
                kwargs['default'] = int(self.default)
            else:
                kwargs['default'] = 0

            return ParamDTypeEnum(
                # Menu values are integers. Ick, eh?
                choices=set(range(len(self.items.split('|')))),
                **kwargs
            )
        else:
            raise ValueError('Unknown ftype %r' % self.ftype)
