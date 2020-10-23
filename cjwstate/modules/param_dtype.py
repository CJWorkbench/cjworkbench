import re
import typing.re
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, FrozenSet, List, Optional

import pytz


@dataclass(frozen=True)
class ParamDType:
    """
    Data type -- that is, storage format -- for a parameter.

    Parameter values are always stored as JSON values. A parameter's DType is
    the JSON "schema" for its values.

    This type applies to user-input data. Since the user may input _anything_
    (even invalid data, especially across multiple versions of a module), we
    provide `coerce()` and `validate()` to ensure type-safety.

    This is the abstract base class for a variety of DTypes which can represent recursive
    type structures.
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

    def iter_dfs_dtypes(self):
        """
        Depth-first search to yield dtypes.

        By default, this yields `self`. "Container"-style dtypes should
        override this method to yield `self` and then yield each "child"
        `dtype`.
        """
        yield self

    def iter_dfs_dtype_values(self, value: Any):
        """
        Depth-first search to yield (dtype, value) pairs.

        By default, this yields `(self, value)`. "Container"-style dtypes
        should override this method to yield `(self, value)` and then yield
        each "child" `(dtype, value)`.

        Be sure to coerce() or validate() `value` before passing it here.
        """
        yield (self, value)

    def find_leaf_values_with_dtype(self, dtype: type, value: Any) -> FrozenSet[Any]:
        """
        Recurse through `value`, finding sub-values of type `dtype`.

        Be sure to coerce() or validate() `value` before passing it here.

        "Container"-style dtypes should override this method to walk their
        children.

        Example:

        >>> schema = ParamDTypeList(inner_dtype=ParamDTypeTab())
        >>> tab_slugs = schema.find_leaf_values_with_dtype(
        ...     ParamDTypeTab,
        ...     ['tab-123', 'tab-234']
        ... })
        {'tab-123', 'tab-234'}
        """
        return frozenset(
            v for dt, v in self.iter_dfs_dtype_values(value) if isinstance(dt, dtype)
        )

    @classmethod
    def _from_plain_data(cls, **kwargs):
        """
        Virtual method used by `ParamDType.parse()`

        `kwargs` are JSON keys/values.
        """
        return cls(**kwargs)

    @classmethod
    def parse(cls, json_value):
        """
        Deserialize this DType from JSON.

        Currently, we only JSON-serialize DTypes in module specifications that
        have explicit `param_schema`. That's rare.
        """
        json_value = json_value.copy()  # don't alter input
        json_type = json_value.pop("type")
        dtype = cls.JsonTypeToDType[json_type]
        return dtype._from_plain_data(**json_value)  # sans 'type'


@dataclass(frozen=True)
class ParamDTypeOption(ParamDType):
    """
    Decorate a dtype such that it may be None.
    """

    inner_dtype: ParamDType

    # override
    def coerce(self, value):
        if value is None:
            return None
        else:
            return self.inner_dtype.coerce(value)

    # override
    def validate(self, value):
        if value is not None:
            self.inner_dtype.validate(value)

    # override
    def iter_dfs_dtypes(self):
        yield from super().iter_dfs_dtypes()
        yield from self.inner_dtype.iter_dfs_dtypes()

    # override
    def iter_dfs_dtype_values(self, value: Any):
        yield from super().iter_dfs_dtype_values(value)
        if value is not None:
            yield from self.inner_dtype.iter_dfs_dtype_values(value)

    # override
    @classmethod
    def _from_plain_data(cls, *, inner_dtype):
        inner_dtype = cls.parse(inner_dtype=inner_dtype)
        return cls(inner_dtype=inner_dtype)


@dataclass(frozen=True)
class ParamDTypeString(ParamDType):
    """
    Valid Unicode text.

    This is stricter than Python `str`. In particular, `"\\ud8002"` is invalid
    (because a lone surrogate isn't valid Unicode text) and `"\x00"` is invalid
    (because Postgres doesn't allow null bytes).
    """

    default: str = ""

    InvalidCodePoints: ClassVar[typing.re.Pattern] = re.compile("[\u0000\ud800-\udfff]")

    def coerce(self, value):
        if value is None:
            return self.default
        elif not isinstance(value, str):
            try:
                value = str(value)
            except Exception:  # __str__() has 1,000 ways to fail....
                return self.default

        # `value` may still be invalid Unicode. In particular, if we received a
        # value from json.parse() it can have invalid surrogates, because
        # invalid surrogates are valid in JSON Strings (!).
        return ParamDTypeString.InvalidCodePoints.sub("\ufffd", value)

    def validate(self, value):
        if not isinstance(value, str):
            raise ValueError("Value %r is not a string" % value)
        if ParamDTypeString.InvalidCodePoints.search(value) is not None:
            if "\x00" in value:
                raise ValueError(
                    "Value %r is not valid text: zero byte not allowed" % value
                )
            else:
                raise ValueError(
                    "Value %r is not valid Unicode: surrogates not allowed" % value
                )


@dataclass(frozen=True)
class ParamDTypeInteger(ParamDType):
    default: int = 0

    def coerce(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return self.default

    def validate(self, value):
        if not isinstance(value, int):
            raise ValueError("Value %r is not an integer" % value)


@dataclass(frozen=True)
class ParamDTypeFloat(ParamDType):
    """
    Accepts floats or integers. Akin to JSON 'number' type.
    """

    default: float = 0.0

    def coerce(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return self.default

    def validate(self, value):
        if not (isinstance(value, float) or isinstance(value, int)):
            raise ValueError("Value %r is not a float" % value)

    @classmethod
    def _from_plain_data(cls, default=0.0):
        # JSON won't differentiate between int and float
        default = float(default)
        return cls(default=default)


@dataclass(frozen=True)
class ParamDTypeBoolean(ParamDType):
    default: bool = False

    def coerce(self, value):
        if value is None:
            return self.default
        elif isinstance(value, str):
            return value.lower() == "true"
        else:
            try:
                return bool(value)
            except (TypeError, ValueError):
                return self.default

    def validate(self, value):
        if not isinstance(value, bool):
            raise ValueError("Value %r is not a boolean" % value)


@dataclass(frozen=True)
class ParamDTypeColumn(ParamDTypeString):
    column_types: Optional[FrozenSet[str]] = None
    tab_parameter: Optional[str] = None

    @classmethod
    def _from_plain_data(cls, *, column_types=None, **kwargs):
        if column_types:
            # column_types comes from JSON as a list. We need a set.
            kwargs["column_types"] = frozenset(column_types)
        return cls(**kwargs)


@dataclass(frozen=True)
class ParamDTypeMulticolumn(ParamDType):
    column_types: Optional[FrozenSet[str]] = None
    tab_parameter: Optional[str] = None

    def coerce(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            value = list(value)
        return [str(v) for v in value]

    def validate(self, value):
        if not isinstance(value, list):
            raise ValueError("Value %r is not a list" % value)
        for i, v in enumerate(value):
            if not isinstance(v, str):
                raise ValueError("Item %d of value %r is not a string" % (i, value))

    @classmethod
    def _from_plain_data(cls, *, column_types=None, **kwargs):
        if column_types:
            # column_types comes from JSON as a list. We need a set.
            kwargs["column_types"] = frozenset(column_types)
        return cls(**kwargs)


@dataclass(frozen=True)
class ParamDTypeEnum(ParamDType):
    choices: FrozenSet[Any]
    default: Any

    def __post_init__(self):
        if self.default not in self.choices:
            raise ValueError(
                "Default %(default)r is not in choices %(choices)r"
                % {"default": self.default, "choices": self.choices}
            )

    def coerce(self, value):
        if value in self.choices:
            return value
        else:
            return self.default

    def validate(self, value):
        if value not in self.choices:
            raise ValueError(
                "Value %(value)r is not in choices %(choices)r"
                % {"value": value, "choices": self.choices}
            )

    @classmethod
    def _from_plain_data(cls, *, choices: List[str], **kwargs):
        return cls(choices=frozenset(choices), **kwargs)


@dataclass(frozen=True)
class ParamDTypeTimezone(ParamDType):
    """
    Accepts 'America/Montreal'-style strings or 'UTC'.

    The database is from https://www.iana.org/time-zones
    """

    default: str = "UTC"

    def coerce(self, value):
        if value in pytz.all_timezones_set:
            return value
        else:
            return self.default

    def validate(self, value):
        if value not in pytz.all_timezones_set:
            raise ValueError("Value %r is not an IANA timezone identifier" % value)


class _ListMethods:
    """
    Methods that use `self.inner_dtype` and expect values to be list.
    """

    def coerce(self, value):
        if value is None:
            return self.default

        if not hasattr(value, "__iter__"):
            value = [value]

        return [self.inner_dtype.coerce(v) for v in value]

    def validate(self, value):
        if not isinstance(value, list):
            raise ValueError("Value %r is not a list" % value)

        for v in value:
            self.inner_dtype.validate(v)

    # override
    def iter_dfs_dtypes(self):
        yield from super().iter_dfs_dtypes()
        yield self.inner_dtype

    # override
    def iter_dfs_dtype_values(self, value):
        yield from super().iter_dfs_dtype_values(value)
        for v in value:
            yield from self.inner_dtype.iter_dfs_dtype_values(v)


@dataclass(frozen=True)
class ParamDTypeList(_ListMethods, ParamDType):
    inner_dtype: ParamDType
    default: List[Any] = field(default_factory=list)

    @classmethod
    def _from_plain_data(cls, *, inner_dtype, **kwargs):
        inner_dtype = cls.parse(inner_dtype)
        return cls(inner_dtype=inner_dtype, **kwargs)


@dataclass(frozen=True)
class ParamDTypeDict(ParamDType):
    """
    A grouping of properties with a schema defined in the dtype.

    This is different from ParamDTypeMap, which allows arbitrary keys and
    forces all values to have the same dtype.
    """

    properties: Dict[str, ParamDType]
    default: Optional[Any] = None  # if None, auto-calculate during init

    def __post_init__(self):
        if self.default is None:
            default = dict(
                (name, dtype.coerce(None)) for name, dtype in self.properties.items()
            )
            object.__setattr__(self, "default", default)

    def coerce(self, value):
        if not isinstance(value, dict):
            return self.default

        return dict(
            (name, dtype.coerce(value.get(name)))
            for name, dtype in self.properties.items()
        )

    def validate(self, value):
        if not isinstance(value, dict):
            raise ValueError("Value %r is not a dict" % value)

        expect_keys = set(self.properties.keys())
        actual_keys = set(value.keys())
        if expect_keys != actual_keys:
            raise ValueError(
                "Value %(value)r has wrong names: expected names %(names)r"
                % {"value": value, "names": expect_keys}
            )

        for name, dtype in self.properties.items():
            dtype.validate(value[name])

    # override
    def iter_dfs_dtypes(self):
        yield from super().iter_dfs_dtypes()
        yield from self.properties.values()

    # override
    def iter_dfs_dtype_values(self, value):
        yield from super().iter_dfs_dtype_values(value)
        for name, dtype in self.properties.items():
            yield from dtype.iter_dfs_dtype_values(value[name])

    @classmethod
    def _from_plain_data(cls, *, properties, **kwargs):
        properties = dict((k, cls.parse(v)) for k, v in properties.items())
        return cls(properties=properties, **kwargs)


@dataclass(frozen=True)
class ParamDTypeMap(ParamDType):
    """
    A key-value store with arbitrary string keys and all-the-same-dtype values.

    This is different from ParamDTypeDict, which has dtype-defined properties,
    each with its own dtype.
    """

    value_dtype: ParamDType
    default: Dict[str, Any] = field(default_factory=dict)

    def coerce(self, value):
        if not isinstance(value, dict):
            return self.default

        return dict((k, self.value_dtype.coerce(v)) for k, v in value.items())

    def validate(self, value):
        if not isinstance(value, dict):
            raise ValueError("Value %r is not a dict" % value)

        for _, v in value.items():
            self.value_dtype.validate(v)

    # override
    def iter_dfs_dtypes(self):
        yield from super().iter_dfs_dtypes()
        yield self.value_dtype

    # override
    def iter_dfs_dtype_values(self, value):
        yield from super().iter_dfs_dtype_values(value)
        for v in value.values():
            yield from self.value_dtype.iter_dfs_dtype_values(v)

    @classmethod
    def _from_plain_data(cls, *, value_dtype, **kwargs):
        value_dtype = cls.parse(value_dtype)
        return cls(value_dtype=value_dtype, **kwargs)


@dataclass(frozen=True)
class ParamDTypeTab(ParamDTypeString):
    pass


@dataclass(frozen=True)
class ParamDTypeMultitab(_ListMethods, ParamDType):
    """
    A 'tabs' parameter: a value is a list of tab slugs.

    This dtype behaves like a ParamDTypeList full of ParamDTypeTab values.
    We'll visit all child ParamDTypeTab values when walking a `value`.
    """

    default: List[str] = field(default_factory=list)

    def __post_init__(self):
        object.__setattr__(self, "inner_dtype", ParamDTypeTab())


@dataclass(frozen=True)
class ParamDTypeMultichartseries(_ListMethods, ParamDType):
    """
    A 'y_series' parameter: array of columns+colors.

    This is like a List[Dict], except when omitting table columns we omit the
    entire Dict if its Column is missing.
    """

    default: List[Dict[str, str]] = field(default_factory=list)

    def __post_init__(self):
        object.__setattr__(
            self,
            "inner_dtype",
            ParamDTypeDict(
                {
                    "column": ParamDTypeColumn(column_types=frozenset({"number"})),
                    "color": ParamDTypeString(),  # TODO enforce '#abc123' pattern
                }
            ),
        )


@dataclass(frozen=True)
class ParamDTypeFile(ParamDType):
    """
    String-encoded UUID pointing to an UploadedFile (and S3).

    The default, value, `null`, means "No file".
    """

    UUIDRegex: ClassVar[typing.re.Pattern] = re.compile(
        r"\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z"
    )

    def coerce(self, value):
        try:
            self.validate(value)
        except ValueError:
            # If it's not a UUID, we _certainly_ can't repair it
            return None
        return value

    def validate(self, value):
        if value is None:
            return  # None is the default, and it's valid
        if not isinstance(value, str):
            raise ValueError("Value %r is not a string" % value)
        if not self.UUIDRegex.match(value):
            raise ValueError("Value %r is not a UUID string representation" % value)


# Aliases to help with import. e.g.:
# from cjwstate.modules.param_dtype import ParamDType
# dtype = ParamDType.String()
ParamDType.String = ParamDTypeString
ParamDType.Integer = ParamDTypeInteger
ParamDType.Float = ParamDTypeFloat
ParamDType.Boolean = ParamDTypeBoolean
ParamDType.Enum = ParamDTypeEnum
ParamDType.Timezone = ParamDTypeTimezone
ParamDType.Option = ParamDTypeOption
ParamDType.List = ParamDTypeList
ParamDType.Dict = ParamDTypeDict
ParamDType.Map = ParamDTypeMap
ParamDType.Column = ParamDTypeColumn
ParamDType.Multicolumn = ParamDTypeMulticolumn
ParamDType.Tab = ParamDTypeTab
ParamDType.Multitab = ParamDTypeMultitab
ParamDType.Multichartseries = ParamDTypeMultichartseries
ParamDType.File = ParamDTypeFile

ParamDType.JsonTypeToDType = {
    "string": ParamDTypeString,
    "integer": ParamDTypeInteger,
    "float": ParamDTypeFloat,
    "boolean": ParamDTypeBoolean,
    "enum": ParamDTypeEnum,
    "option": ParamDTypeOption,
    "list": ParamDTypeList,
    "dict": ParamDTypeDict,
    "map": ParamDTypeMap,
    "tab": ParamDTypeTab,
    "tabs": ParamDTypeMultitab,
    "column": ParamDTypeColumn,
    "multicolumn": ParamDTypeMulticolumn,
    "multichartseries": ParamDTypeMultichartseries,
    "file": ParamDTypeFile,
}
