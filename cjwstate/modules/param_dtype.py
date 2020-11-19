import re
import typing.re
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, FrozenSet, List, Optional

import pytz


@dataclass(frozen=True)
class ParamDType:
    """Data type -- that is, storage format -- for a parameter.

    Parameter values are always stored as JSON values. A parameter's DType is
    the "schema" for its values.

    This type applies to user-input data. Since the user may input _anything_
    (even invalid data, especially across multiple versions of a module), we
    provide `coerce()` and `validate()` to ensure type-safety.

    This is the abstract base class for a variety of DTypes which can represent
    recursive type structures.
    """

    def coerce(self, value: Any) -> Any:
        """Convert `value` to something valid.

        This cannot raise: it must return _something_ instead. In effect, types
        must have sensible "zero" values (e.g., a String's zero value is "").
        """
        raise NotImplementedError

    def validate(self, value: Any) -> Any:
        """Raise `ValueError` if `value` is not valid."""
        raise NotImplementedError

    def iter_dfs_dtype_values(self, value: Any):
        """Depth-first search to yield (dtype, value) pairs.

        By default, this yields `(self, value)`. "Container"-style dtypes
        should override this method to yield `(self, value)` and then yield
        each "child" `(dtype, value)`.

        Be sure to coerce() or validate() `value` before passing it here.
        """
        yield (self, value)

    @classmethod
    def _from_plain_data(cls, **kwargs):
        """Virtual method used by `ParamDType.parse()`

        `kwargs` are JSON keys/values.
        """
        return cls(**kwargs)

    @classmethod
    def parse(cls, json_value):
        """Deserialize this DType from JSON.

        Currently, we only JSON-serialize DTypes in module specifications that
        have explicit `param_schema`. That's rare.
        """
        json_value = json_value.copy()  # don't alter input
        json_type = json_value.pop("type")
        dtype = cls.JsonTypeToDType[json_type]
        return dtype._from_plain_data(**json_value)  # sans 'type'


@dataclass(frozen=True)
class ParamDTypeOption(ParamDType):
    """Decorate a dtype such that it may be None."""

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
    r"""Accept valid Unicode text.

    This is stricter than Python `str`. In particular, `"\ud8002"` is invalid
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
    """Accept integers."""

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
    """Accept floats or integers. Akin to JSON 'number' type."""

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
    """Accept `True` or `False`."""

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
class ParamDTypeCondition(ParamDType):
    """Valid JSON structure for column comparisons and combinations of them.

    Example valid value:

        {
            "operation": "text_contains",
            "column": "A",
            "value": "foo",
            "isCaseSensitive": True,
            "isRegex": False
        }

    Or:

        {
            "operation": "number_is_greater_than",
            "column": "A",
            "value": "4",
            "isCaseSensitive": True,
            "isRegex": True
        }

    There's nesting, too:

        {
            "operation": "and",
            "conditions": [ ... ]
        }

    List of valid operations (and arguments):

        * `and` (`conditions`)
        * `or` (`conditions`)
        * `cell_is_empty` ()
        * `cell_is_not_empty` ()
        * `cell_is_null` ()
        * `cell_is_not_null` ()
        * `text_contains` (`column`, `value`, `isCaseSensitive`, `isRegex`)
        * `text_does_not_contain` (`column`, `value`, `isCaseSensitive`, `isRegex`)
        * `text_is` (`column`, `value`, `isCaseSensitive`, `isRegex`)
        * `text_is_not` (`column`, `value`, `isCaseSensitive`, `isRegex`)
        * `timestamp_is` (`column`, `value`)
        * `timestamp_is_after` (`column`, `value`)
        * `timestamp_is_after_or_equals` (`column`, `value`)
        * `timestamp_is_before` (`column`, `value`)
        * `timestamp_is_before_or_equals` (`column`, `value`)
        * `timestamp_is_not` (`column`, `value`)
        * `number_is` (`column`, `value`)
        * `number_is_greater_than` (`column`, `value`)
        * `number_is_greater_than_or_equal` (`column`, `value`)
        * `number_is_less_than` (`column`, `value`)
        * `number_is_less_than_or_equal` (`column`, `value`)
        * `number_is_not` (`column`, `value`)

    For ease of UI implementation, some nonsense is allowed: "value" is a String
    so it may be invalid for number/timestamp operations; "column" may be empty;
    "isCaseSensitive" and "isRegex" apply to number/timestamp operations;
    "column" may have the wrong type; and nested "conditions" may be empty. Look
    to `renderprep` to see how those inconsistencies are removed.

    XXX right now, for UI reasons, conditions with a `column` must be nested
    exactly two levels depe, and deeper nesting is not allowed. For instance:

        {
            "operation": "and",
            "conditions": [
                {
                    "operation": "or",
                    "conditions": [
                        { ...condition... }
                    ]
                }
            ]
        }

    XXX This is to handle restrictions built into the user interface.

    More than any other value, `condition` values show one thing in the UI (and
    the module's `migrate_params()` and another thing entirely when passed to a
    module's `render()` method. See `renderprep` for details. The gist:
    `render()` has a `not` (`condition`) operation and all invalid operations
    are omitted. (It can receive `condition: None`.)
    """

    def coerce(self, value):
        try:
            self.validate(value)
            return value
        except ValueError as err:
            return {"operation": "and", "conditions": []}

    def __validate_common(self, value):
        if not isinstance(value, dict) or "operation" not in value:
            raise ValueError("%r must be a dict with an 'operation' key" % value)

    def __validate_common_level_0_or_1(self, value):
        keys = frozenset(value.keys())
        if (
            keys != {"operation", "conditions"}
            or value["operation"] not in {"and", "or"}
            or not isinstance(value["conditions"], list)
        ):
            raise ValueError(
                "Value must look like {'operation': 'or|and', 'conditions': [...]}; got %r"
                % value
            )

    def __validate_level2(self, value):
        self.__validate_common(value)
        keys = frozenset(value.keys())
        if keys != frozenset(
            ["operation", "column", "value", "isCaseSensitive", "isRegex"]
        ):
            raise ValueError(
                "Keys must be operation, column, value, isCaseSensitive, isRegex. Got: %r"
                % value
            )
        if value["operation"] not in {
            "",
            "and",
            "or",
            "cell_is_empty",
            "cell_is_not_empty",
            "cell_is_null",
            "cell_is_not_null",
            "text_contains",
            "text_does_not_contain",
            "text_is",
            "text_is_not",
            "timestamp_is",
            "timestamp_is_after",
            "timestamp_is_after_or_equals",
            "timestamp_is_before",
            "timestamp_is_before_or_equals",
            "timestamp_is_not",
            "number_is",
            "number_is_greater_than",
            "number_is_greater_than_or_equals",
            "number_is_less_than",
            "number_is_less_than_or_equals",
            "number_is_not",
        }:
            raise ValueError("There is no such operation: %r" % value["operation"])
        for key, wanted_type in (
            ("column", str),
            ("value", str),
            ("isCaseSensitive", bool),
            ("isRegex", bool),
        ):
            if not isinstance(value[key], wanted_type):
                raise ValueError(
                    "Wrong type of %s: expected %s, got %r"
                    % (key, wanted_type.__name__, value[key])
                )

    def __validate_level1(self, value):
        self.__validate_common(value)
        self.__validate_common_level_0_or_1(value)
        for condition in value["conditions"]:
            self.__validate_level2(condition)

    def validate(self, value):
        self.__validate_common(value)
        self.__validate_common_level_0_or_1(value)
        for condition in value["conditions"]:
            self.__validate_level1(condition)


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
    """Accept 'America/Montreal'-style strings or 'UTC'.

    The database is from https://www.iana.org/time-zones
    """

    default: str = "UTC"

    def __post_init__(self):
        if self.default not in pytz.all_timezones_set:
            raise ValueError(
                "Value %r is not an IANA timezone identifier" % self.default
            )

    def coerce(self, value):
        if value in pytz.all_timezones_set:
            return value
        else:
            return self.default

    def validate(self, value):
        if value not in pytz.all_timezones_set:
            raise ValueError("Value %r is not an IANA timezone identifier" % value)


class _ListMethods:
    """Methods that use `self.inner_dtype` and expect values to be list."""

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
    """A grouping of properties with a schema defined in the dtype.

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
    """A key-value store with arbitrary string keys and all-the-same-dtype values.

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
    """A 'tabs' parameter: a value is a list of tab slugs.

    This dtype behaves like a ParamDTypeList full of ParamDTypeTab values.
    We'll visit all child ParamDTypeTab values when walking a `value`.
    """

    default: List[str] = field(default_factory=list)

    def __post_init__(self):
        object.__setattr__(self, "inner_dtype", ParamDTypeTab())


@dataclass(frozen=True)
class ParamDTypeMultichartseries(_ListMethods, ParamDType):
    """A 'y_series' parameter: array of columns+colors.

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
    """String-encoded UUID pointing to an UploadedFile (and S3).

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
ParamDType.Boolean = ParamDTypeBoolean
ParamDType.Column = ParamDTypeColumn
ParamDType.Condition = ParamDTypeCondition
ParamDType.Dict = ParamDTypeDict
ParamDType.Enum = ParamDTypeEnum
ParamDType.File = ParamDTypeFile
ParamDType.Float = ParamDTypeFloat
ParamDType.Integer = ParamDTypeInteger
ParamDType.List = ParamDTypeList
ParamDType.Map = ParamDTypeMap
ParamDType.Multichartseries = ParamDTypeMultichartseries
ParamDType.Multicolumn = ParamDTypeMulticolumn
ParamDType.Multitab = ParamDTypeMultitab
ParamDType.Option = ParamDTypeOption
ParamDType.String = ParamDTypeString
ParamDType.Tab = ParamDTypeTab
ParamDType.Timezone = ParamDTypeTimezone

ParamDType.JsonTypeToDType = {
    "boolean": ParamDTypeBoolean,
    "column": ParamDTypeColumn,
    "condition": ParamDTypeCondition,
    "dict": ParamDTypeDict,
    "enum": ParamDTypeEnum,
    "file": ParamDTypeFile,
    "float": ParamDTypeFloat,
    "integer": ParamDTypeInteger,
    "list": ParamDTypeList,
    "map": ParamDTypeMap,
    "multichartseries": ParamDTypeMultichartseries,
    "multicolumn": ParamDTypeMulticolumn,
    "option": ParamDTypeOption,
    "string": ParamDTypeString,
    "tab": ParamDTypeTab,
    "tabs": ParamDTypeMultitab,
}
