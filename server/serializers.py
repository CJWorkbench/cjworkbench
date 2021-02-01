import datetime
import logging
import re
from collections import namedtuple
from dataclasses import asdict
from functools import singledispatch
from typing import Any, Dict, Iterable, List, Optional, Union

from allauth.account.utils import user_display
from cjwkernel.types import Column, I18nMessage, QuickFix, QuickFixAction, RenderError
from cjworkbench.i18n.trans import (
    MESSAGE_LOCALIZER_REGISTRY,
    MessageLocalizer,
    NotInternationalizedError,
)
from cjworkbench.settings import KB_ROOT_URL
from cjwstate import clientside
from cjwstate.modules.param_spec import ParamSpec
from django.contrib.auth import get_user_model
from icu import ICUError
from server.settingsutils import workbench_user_display

User = get_user_model()


_NeedCamelRegex = re.compile("_(\w)")


logger = logging.getLogger(__name__)


def _camelize_str(s: str) -> str:
    """Convert snake-case to camel-case.

    >>> _camelize_str('id_name')
    'idName'
    """
    return _NeedCamelRegex.sub(lambda s: s.group(1).upper(), s)


def _camelize_list(l: List[Any]) -> List[Any]:
    """Convert snake-case dicts within `l` to camel-case.

    >>> _camelize_list(['x_y', {'y_z': 'z_a'}])
    ['x_y', {'yZ': 'z_a'}]
    """
    return [_camelize_value(v) for v in l]


def _camelize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Convert snake-case keys within `d` to camel-case, recursively.

    >>> _camelize_dict({'a_b': 'b_c', 'c_d': {'e_f': 'f_g'}})
    {'aB': 'b_c', 'cD': {'eF': 'f_g'}}
    """
    return {_camelize_str(k): _camelize_value(v) for k, v in d.items()}


def _camelize_value(v: Any) -> Any:
    """Camelize keys of dicts within `v`, recursively.

    `v` must be a JSON-serializable dict.
    """
    if isinstance(v, dict):
        return _camelize_dict(v)
    elif isinstance(v, list):
        return _camelize_list(v)
    else:
        return v


JsonizeContext = namedtuple(
    "JsonizeContext", ["user", "session", "locale_id", "module_zipfiles"]
)
JsonizeModuleContext = namedtuple(
    "JsonizeModuleContext",
    ["user", "session", "locale_id", "module_id", "module_zipfiles"],
)


def _add_module_to_ctx(ctx: JsonizeContext, module_id: str) -> JsonizeModuleContext:
    return JsonizeModuleContext(
        user=ctx.user,
        session=ctx.session,
        locale_id=ctx.locale_id,
        module_id=module_id,
        module_zipfiles=ctx.module_zipfiles,
    )


def jsonize_datetime(dt_or_none: Optional[datetime.datetime]) -> str:
    if dt_or_none is None:
        return None
    else:
        # StoredObject IDs are actually their timestamps with
        # microsecond precision, encoded as ISO-8601 with 'Z' as the time zone
        # specifier. Anything else and IDs won't match up!
        return dt_or_none.isoformat() + "Z"


def jsonize_user(user: User) -> Dict[str, Any]:
    return {
        "display_name": user_display(user),
        "email": user.email,
        "is_staff": user.is_staff,
    }


def _maybe_yield(value: Optional[Union[clientside._Null, Any]]) -> Iterable[Any]:
    """Yield `value` if it is not None.

    Special case: yield `None` if `value == clientside.Null`.
    """
    if value is not None:
        # We check with "==" instead of "is". That's because we
        # pickle+unpickle, and the unpickled object won't be the original.
        if value == clientside.Null:
            value = None
        yield value


def _maybe_set(
    d: Dict[str, Any], key: str, value: Optional[Union[clientside._Null, Any]]
) -> None:
    """Set `d[key] = value` if `value` is not `None`.

    Special case: if `value` is `Null`, set `d[key] = None`.
    """
    for value in _maybe_yield(value):
        d[key] = value


def jsonize_clientside_acl_entry(entry: clientside.AclEntry) -> Dict[str, Any]:
    return {"email": entry.email, "canEdit": entry.can_edit}


@singledispatch
def _jsonize_param_spec(
    spec: ParamSpec, ctx: JsonizeModuleContext, prefix: str
) -> Dict[str, Any]:
    return _camelize_dict(spec.to_dict())


@_jsonize_param_spec.register(ParamSpec.String)
def _(spec: ParamSpec.String, ctx: JsonizeModuleContext, prefix: str) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    ret["placeholder"] = _localize_module_spec_message(
        f"{prefix}.placeholder", ctx, spec.placeholder
    )
    ret["default"] = _localize_module_spec_message(
        f"{prefix}.default", ctx, spec.default
    )
    return ret


@_jsonize_param_spec.register(ParamSpec.Statictext)
def _(
    spec: ParamSpec.Statictext, ctx: JsonizeModuleContext, prefix: str
) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    return ret


@_jsonize_param_spec.register(ParamSpec.Integer)
def _(
    spec: ParamSpec.Integer, ctx: JsonizeModuleContext, prefix: str
) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    ret["placeholder"] = _localize_module_spec_message(
        f"{prefix}.placeholder", ctx, spec.placeholder
    )
    return ret


@_jsonize_param_spec.register(ParamSpec.Float)
def _(spec: ParamSpec.Float, ctx: JsonizeModuleContext, prefix: str) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    ret["placeholder"] = _localize_module_spec_message(
        f"{prefix}.placeholder", ctx, spec.placeholder
    )
    return ret


@_jsonize_param_spec.register(ParamSpec.Checkbox)
def _(
    spec: ParamSpec.Checkbox, ctx: JsonizeModuleContext, prefix: str
) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    return ret


@_jsonize_param_spec.register(ParamSpec.Menu)
def _(spec: ParamSpec.Menu, ctx: JsonizeModuleContext, prefix: str) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    ret["placeholder"] = _localize_module_spec_message(
        f"{prefix}.placeholder", ctx, spec.placeholder
    )
    ret["options"] = [
        "separator"
        if option is ParamSpec.Menu.Option.Separator
        else {
            "value": option.value,
            "label": _localize_module_spec_message(
                f"{prefix}.options.{option.value}.label", ctx, option.label
            ),
        }
        for option in spec.options
    ]
    return ret


@_jsonize_param_spec.register(ParamSpec.Radio)
def _(spec: ParamSpec.Radio, ctx: JsonizeModuleContext, prefix: str) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    ret["options"] = [
        {
            "value": option.value,
            "label": _localize_module_spec_message(
                f"{prefix}.options.{option.value}.label", ctx, option.label
            ),
        }
        for option in spec.options
    ]
    return ret


@_jsonize_param_spec.register(ParamSpec.Button)
def _(spec: ParamSpec.Button, ctx: JsonizeModuleContext, prefix: str) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    return ret


@_jsonize_param_spec.register(ParamSpec.NumberFormat)
def _(
    spec: ParamSpec.NumberFormat, ctx: JsonizeModuleContext, prefix: str
) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    ret["placeholder"] = _localize_module_spec_message(
        f"{prefix}.placeholder", ctx, spec.placeholder
    )
    return ret


@_jsonize_param_spec.register(ParamSpec.Column)
def _(spec: ParamSpec.Column, ctx: JsonizeModuleContext, prefix: str) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    ret["placeholder"] = _localize_module_spec_message(
        f"{prefix}.placeholder", ctx, spec.placeholder
    )
    return ret


@_jsonize_param_spec.register(ParamSpec.Multicolumn)
def _(
    spec: ParamSpec.Multicolumn, ctx: JsonizeModuleContext, prefix: str
) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    ret["placeholder"] = _localize_module_spec_message(
        f"{prefix}.placeholder", ctx, spec.placeholder
    )
    return ret


@_jsonize_param_spec.register(ParamSpec.Tab)
def _(spec: ParamSpec.Tab, ctx: JsonizeModuleContext, prefix: str) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    ret["placeholder"] = _localize_module_spec_message(
        f"{prefix}.placeholder", ctx, spec.placeholder
    )
    return ret


@_jsonize_param_spec.register(ParamSpec.Multitab)
def _(
    spec: ParamSpec.Multitab, ctx: JsonizeModuleContext, prefix: str
) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    ret["placeholder"] = _localize_module_spec_message(
        f"{prefix}.placeholder", ctx, spec.placeholder
    )
    return ret


@_jsonize_param_spec.register(ParamSpec.Multichartseries)
def _(
    spec: ParamSpec.Multichartseries, ctx: JsonizeModuleContext, prefix: str
) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    return ret


@_jsonize_param_spec.register(ParamSpec.Secret)
def _(spec: ParamSpec.Secret, ctx: JsonizeModuleContext, prefix: str) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    if spec.secret_logic.provider == "string":
        ret["secretLogic"]["label"] = _localize_module_spec_message(
            f"{prefix}.secret_logic.label", ctx, spec.secret_logic.label
        )
        ret["secretLogic"]["help"] = _localize_module_spec_message(
            f"{prefix}.secret_logic.help", ctx, spec.secret_logic.help
        )
        ret["secretLogic"]["helpUrl"] = _localize_module_spec_message(
            f"{prefix}.secret_logic.help_url", ctx, spec.secret_logic.help_url
        )
        ret["secretLogic"]["helpUrlPrompt"] = _localize_module_spec_message(
            f"{prefix}.secret_logic.help_url_prompt",
            ctx,
            spec.secret_logic.help_url_prompt,
        )
    return ret


@_jsonize_param_spec.register(ParamSpec.Custom)
def _(spec: ParamSpec.Custom, ctx: JsonizeModuleContext, prefix: str) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    return ret


@_jsonize_param_spec.register(ParamSpec.List)
def _(spec: ParamSpec.List, ctx: JsonizeModuleContext, prefix: str) -> Dict[str, Any]:
    ret = _camelize_dict(spec.to_dict())
    ret["name"] = _localize_module_spec_message(f"{prefix}.name", ctx, spec.name)
    ret["childDefault"] = spec.dtype.inner_dtype.default
    ret["childParameters"] = [
        _jsonize_param_spec(
            child_spec, ctx, f"{prefix}.child_parameters.{child_spec.id_name}"
        )
        for child_spec in spec.child_parameters
    ]
    return ret


def _ctx_authorized_write(
    workflow: clientside.WorkflowUpdate, ctx: JsonizeContext
) -> bool:
    user = ctx.user

    if user.is_anonymous:
        # We got this far, so an anonymous user has read access. How? We'll
        # reverse-engineer.
        #
        # * It's a public, non-example workflow => then the user does not have
        #   write access.
        # * It's a private, non-example workflow => then it's an anonymous
        #   workflow _owned by this anonymous user_. The user has write access.
        # * It's an example workflow => this can't happen! We never serialize
        #   example workflows. We duplicate them and serialize the duplicates
        #   ... which are private, non-example workfows.
        return workflow.public is False

    return _ctx_authorized_owner(workflow, ctx) or any(
        entry.can_edit and entry.email == user.email for entry in workflow.acl
    )


def _ctx_authorized_owner(
    workflow: clientside.WorkflowUpdate, ctx: JsonizeContext
) -> bool:
    # mimics models.Workflow.user_session_authorized_owner
    owner = workflow.owner
    user = ctx.user
    return (
        user and user == owner
    ) or not owner  # in an anonymous workflow, (s)he who sees it owns it


def jsonize_clientside_workflow(
    workflow: clientside.WorkflowUpdate, ctx: JsonizeContext, *, is_init: bool
) -> Dict[str, Any]:
    """Build a JSON-ready dict representation of `workflow`.

    If `is_init`, we add some extra properties:

    * `read_only` -- TODO derive client-side (so it changes when ACL changes)
    * `is_owner`
    * `owner_email`
    * `owner_name`
    * `is_anonymous` -- TODO derive client-side
    """
    d = {}
    for k, v in (
        ("id", workflow.id),
        ("url_id", workflow.url_id),
        ("name", workflow.name),
        ("tab_slugs", workflow.tab_slugs),
        ("public", workflow.public),
        ("selected_tab_position", workflow.selected_tab_position),
        ("hasCustomReport", workflow.has_custom_report),
        ("blockSlugs", workflow.block_slugs),
    ):
        _maybe_set(d, k, v)
    for updated_at in _maybe_yield(workflow.updated_at):
        d["last_update"] = jsonize_datetime(updated_at)
    for acl in _maybe_yield(workflow.acl):
        d["acl"] = [jsonize_clientside_acl_entry(e) for e in acl]
    if is_init:
        d.update(
            {
                # assume if we're passing the workflow here the user is allowed
                # to read it.
                "read_only": not _ctx_authorized_write(workflow, ctx),
                "is_owner": _ctx_authorized_owner(workflow, ctx),
                "owner_email": (
                    workflow.owner.email
                    # TODO simplify -- why is workflow.owner sometimes set,
                    # sometimes not? Choose one and follow through with it.
                    if (workflow.owner and not workflow.owner.is_anonymous)
                    else None
                ),
                "owner_name": (
                    "Workbench"
                    if workflow.is_example
                    else workbench_user_display(workflow.owner)
                ),
                "is_anonymous": workflow.url_id != workflow.id,
                "selected_tab_position": workflow.selected_tab_position,
            }
        )
    return d


def jsonize_clientside_block(block: clientside.Block) -> Dict[str, str]:
    if block.type == "text":
        return {"type": "text", "markdown": block.markdown}
    elif block.type == "chart":
        return {"type": "chart", "stepSlug": block.step_slug}
    elif block.type == "table":
        return {"type": "table", "tabSlug": block.tab_slug}
    else:
        raise NotImplementedError


def jsonize_clientside_module(
    module: clientside.Module, ctx: JsonizeContext
) -> Dict[str, Any]:
    spec = module.spec
    ctx = _add_module_to_ctx(ctx, spec.id_name)

    help_url = spec.help_url
    if help_url and not (
        help_url.startswith("http://")
        or help_url.startswith("https://")
        or help_url.startswith("//")
    ):
        help_url = KB_ROOT_URL + help_url

    return {
        "id_name": spec.id_name,
        "name": _localize_module_spec_message("name", ctx, spec.name),
        "category": spec.category,
        "description": _localize_module_spec_message(
            "description", ctx, spec.description
        ),
        "deprecated": {
            "message": _localize_module_spec_message(
                "deprecated.message", ctx, spec.deprecated["message"]
            ),
            "end_date": spec.deprecated["end_date"],
        }
        if spec.deprecated
        else None,
        "icon": spec.icon or "url",
        "loads_data": spec.loads_data,
        "uses_data": spec.get_uses_data(),
        "help_url": help_url,
        "has_zen_mode": spec.has_zen_mode,
        "has_html_output": spec.html_output,
        "row_action_menu_entry_title": _localize_module_spec_message(
            "row_action_menu_entry_title", ctx, spec.row_action_menu_entry_title
        ),
        "js_module": module.js_module,
        "param_fields": [
            _jsonize_param_spec(field, ctx, prefix=f"parameters.{field.id_name}")
            for field in spec.param_fields
        ],
    }


def jsonize_clientside_tab(tab: clientside.TabUpdate) -> Dict[str, Any]:
    d = {}
    for k, v in (
        ("slug", tab.slug),
        ("name", tab.name),
        ("step_ids", tab.step_ids),
        ("selected_step_position", tab.selected_step_index),
    ):
        _maybe_set(d, k, v)
    return d


def _localize_module_spec_message(
    message_path: str, ctx: JsonizeModuleContext, spec_value: str
) -> str:
    """Search the module catalogs for the spec message with the given path and localize it.

    The path of the message is its translation key minus "_spec." at the beginning.

    If the message is not found or is incorrectly formatted, `spec_value` is returned.

    In addition, if `spec_value` is empty, `spec_value` is returned.
    This is in order to make sure that module spec values not defined in the spec file
    cannot be overriden by message catalogs.

    Uses `locale_id`, `module_id`, and `module_zipfiles` from `ctx`
    """
    if not spec_value:
        return spec_value

    message_id = f"_spec.{message_path}"

    if ctx.module_id not in ctx.module_zipfiles:
        logger.exception(f"Module {ctx.module_id} not in jsonize context")
        return spec_value

    try:
        localizer = MESSAGE_LOCALIZER_REGISTRY.for_module_zipfile(
            ctx.module_zipfiles[ctx.module_id]
        )
    except NotInternationalizedError:
        return spec_value

    try:
        return localizer.localize(ctx.locale_id, message_id)
    except ICUError:
        # `localize` handles `ICUError` for the given locale.
        # Hence, if we get here, it means that the message is badly formatted in the default locale.
        logger.exception(
            "I18nMessage badly formatted in default locale. id: %s, module: %s",
            message_id,
            ctx.module_id,
        )
        return spec_value
    except KeyError:
        logger.exception(
            "I18nMessage not found in module catalogs. id: %s, module: %s",
            message_id,
            ctx.module_id,
        )
        return spec_value


def _i18n_message_source_to_localizer(
    message: I18nMessage, ctx: JsonizeModuleContext
) -> MessageLocalizer:
    """Return a localizer for the source of the given `I18nMessage`.

    Raise `NotInternationalizedError` if the source is a non-internationalized module.
    Raise `KeyError` if the source is a module that has no associated `ModuleZipFile`.
    """
    if message.source == "module":
        module_zipfile = ctx.module_zipfiles[ctx.module_id]  # Raises `KeyError`
        return MESSAGE_LOCALIZER_REGISTRY.for_module_zipfile(
            module_zipfile
        )  # Raises `NotInternationalizedError`
    elif message.source == "cjwmodule":
        return MESSAGE_LOCALIZER_REGISTRY.cjwmodule_localizer
    elif message.source == "cjwparse":
        return MESSAGE_LOCALIZER_REGISTRY.cjwparse_localizer
    else:  # if message.source is None
        return MESSAGE_LOCALIZER_REGISTRY.application_localizer


def jsonize_i18n_message(message: I18nMessage, ctx: JsonizeModuleContext) -> str:
    """Localize (or unwrap, if it's a TODO_i18n) an `I18nMessage`

    Uses `locale_id` and `module_zipfiles` from `ctx`

    If the message content is not found or is invalid, a representation of the `I18nMessage` is returned.
    """
    if message.id == "TODO_i18n" and (
        message.source is None or message.source == "cjwmodule"
    ):
        return message.arguments["text"]

    # Get localizer
    try:
        localizer = _i18n_message_source_to_localizer(message, ctx)
    except NotInternationalizedError:
        logger.exception(
            "I18nMessage source %s does not support localization", message.source
        )
        return repr(message)
    except KeyError as err:
        logger.exception(
            "JsonizeContext not set properly for I18nMessage source %s. Error: %s",
            message.source,
            err,
        )
        return repr(message)

    # Attempt to localize in the locale given by `ctx`.
    try:
        return localizer.localize(
            ctx.locale_id, message.id, arguments=message.arguments
        )
    except ICUError:
        # `localize` handles `ICUError` for the given locale.
        # Hence, if we get here, it means that the message is badly formatted in the default locale.
        logger.exception(
            "I18nMessage badly formatted in default locale. id: %s, source: %s",
            message.id,
            message.source,
        )
        return repr(message)
    except KeyError:
        logger.exception(
            "I18nMessage content not found in catalogs. id: %s, source: %s",
            message.id,
            message.source,
        )
        return repr(message)


def jsonize_quick_fix_action(action: QuickFixAction) -> Dict[str, Any]:
    if isinstance(action, QuickFixAction.PrependStep):
        return {
            "type": "prependStep",
            "moduleSlug": action.module_slug,
            "partialParams": action.partial_params,
        }
    else:
        raise NotImplementedError


def jsonize_quick_fix(quick_fix: QuickFix, ctx: JsonizeModuleContext) -> Dict[str, Any]:
    return {
        "buttonText": jsonize_i18n_message(quick_fix.button_text, ctx),
        "action": jsonize_quick_fix_action(quick_fix.action),
    }


def jsonize_render_error(
    error: RenderError, ctx: JsonizeModuleContext
) -> Dict[str, Any]:
    return {
        "message": jsonize_i18n_message(error.message, ctx),
        "quickFixes": [jsonize_quick_fix(qf, ctx) for qf in error.quick_fixes],
    }


def jsonize_column(column: Column) -> Dict[str, Any]:
    ret = {"name": column.name, "type": column.type.name}
    if hasattr(column.type, "format"):
        ret["format"] = column.type.format
    return ret


def jsonize_fetched_version_list(
    versions: clientside.FetchedVersionList,
) -> Dict[str, Any]:
    return {
        "versions": [
            # TODO pass Objects, not Arrays
            [jsonize_datetime(v.created_at), v.is_seen]
            for v in versions.versions
        ],
        "selected": jsonize_datetime(versions.selected),
    }


def jsonize_clientside_step(
    step: clientside.StepUpdate, ctx: JsonizeContext
) -> Dict[str, Any]:
    d = {}
    for k, v in (
        ("id", step.id),
        ("slug", step.slug),
        ("module", step.module_slug),
        ("tab_slug", step.tab_slug),
        ("is_busy", step.is_busy),
        ("last_relevant_delta_id", step.last_relevant_delta_id),
        ("params", step.params),
        ("secrets", step.secrets),
        ("is_collapsed", step.is_collapsed),
        ("notes", step.notes),
        ("auto_update_data", step.is_auto_fetch),
        ("update_interval", step.fetch_interval),
        ("notifications", step.is_notify_on_change),
        ("has_unseen_notification", step.has_unseen_notification),
    ):
        _maybe_set(d, k, v)
    for crr in _maybe_yield(step.render_result):
        if crr is None:
            # This can happen during init. Afterwards, nobody should create a
            # StepUpdate with render_result=Null, because the client gets a
            # better experience if we leave the existing render result. (The
            # server should just send a new last_relevant_delta_id instead, to
            # notify the client its cache is stale.)
            d.update(
                {
                    "cached_render_result_delta_id": None,
                    "output_columns": [],
                    "output_errors": [],
                    "output_status": None,
                    "output_n_rows": 0,
                }
            )
        else:
            module_ctx = _add_module_to_ctx(ctx, step.module_slug)
            d.update(
                {
                    "cached_render_result_delta_id": crr.delta_id,
                    "output_columns": [
                        jsonize_column(c) for c in crr.table_metadata.columns
                    ],
                    "output_n_rows": crr.table_metadata.n_rows,
                    "output_status": crr.status,
                    "output_errors": [
                        jsonize_render_error(e, module_ctx) for e in crr.errors
                    ],
                }
            )
    for files in _maybe_yield(step.files):
        d["files"] = [
            {
                "uuid": file.uuid,
                "name": file.name,
                "size": file.size,
                "createdAt": jsonize_datetime(file.created_at),
            }
            for file in files
        ]
    for last_fetched_at in _maybe_yield(step.last_fetched_at):
        # jsonize_datetime(None) == None
        d["last_update_check"] = jsonize_datetime(last_fetched_at)
    for versions in _maybe_yield(step.versions):
        d["versions"] = jsonize_fetched_version_list(versions)
    return d


def jsonize_clientside_init(
    state: clientside.Init, ctx: JsonizeContext
) -> Dict[str, Any]:
    """Serialize an InitialWorkflow for the user, for use in json.dumps().

    The input is user-agnostic. The output is unique to each user. (There is
    some i18n code invoked here.)
    """
    return {
        "loggedInUser": None if ctx.user.is_anonymous else jsonize_user(ctx.user),
        "modules": {
            k: jsonize_clientside_module(v, ctx) for k, v in state.modules.items()
        },
        "tabs": {k: jsonize_clientside_tab(v) for k, v in state.tabs.items()},
        "steps": {
            str(k): jsonize_clientside_step(v, ctx) for k, v in state.steps.items()
        },
        "blocks": {
            str(k): jsonize_clientside_block(v) for k, v in state.blocks.items()
        },
        "workflowId": state.workflow.id,
        "workflow": jsonize_clientside_workflow(state.workflow, ctx, is_init=True),
        "settings": state.settings,
    }


def jsonize_clientside_update(
    update: clientside.Update, ctx: JsonizeContext
) -> Dict[str, Any]:
    """Serialize an InitialWorkflow for the user, for use in json.dumps().

    The input is user-agnostic. The output is unique to each user. (There is
    some i18n code invoked here.)
    """
    r = {}
    if update.mutation_id:
        r["mutationId"] = update.mutation_id
    if update.workflow:
        r["updateWorkflow"] = jsonize_clientside_workflow(
            update.workflow, ctx, is_init=False
        )
    if update.blocks:
        r["updateBlocks"] = {
            k: jsonize_clientside_block(v) for k, v in update.blocks.items()
        }
    if update.modules:
        r["updateModules"] = {
            k: jsonize_clientside_module(v, ctx) for k, v in update.modules.items()
        }
    if update.steps:
        r["updateSteps"] = {
            str(k): jsonize_clientside_step(v, ctx) for k, v in update.steps.items()
        }
    if update.tabs:
        r["updateTabs"] = {k: jsonize_clientside_tab(v) for k, v in update.tabs.items()}
    if update.clear_block_slugs:
        r["clearBlockSlugs"] = list(update.clear_block_slugs)
    if update.clear_tab_slugs:
        r["clearTabSlugs"] = list(update.clear_tab_slugs)
    if update.clear_step_ids:
        r["clearStepIds"] = list(str(id) for id in update.clear_step_ids)
    return r
