from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Union
from .param_dtype import ParamDType


VisibleIf = Optional[Dict[str, Dict[str, Any]]]
EnumOptions = List[Union[str, Dict[str, str]]]


_lookup = {}  # dict of e.g., {'column': ParamSpecColumn}

# See also: param_dtype, which is the JSON storage format of params.

@dataclass(frozen=True)
class ParamSpec(ABC):
    """
    The specification of a module form field that will appear to the user.

    The module author specifies this in `parameters` in the module-spec file.

    This class does not represent values: just the module author's
    specification.
    
    ParamFields are immutable objects created as needed, in
    ModuleVersion.param_fields.

    A ParamSpec defines ParamDTypes, the "data type": how values are stored in
    JSON and selected by JavaScript components. The DType is the schema of
    `WfModule.params`. The ParamSpec is what the module author writes in the
    module specification, and it describes the JavaScript component.
    """
    id_name: str
    """The JSON Object key (or HTML field "name") of this field."""

    visible_if: VisibleIf = None
    """
    JSON object with logic deciding when the field should appear.

    Even when the field does not appear, it still has a value.

    The default is `None`, which means: "always visible."
    """

    # Some common other properties are documented here, since they're reused in
    # several subclasses:

    @property
    def type(self) -> str:
        """
        The "type" of component to render (passed to JavaScript).
        """

    @property
    @abstractmethod
    def dtype(self) -> Optional[ParamDType]:
        """
        ParamDTypes of values this field returns.

        Usually, a ParamSpec maps to a single ParamDType -- meaning a single
        JSON value. Exceptions like "statictext" (zero DTypes) return zero
        DTypes.
        """

    @classmethod
    def from_dict(cls, json_value: Dict[str, Any]) -> ParamSpec:
        """
        Parse a parameter from the module specification.

        At this point the schema has been validated; assume it is valid and any
        exception raised from this method is a bug.

        The logic is: look up the subclass by `json_value['type']`, and then
        call its `._from_kwargs()` method with the rest of the JSON dict.
        """
        json_value = json_value.copy()  # do not alter input
        json_type = json_value.pop('type')
        subcls = _lookup[json_type]
        return subcls._from_kwargs(**json_value)

    @classmethod
    def _from_kwargs(cls, **kwargs) -> ParamSpec:
        return cls(**kwargs)

    # "Register" all subclasses:
    # ParamSpec.Column => shorthand for ParamSpecColumn
    # ParamSpec.lookup['column'] == ParamSpec.Column
    def __init_subclass__(cls, **kwargs):
        """
        Register a subclass by class name (called implicitly).

        For instance, if you write `class ParamSpecFoo(ParamSpec):`, that
        means:

        * `_lookup['foo'] == ParamSpecFoo`
        * `ParamSpec.Foo == ParamSpecFoo`
        """
        super().__init_subclass__(**kwargs)

        name = cls.__name__
        assert name.startswith('ParamSpec')
        subname = name[len('ParamSpec'):]

        # ParamSpecFoo.type = 'foo' (JSON "type")
        cls.type = subname.lower()

        # _lookup['foo'] = ParamSpecFoo
        _lookup[cls.type] = cls

        # ParamSpec.Foo = ParamSpecFoo
        setattr(ParamSpec, subname, cls)

    def to_dict(self, *, dict_factory=dict) -> Dict[str, Any]:
        """
        Create a JSON-compatible Dict from this ParamSpec.

        This is the inverse of `ParamSpec.from_dict()`. That is, in all cases,
        `ParamSpec.from_dict(param_spec.to_dict()) == param_spec`.
        """
        return {
            'type': self.type,
            **asdict(self, dict_factory=dict_factory),
        }


@dataclass(frozen=True)
class _HasName:
    name: str = ''
    """
    The _label_ of this field. (Beware this misleading property name!)

    The default is `""`, meaning: no label.
    """

@dataclass(frozen=True)
class _HasPlaceholder:
    placeholder: str = ''
    """
    The text appearing in this field when there is no value.

    The default is '', which means: "component-specific default behavior."
    """

@dataclass(frozen=True)
class ParamSpecStatictext(_HasName, ParamSpec):
    """
    Text the user sees, with no underlying value.
    """
    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return None


@dataclass(frozen=True)
class ParamSpecSecret(_HasName, ParamSpec):
    """
    Secret such as an API key the user can set.

    Secrets are not stored in undo history (because we only want the owner to
    see them, not readers). So they don't have JSON values.
    """
    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return None


@dataclass(frozen=True)
class ParamSpecButton(_HasName, ParamSpec):
    """
    Button the user can click to submit data.

    This does not store a value. It does not send any different data over the
    wire. Some modules show buttons; others use the default "Execute" button.

    The "name" is what appears _inside_ the button, not outside it.
    """
    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return None


@dataclass(frozen=True)
class ParamSpecString(_HasPlaceholder, _HasName, ParamSpec):
    """
    Text the user can type.
    """
    default: str = ''
    multiline: bool = False
    """If True, newlines are permitted in data."""

    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return ParamDType.String(self.default)


@dataclass(frozen=True)
class ParamSpecNumberFormat(_HasPlaceholder, _HasName, ParamSpec):
    """
    Textual number-format string, like '${:0,.2f}'
    """
    default: str = '{:,}'

    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return ParamDType.String(self.default)


@dataclass(frozen=True)
class ParamSpecCustom(_HasName, ParamSpec):
    """
    Deprecated "custom" value -- behavior depends on id_name.

    Tread very carefully here. Don't add functionality: remove it. Nobody knows
    how this works.
    """
    default: Any = ''  # for version_select

    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return ParamDType.String(self.default)  # dunno why


@dataclass(frozen=True)
class ParamSpecColumn(_HasPlaceholder, _HasName, ParamSpec):
    """
    Column selector. Selects a str; default value `""` means "no column".
    """
    column_types: Optional[FrozenSet[str]] = None
    """
    Column-type restrictions for the underlying ParamDType.Column.
    """

    tab_parameter: Optional[str] = None
    """
    If set, the ParamSpecTab id_name that determines valid columns.

    For instance, a "join" module might want to list columns from a different
    tab.

    The default `None` means, "this tab."
    """

    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return ParamDType.Column(
            column_types=self.column_types,
            tab_parameter=self.tab_parameter
        )


@dataclass(frozen=True)
class ParamSpecMulticolumn(_HasPlaceholder, _HasName, ParamSpec):
    """
    Multicolumn selector. Selects FrozenSet of str.

    If `deprecated_string_storage` is set (DEPRECATED), value is str and the
    client and module must split it by `","`.
    """
    column_types: Optional[FrozenSet[str]] = None
    """
    Column-type restrictions for the underlying ParamDType.Multicolumn.
    """

    tab_parameter: Optional[str] = None
    """
    If set, the ParamSpecTab id_name that determines valid columns.

    For instance, a "join" module might want to list columns from a different
    tab.

    The default `None` means, "this tab."
    """

    deprecated_string_storage: bool = True
    """
    Passed to ParamDType.Multicolumn; if True, values are str not List.
    """

    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return ParamDType.Multicolumn(
            column_types=self.column_types,
            tab_parameter=self.tab_parameter,
            deprecated_string_storage=self.deprecated_string_storage
        )


@dataclass(frozen=True)
class ParamSpecMultichartseries(_HasPlaceholder, _HasName, ParamSpec):
    """
    Selects { column, color } pairs.
    """

    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return ParamDType.Multichartseries()


@dataclass(frozen=True)
class ParamSpecInteger(_HasPlaceholder, _HasName, ParamSpec):
    """
    Integer the user can type.
    """
    default: int = 0

    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return ParamDType.Integer(self.default)


@dataclass(frozen=True)
class ParamSpecFloat(_HasPlaceholder, _HasName, ParamSpec):
    """
    Decimal (stored as floating-point) the user can type.
    """
    default: float = 0.0

    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return ParamDType.Float(self.default)


@dataclass(frozen=True)
class ParamSpecCheckbox(_HasName, ParamSpec):
    """
    Boolean selected by checkbox.
    """
    default: Optional[bool] = None

    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return ParamDType.Boolean(self.default)


@dataclass(frozen=True)
class EnumOption:
    """
    An enum (menu/radio) option the user can select.
    """

    label: str
    """Text visible to the user."""

    value: Any
    """Value stored when the user selects this option."""

    @property
    def dtype_choices(self) -> FrozenSet[Any]:
        return frozenset([self.value])


class MenuOption(ABC):
    @property
    def dtype_choices(self) -> FrozenSet[Any]:
        return frozenset()

    @classmethod
    def _from_dict(cls, json_value) -> MenuOption:
        if json_value == 'separator':
            return cls.Separator()
        else:
            return cls.Value(**json_value)

    @classmethod
    def _from_deprecated_str(cls, index: int, value: str) -> MenuOption:
        if value:
            # Tricksy names here. Good thing this syntax is deprecated ;)
            return cls.Value(value=index, label=value)
        else:
            return cls.Separator()


class MenuOptionEnum(EnumOption, MenuOption):
    pass


@dataclass(frozen=True)  # for its equality operator
class MenuOptionSeparator(MenuOption):
    pass


@dataclass(frozen=True)
class ParamSpecMenu(_HasPlaceholder, _HasName, ParamSpec):
    """
    Enum value selected by drop-down menu.

    `options` may contain `"separator"` to improve styling.
    """
    default: Any = None  # None is invalid ... reconsider?
    options: List[MenuOption] = field(default_factory=list)  # mustn't be empty
    """
    Enumeration options. Some may be "separator" -- it appears to the client
    but is not part of the DType.
    """

    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return ParamDType.Enum(
            choices=frozenset.union(*[o.dtype_choices for o in self.options]),
            default=self.default
        )

    # override
    @classmethod
    def _from_kwargs(cls, *, options: List[Dict[str, str]] = None,
                     menu_items: str = None, default: Any = None, **kwargs):
        # Parses `options` ... or converts DEPRECATED `menu_items` parameter to
        # `options`.
        if menu_items:
            options = [MenuOption._from_deprecated_str(i, s)
                       for i, s in enumerate(menu_items.split('|'))]
        else:
            options = [MenuOption._from_dict(option) for option in options]
        if default is None:
            # TODO consider allowing None instead of forcing a default? Menus
            # could have a "placeholder"
            default = options[0].value
        return cls(options=options, **kwargs)


ParamSpecMenu.Option = MenuOption
ParamSpecMenu.Option.Value = MenuOptionEnum
ParamSpecMenu.Option.Separator = MenuOptionSeparator


@dataclass(frozen=True)
class ParamSpecRadio(_HasName, ParamSpec):
    """
    Enum values which are all visible at the same time.
    """
    default: Any = None  # None is an invalid default -- this is a radio
    options: List[EnumOption] = field(default_factory=list)
    """
    Enumeration options. All are visible at once.
    """

    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return ParamDType.Enum(
            choices=frozenset.union(*[o.dtype_choices for o in self.options]),
            default=self.default
        )

    # override
    @classmethod
    def _from_kwargs(cls, *, options: List[Dict[str, str]] = None,
                     radio_items: str = None, default: Any = None, **kwargs):
        # Parses `options` ... or converts DEPRECATED `radio_items` parameter
        # to `options`.
        if radio_items:
            options = [EnumOption(s, i)
                       for i, s in enumerate(radio_items.split('|'))]
        else:
            options = [EnumOption(**option) for option in options]
        if default is None:
            default = options[0].value
        return cls(options=options, default=default, **kwargs)


ParamSpecRadio.Option = EnumOption


@dataclass(frozen=True)
class ParamSpecTab(_HasPlaceholder, _HasName, ParamSpec):
    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return ParamDType.Tab()


@dataclass(frozen=True)
class ParamSpecMultitab(_HasPlaceholder, _HasName, ParamSpec):
    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        return ParamDType.Multitab()


@dataclass(frozen=True)
class ParamSpecList(_HasName, ParamSpec):
    child_parameters: List[ParamSpec] = field(default_factory=list)

    # override
    @classmethod
    def _from_kwargs(cls, *, child_parameters: List[Dict[str, Any]],
                     **kwargs) -> ParamSpecList:
        # Parse child parameters recursively
        child_parameters = [ParamSpec.from_dict(cp) for cp in child_parameters]
        return cls(child_parameters=child_parameters, **kwargs)

    # override
    @property
    def dtype(self) -> Optional[ParamDType]:
        child_dtypes = {cp.id_name: cp.dtype
                        for cp in self.child_parameters if cp.dtype}
        return ParamDType.List(ParamDType.Dict(child_dtypes))

    # override
    def to_dict(self, *, dict_factory=dict) -> Dict[str, Any]:
        """
        Create a JSON-compatible Dict from this ParamSpec.

        This is the inverse of `ParamSpec.from_dict()`. That is, in all cases,
        `ParamSpec.from_dict(param_spec.to_dict()) == param_spec`.
        """
        return {
            'type': self.type,
            **asdict(self, dict_factory=dict_factory),
            # asdict(self) won't encode the "type" of child_parameters, because
            # to_dict() isn't recursive. We don't actually _need_ it to be
            # recursive, since ParamSpecList isn't recursive. (A List can't
            # contain other Lists). So let's simply re-encode the
            # child_parameters, _with_ their type info.
            'child_parameters': [cp.to_dict() for cp in self.child_parameters]
        }
