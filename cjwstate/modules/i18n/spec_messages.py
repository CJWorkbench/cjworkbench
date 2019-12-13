from cjwstate.models.param_spec import ParamSpec, MenuOptionEnum
from functools import singledispatch
from typing import Dict
from cjwstate.modules.module_loader import ModuleSpec


def find_spec_messages(spec: ModuleSpec) -> Dict[str, str]:
    messages = {
        "_spec.name": spec.get("name") or None,
        "_spec.description": spec.get("description") or None,
        "_spec.row_action_menu_entry_title": spec.get("row_action_menu_entry_title")
        or None,
        "_spec.deprecated.message": spec.get("deprecated", {}).get("message") or None,
    }
    for param_dict in spec.parameters:
        param_spec = ParamSpec.from_dict(param_dict)
        messages.update(
            extract_param_messages(param_spec, f"_spec.parameters.{param_spec.id_name}")
        )
    return messages


@singledispatch
def extract_param_messages(spec: ParamSpec, prefix: str) -> Dict[str, str]:
    return {}


def _add_if_set(
    messages: Dict[str, str], spec: object, prefix: str, key: str
) -> Dict[str, str]:
    value = getattr(spec, key)
    if value:
        messages.update({f"{prefix}.{key}": value})


@extract_param_messages.register(ParamSpec.String)
def _(spec: ParamSpec.String, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    _add_if_set(result, spec, prefix, "default")
    return result


@extract_param_messages.register(ParamSpec.Statictext)
def _(spec: ParamSpec.Statictext, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamSpec.Integer)
def _(spec: ParamSpec.Integer, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamSpec.Float)
def _(spec: ParamSpec.Float, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamSpec.Checkbox)
def _(spec: ParamSpec.Checkbox, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamSpec.Menu)
def _(spec: ParamSpec.Menu, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    for option in spec.options:
        if isinstance(option, MenuOptionEnum):
            _add_if_set(result, option, f"{prefix}.options.{option.value}", "label")
    return result


@extract_param_messages.register(ParamSpec.Radio)
def _(spec: ParamSpec.Radio, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    for option in spec.options:
        _add_if_set(result, option, f"{prefix}.options.{option.value}", "label")
    return result


@extract_param_messages.register(ParamSpec.Button)
def _(spec: ParamSpec.Button, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamSpec.NumberFormat)
def _(spec: ParamSpec.NumberFormat, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamSpec.Column)
def _(spec: ParamSpec.Column, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamSpec.Multicolumn)
def _(spec: ParamSpec.Multicolumn, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamSpec.Tab)
def _(spec: ParamSpec.Tab, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamSpec.Multitab)
def _(spec: ParamSpec.Multitab, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    _add_if_set(result, spec, prefix, "placeholder")
    return result


@extract_param_messages.register(ParamSpec.Multichartseries)
def _(spec: ParamSpec.Multichartseries, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamSpec.Secret)
def _(spec: ParamSpec.Secret, prefix: str) -> Dict[str, str]:
    result = {}
    if spec.secret_logic.provider == "string":
        secret_prefix = f"{prefix}.secret_logic"
        _add_if_set(result, spec.secret_logic, secret_prefix, "label")
        _add_if_set(result, spec.secret_logic, secret_prefix, "help")
        _add_if_set(result, spec.secret_logic, secret_prefix, "help_url")
        _add_if_set(result, spec.secret_logic, secret_prefix, "help_url_prompt")
    return result


@extract_param_messages.register(ParamSpec.Custom)
def _(spec: ParamSpec.Custom, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    return result


@extract_param_messages.register(ParamSpec.List)
def _(spec: ParamSpec.List, prefix: str) -> Dict[str, str]:
    result = {}
    _add_if_set(result, spec, prefix, "name")
    for child_spec in spec.child_parameters:
        result.update(
            extract_param_messages(
                child_spec, f"{prefix}.child_parameters.{child_spec.id_name}"
            )
        )
    return result
