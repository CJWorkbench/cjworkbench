from functools import singledispatch
from typing import Dict, Union

from cjwmodule.spec.types import ModuleSpec
from cjwmodule.spec.paramfield import ParamField


def find_spec_messages(spec: ModuleSpec) -> Dict[str, str]:
    messages = {}
    prefix = "_spec"
    _add_if_set(messages, spec, prefix, "name")
    _add_if_set(messages, spec, prefix, "description")
    _add_if_set(messages, spec, prefix, "row_action_menu_entry_title")
    if spec.deprecated:
        _add_if_set(messages, spec.deprecated, f"{prefix}.deprecated", "message")
    for field in spec.param_fields:
        messages.update(
            extract_param_messages(field, f"{prefix}.parameters.{field.id_name}")
        )
    return messages


def _add_if_set(
    messages: Dict[str, str],
    spec: Union[object, ModuleSpec, Dict[str, str]],
    prefix: str,
    key: str,
) -> Dict[str, str]:
    if isinstance(spec, dict):
        value = spec.get(key)
    else:
        value = getattr(spec, key)
    if value:
        messages.update({f"{prefix}.{key}": value})


@singledispatch
def extract_param_messages(spec: ParamField, prefix: str) -> Dict[str, str]:
    return {}


@extract_param_messages.register(ParamField.String)
def _(spec: ParamField.String, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    _add_if_set(result, spec, prefix, "default")
    return result


@extract_param_messages.register(ParamField.Statictext)
def _(spec: ParamField.Statictext, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamField.Integer)
def _(spec: ParamField.Integer, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamField.Float)
def _(spec: ParamField.Float, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamField.Checkbox)
def _(spec: ParamField.Checkbox, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamField.Menu)
def _(spec: ParamField.Menu, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    for option in spec.options:
        if isinstance(option, ParamField.Menu.Option.Value):
            _add_if_set(result, option, f"{prefix}.options.{option.value}", "label")
    return result


@extract_param_messages.register(ParamField.Radio)
def _(spec: ParamField.Radio, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    for option in spec.options:
        _add_if_set(result, option, f"{prefix}.options.{option.value}", "label")
    return result


@extract_param_messages.register(ParamField.Button)
def _(spec: ParamField.Button, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamField.NumberFormat)
def _(spec: ParamField.NumberFormat, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamField.Column)
def _(spec: ParamField.Column, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamField.Multicolumn)
def _(spec: ParamField.Multicolumn, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamField.Tab)
def _(spec: ParamField.Tab, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamField.Multitab)
def _(spec: ParamField.Multitab, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamField.Multichartseries)
def _(spec: ParamField.Multichartseries, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamField.Secret)
def _(spec: ParamField.Secret, prefix: str) -> Dict[str, str]:
    result = {}
    if spec.secret_logic.provider == "string":
        secret_prefix = f"{prefix}.secret_logic"
        _add_if_set(result, spec.secret_logic, secret_prefix, "label")
        _add_if_set(result, spec.secret_logic, secret_prefix, "help")
        _add_if_set(result, spec.secret_logic, secret_prefix, "help_url")
        _add_if_set(result, spec.secret_logic, secret_prefix, "help_url_prompt")
    return result


@extract_param_messages.register(ParamField.Custom)
def _(spec: ParamField.Custom, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamField.Timezone)
def _(spec: ParamField.Custom, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamField.List)
def _(spec: ParamField.List, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    for child_spec in spec.child_parameters:
        result.update(
            extract_param_messages(
                child_spec, f"{prefix}.child_parameters.{child_spec.id_name}"
            )
        )
    return result
