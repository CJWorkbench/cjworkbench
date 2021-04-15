from functools import partial, singledispatch
import pathlib
from typing import Any, Dict, List, Optional, Union
from cjwkernel.types import ColumnType, TableMetadata
from cjwstate.modules.param_dtype import ParamDType
from renderer.execute.renderprep import PromptErrorAggregator
from renderer.execute.types import PromptingError


# singledispatch primer: `clean_value(dtype, value, context)` will choose its
# logic based on the _type_ of `dtype`. (Handily, it'll prefer a specific class
# to its parent class.)
#
# The recursive logic in fetchprep.py was copy/pasted from renderprep.py.
#
# TODO abstract this pattern. The recursion parts seem like they should be
# written in just one place.
@singledispatch
def clean_value(dtype: ParamDType, value: Any, input_metadata: TableMetadata) -> Any:
    """
    Ensure `value` fits the Params dict `render()` expects.

    The most basic implementation is to just return `value`: it looks a lot
    like the dict we pass `render()`. But we have special-case implementations
    for a few dtypes.

    Features:

        * `Tab` and `MultiTab` raise RuntimeError.
        * `column` parameters become '' if they aren't input columns
        * `multicolumn` parameters lose values that aren't input columns
        * Raise `PromptingError` if a chosen column is of the wrong type
          (so the caller can return a FetchResult with errors and quickfixes)
    """
    return value  # fallback method


@clean_value.register(ParamDType.Float)
def _(
    dtype: ParamDType.Float, value: Union[int, float], input_metadata: TableMetadata
) -> float:
    # ParamDType.Float can have `int` values (because values come from
    # json.parse(), which only gives Numbers so can give "3" instead of
    # "3.0". We want to pass that as `float` in the `params` dict.
    return float(value)


@clean_value.register(ParamDType.File)
def _(
    dtype: ParamDType.File, value: Optional[str], input_metadata: TableMetadata
) -> Optional[pathlib.Path]:
    raise RuntimeError("Unsupported: fetch file")


@clean_value.register(ParamDType.Tab)
def _(dtype: ParamDType.Tab, value: str, input_metadata: TableMetadata) -> None:
    raise RuntimeError("Unsupported: fetch tab")


def _column_type_name(column_type: ColumnType) -> str:
    if isinstance(column_type, ColumnType.Text):
        return "text"
    elif isinstance(column_type, ColumnType.Date):
        return "date"
    elif isinstance(column_type, ColumnType.Number):
        return "number"
    elif isinstance(column_type, ColumnType.Timestamp):
        return "timestamp"
    else:
        raise ValueError("Unhandled column type %r" % column_type)


@clean_value.register(ParamDType.Column)
def _(dtype: ParamDType.Column, value: str, input_metadata: TableMetadata) -> str:
    if dtype.tab_parameter:
        raise RuntimeError("Unsupported: fetch column with tab_parameter")

    if not input_metadata.columns:
        return ""

    valid_columns = {c.name: c for c in input_metadata.columns}
    if value not in valid_columns:
        return ""  # Null column

    column = valid_columns[value]
    if dtype.column_types and _column_type_name(column.type) not in dtype.column_types:
        if "text" in dtype.column_types:
            found_type = None
        else:
            found_type = _column_type_name(column.type)
        raise PromptingError(
            [PromptingError.WrongColumnType([value], found_type, dtype.column_types)]
        )

    return value


@clean_value.register(ParamDType.Multicolumn)
def _(
    dtype: ParamDType.Multicolumn, value: List[str], input_metadata: TableMetadata
) -> str:
    if dtype.tab_parameter:
        raise RuntimeError("Unsupported: fetch multicolumn with tab_parameter")

    error_agg = PromptErrorAggregator()
    requested_colnames = set(value)

    valid_colnames = []
    # ignore colnames not in valid_columns
    # iterate in table order
    for column in input_metadata.columns:
        if column.name not in requested_colnames:
            continue

        if (
            dtype.column_types
            and _column_type_name(column.type) not in dtype.column_types
        ):
            if "text" in dtype.column_types:
                found_type = None
            else:
                found_type = _column_type_name(column.type)
            error_agg.add(
                PromptingError.WrongColumnType(
                    [column.name], found_type, dtype.column_types
                )
            )
        else:
            valid_colnames.append(column.name)

    error_agg.raise_if_nonempty()

    return valid_colnames


@clean_value.register(ParamDType.Multichartseries)
def _(
    dtype: ParamDType.Multichartseries,
    value: List[Dict[str, str]],
    input_metadata: TableMetadata,
) -> List[Dict[str, str]]:
    raise RuntimeError("Unsupported: fetch multichartseries")


# ... and then the methods for recursing
@clean_value.register(ParamDType.List)
def clean_value_list(
    dtype: ParamDType.List, value: List[Any], input_metadata: TableMetadata
) -> List[Any]:
    inner_clean = partial(clean_value, dtype.inner_dtype)
    ret = []
    error_agg = PromptErrorAggregator()
    for v in value:
        try:
            ret.append(inner_clean(v, input_metadata))
        except PromptingError as err:
            error_agg.extend(err.errors)
    error_agg.raise_if_nonempty()
    return ret


@clean_value.register(ParamDType.Multitab)
def _(
    dtype: ParamDType.Multitab, value: List[str], input_metadata: TableMetadata
) -> List[Any]:
    raise RuntimeError("Unsupported: fetch multitab")


@clean_value.register(ParamDType.Dict)
def _(
    dtype: ParamDType.Dict, value: Dict[str, Any], input_metadata: TableMetadata
) -> Dict[str, Any]:
    ret = {}
    error_agg = PromptErrorAggregator()

    for k, v in value.items():
        try:
            ret[k] = clean_value(dtype.properties[k], v, input_metadata)
        except PromptingError as err:
            error_agg.extend(err.errors)

    error_agg.raise_if_nonempty()
    return ret


@clean_value.register(ParamDType.Map)
def _(
    dtype: ParamDType.Map, value: Dict[str, Any], input_metadata: TableMetadata
) -> Dict[str, Any]:
    value_dtype = dtype.value_dtype
    value_clean = partial(clean_value, value_dtype)
    return dict((k, value_clean(v, input_metadata)) for k, v in value.items())
