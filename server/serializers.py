import datetime
import logging
import re
from functools import singledispatch
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Union

from allauth.account.utils import user_display
from cjwmodule.i18n import I18nMessage
from cjwmodule.spec.paramfield import ParamField
from django.contrib.auth import get_user_model
from icu import ICUError

from cjwkernel.types import Column, ColumnType, QuickFix, QuickFixAction, RenderError
from cjworkbench.i18n.trans import (
    MESSAGE_LOCALIZER_REGISTRY,
    MessageLocalizer,
    NotInternationalizedError,
)
from cjworkbench.models.userlimits import UserLimits
from cjworkbench.models.userprofile import UserProfile
from cjworkbench.settings import KB_ROOT_URL
from cjwstate import clientside

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


class JsonizeContext(NamedTuple):
    locale_id: str
    module_zipfiles: Dict[str, "ModuleZipFile"]


class JsonizeModuleContext(NamedTuple):
    locale_id: str
    module_id: str
    module_zipfile: Optional["ModuleZipFile"]


def jsonize_datetime(dt_or_none: Optional[datetime.datetime]) -> str:
    if dt_or_none is None:
        return None
    else:
        # StoredObject IDs are actually their timestamps with
        # microsecond precision, encoded as ISO-8601 with 'Z' as the time zone
        # specifier. Anything else and IDs won't match up!
        return dt_or_none.isoformat() + "Z"


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
    return {"email": entry.email, "role": entry.role}


@singledispatch
def _jsonize_param_field(
    spec: ParamField, ctx: JsonizeModuleContext, prefix: str
) -> Dict[str, Any]:
    raise NotImplementedError("Cannot handle spec %r" % spec)


@_jsonize_param_field.register(ParamField.String)
def _(
    spec: ParamField.String, ctx: JsonizeModuleContext, prefix: str
) -> Dict[str, Any]:
    return dict(
        type="string",
        idName=spec.id_name,
        visibleIf=_camelize_value(spec.visible_if),
        name=_localize_module_spec_message(f"{prefix}.name", ctx, spec.name),
        placeholder=_localize_module_spec_message(
            f"{prefix}.placeholder", ctx, spec.placeholder
        ),
        default=_localize_module_spec_message(f"{prefix}.default", ctx, spec.default),
        multiline=spec.multiline,
        syntax=spec.syntax,
    )


@_jsonize_param_field.register(ParamField.Float)
@_jsonize_param_field.register(ParamField.Integer)
def _(
    spec: Union[ParamField.Float, ParamField.Integer],
    ctx: JsonizeModuleContext,
    prefix: str,
) -> Dict[str, Any]:
    return dict(
        type=spec.type,
        idName=spec.id_name,
        visibleIf=_camelize_value(spec.visible_if),
        name=_localize_module_spec_message(f"{prefix}.name", ctx, spec.name),
        placeholder=_localize_module_spec_message(
            f"{prefix}.placeholder", ctx, spec.placeholder
        ),
        default=spec.default,
    )


@_jsonize_param_field.register(ParamField.Multichartseries)
@_jsonize_param_field.register(ParamField.Multitab)
@_jsonize_param_field.register(ParamField.Tab)
def _(
    spec: Union[ParamField.Multichartseries, ParamField.Multitab, ParamField.Tab],
    ctx: JsonizeModuleContext,
    prefix: str,
) -> Dict[str, Any]:
    return dict(
        type=spec.type,
        idName=spec.id_name,
        visibleIf=_camelize_value(spec.visible_if),
        name=_localize_module_spec_message(f"{prefix}.name", ctx, spec.name),
        placeholder=_localize_module_spec_message(
            f"{prefix}.placeholder", ctx, spec.placeholder
        ),
    )


@_jsonize_param_field.register(ParamField.Checkbox)
@_jsonize_param_field.register(ParamField.Custom)
@_jsonize_param_field.register(ParamField.NumberFormat)
def _(
    spec: Union[ParamField.Checkbox, ParamField.Custom, ParamField.NumberFormat],
    ctx: JsonizeModuleContext,
    prefix: str,
) -> Dict[str, Any]:
    return dict(
        type=spec.type,
        idName=spec.id_name,
        visibleIf=_camelize_value(spec.visible_if),
        name=_localize_module_spec_message(f"{prefix}.name", ctx, spec.name),
        default=spec.default,
    )


@_jsonize_param_field.register(ParamField.Menu)
def _(spec: ParamField.Menu, ctx: JsonizeModuleContext, prefix: str) -> Dict[str, Any]:
    return dict(
        type="menu",
        idName=spec.id_name,
        visibleIf=_camelize_value(spec.visible_if),
        name=_localize_module_spec_message(f"{prefix}.name", ctx, spec.name),
        placeholder=_localize_module_spec_message(
            f"{prefix}.placeholder", ctx, spec.placeholder
        ),
        default=spec.default,
        options=[
            "separator"
            if option is ParamField.Menu.Option.Separator
            else {
                "value": option.value,
                "label": _localize_module_spec_message(
                    f"{prefix}.options.{option.value}.label", ctx, option.label
                ),
            }
            for option in spec.options
        ],
    )


@_jsonize_param_field.register(ParamField.Radio)
def _(spec: ParamField.Radio, ctx: JsonizeModuleContext, prefix: str) -> Dict[str, Any]:
    return dict(
        type="radio",
        idName=spec.id_name,
        visibleIf=_camelize_value(spec.visible_if),
        name=_localize_module_spec_message(f"{prefix}.name", ctx, spec.name),
        default=spec.default,
        options=[
            "separator"
            if option is ParamField.Menu.Option.Separator
            else {
                "value": option.value,
                "label": _localize_module_spec_message(
                    f"{prefix}.options.{option.value}.label", ctx, option.label
                ),
            }
            for option in spec.options
        ],
    )


@_jsonize_param_field.register(ParamField.Button)
@_jsonize_param_field.register(ParamField.Statictext)
@_jsonize_param_field.register(ParamField.Timezone)
def _(
    spec: Union[ParamField.Button, ParamField.Statictext, ParamField.Timezone],
    ctx: JsonizeModuleContext,
    prefix: str,
) -> Dict[str, Any]:
    return dict(
        type=spec.type,
        idName=spec.id_name,
        visibleIf=_camelize_value(spec.visible_if),
        name=_localize_module_spec_message(f"{prefix}.name", ctx, spec.name),
    )


@_jsonize_param_field.register(ParamField.Column)
@_jsonize_param_field.register(ParamField.Multicolumn)
def _(
    spec: Union[ParamField.Column, ParamField.Multicolumn],
    ctx: JsonizeModuleContext,
    prefix: str,
) -> Dict[str, Any]:
    return dict(
        type=spec.type,
        idName=spec.id_name,
        visibleIf=_camelize_value(spec.visible_if),
        name=_localize_module_spec_message(f"{prefix}.name", ctx, spec.name),
        placeholder=_localize_module_spec_message(
            f"{prefix}.placeholder", ctx, spec.placeholder
        ),
        columnTypes=(list(spec.column_types) if spec.column_types else None),
        tabParameter=spec.tab_parameter,
    )


@_jsonize_param_field.register(ParamField.Condition)
@_jsonize_param_field.register(ParamField.File)
def _(
    spec: Union[ParamField.Condition, ParamField.File],
    ctx: JsonizeModuleContext,
    prefix: str,
) -> Dict[str, Any]:
    return dict(
        type=spec.type,
        idName=spec.id_name,
        visibleIf=_camelize_value(spec.visible_if),
    )


@_jsonize_param_field.register(ParamField.Gdrivefile)
def _(
    spec: ParamField.Gdrivefile, ctx: JsonizeModuleContext, prefix: str
) -> Dict[str, Any]:
    return dict(
        type="gdrivefile",
        idName=spec.id_name,
        visibleIf=_camelize_value(spec.visible_if),
        name=_localize_module_spec_message(f"{prefix}.name", ctx, spec.name),
        secretParameter=spec.secret_parameter,
    )


@_jsonize_param_field.register(ParamField.Secret)
def _(
    spec: ParamField.Secret, ctx: JsonizeModuleContext, prefix: str
) -> Dict[str, Any]:
    logic = spec.secret_logic
    return dict(
        type="secret",
        idName=spec.id_name,
        visibleIf=_camelize_value(spec.visible_if),
        secretLogic=(
            dict(
                provider="string",
                label=_localize_module_spec_message(
                    f"{prefix}.secret_logic.label", ctx, spec.secret_logic.label
                ),
                pattern=logic.pattern,
                placeholder=logic.placeholder,
                help=_localize_module_spec_message(
                    f"{prefix}.secret_logic.help", ctx, spec.secret_logic.help
                ),
                helpUrl=_localize_module_spec_message(
                    f"{prefix}.secret_logic.help_url", ctx, spec.secret_logic.help_url
                ),
                helpUrlPrompt=_localize_module_spec_message(
                    f"{prefix}.secret_logic.help_url_prompt",
                    ctx,
                    spec.secret_logic.help_url_prompt,
                ),
            )
            if logic.provider == "string"
            else dict(provider=logic.provider, service=logic.service)
        ),
    )


@_jsonize_param_field.register(ParamField.List)
def _(spec: ParamField.List, ctx: JsonizeModuleContext, prefix: str) -> Dict[str, Any]:
    return dict(
        type="list",
        idName=spec.id_name,
        visibleIf=_camelize_value(spec.visible_if),
        name=_localize_module_spec_message(f"{prefix}.name", ctx, spec.name),
        childDefault=spec.to_schema().inner_schema.default,
        childParameters=[
            _jsonize_param_field(
                child_spec, ctx, f"{prefix}.child_parameters.{child_spec.id_name}"
            )
            for child_spec in spec.child_parameters
        ],
    )


def jsonize_clientside_workflow(
    workflow: clientside.WorkflowUpdate, ctx: JsonizeContext, *, is_init: bool
) -> Dict[str, Any]:
    """Build a JSON-ready dict representation of `workflow`.

    If `is_init`, we add some extra properties (MAY COST A SYNC DB ACCESS):

    * `owner_email`
    * `owner_name`
    """
    d = {}
    for k, v in (
        ("id", workflow.id),
        ("secret_id", workflow.secret_id),
        ("name", workflow.name),
        ("tab_slugs", workflow.tab_slugs),
        ("public", workflow.public),
        ("selected_tab_position", workflow.selected_tab_position),
        ("hasCustomReport", workflow.has_custom_report),
        ("blockSlugs", workflow.block_slugs),
        ("fetchesPerDay", workflow.fetches_per_day),
    ):
        _maybe_set(d, k, v)
    for updated_at in _maybe_yield(workflow.updated_at):
        d["last_update"] = jsonize_datetime(updated_at)
    for acl in _maybe_yield(workflow.acl):
        d["acl"] = [jsonize_clientside_acl_entry(e) for e in acl]
    if is_init:
        d.update(
            {
                "owner_email": workflow.owner_email,
                "owner_name": workflow.owner_display_name,
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
    module_ctx = JsonizeModuleContext(
        ctx.locale_id, spec.id_name, ctx.module_zipfiles.get(spec.id_name)
    )

    help_url = spec.help_url
    if help_url and not (
        help_url.startswith("http://")
        or help_url.startswith("https://")
        or help_url.startswith("//")
    ):
        help_url = KB_ROOT_URL + help_url

    return {
        "id_name": spec.id_name,
        "name": _localize_module_spec_message("name", module_ctx, spec.name),
        "category": spec.category,
        "description": _localize_module_spec_message(
            "description", module_ctx, spec.description
        ),
        "deprecated": {
            "message": _localize_module_spec_message(
                "deprecated.message", module_ctx, spec.deprecated["message"]
            ),
            "end_date": spec.deprecated["end_date"],
        }
        if spec.deprecated
        else None,
        "icon": spec.icon or "url",
        "loads_data": spec.loads_data,
        "uses_data": spec.uses_data,
        "help_url": help_url,
        "has_zen_mode": spec.has_zen_mode,
        "has_html_output": spec.html_output,
        "row_action_menu_entry_title": _localize_module_spec_message(
            "row_action_menu_entry_title", module_ctx, spec.row_action_menu_entry_title
        ),
        "js_module": module.js_module,
        "param_fields": [
            _jsonize_param_field(
                field, module_ctx, prefix=f"parameters.{field.id_name}"
            )
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

    if ctx.module_zipfile is None:
        logger.exception(f"Module {ctx.module_id} not in jsonize context")
        return spec_value

    try:
        localizer = MESSAGE_LOCALIZER_REGISTRY.for_module_zipfile(ctx.module_zipfile)
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
            str(ctx.module_zipfile.path),
        )
        return spec_value
    except KeyError:
        logger.exception(
            "I18nMessage not found in module catalogs. id: %s, module: %s",
            message_id,
            str(ctx.module_zipfile.path),
        )
        return spec_value


def _i18n_message_source_to_localizer(
    message: I18nMessage, ctx: JsonizeModuleContext
) -> MessageLocalizer:
    """Return a localizer for the source of the given `I18nMessage`.

    Raise `NotInternationalizedError` if the source is a non-internationalized module.
    """
    if message.source == "module":
        if ctx.module_zipfile is None:
            raise NotInternationalizedError
        return MESSAGE_LOCALIZER_REGISTRY.for_module_zipfile(ctx.module_zipfile)
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
        logger.exception("Module %s does not support localization", ctx.module_id)
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
    name = column.name
    ctype = column.type

    if isinstance(ctype, ColumnType.Text):
        return dict(name=name, type="text")
    elif isinstance(column.type, ColumnType.Date):
        return dict(name=name, type="date", unit=ctype.unit)
    elif isinstance(column.type, ColumnType.Number):
        return dict(name=name, type="number", format=ctype.format)
    elif isinstance(ctype, ColumnType.Timestamp):
        return dict(name=name, type="timestamp")
    else:
        raise ValueError("Unknown column type %r" % column.type)


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
            module_ctx = JsonizeModuleContext(
                ctx.locale_id,
                step.module_slug,
                ctx.module_zipfiles.get(step.module_slug),
            )
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


def jsonize_clientside_user(user: clientside.UserUpdate) -> Dict[str, Any]:
    d = {}
    for k, v in (
        ("display_name", user.display_name),
        ("email", user.email),
        ("is_staff", user.is_staff),
        ("stripeCustomerId", user.stripe_customer_id),
    ):
        _maybe_set(d, k, v)

    if user.limits:
        d["limits"] = user.limits._asdict()
    if user.subscribed_stripe_product_ids is not None:
        d["subscribedStripeProductIds"] = user.subscribed_stripe_product_ids
    if user.usage:
        d["usage"] = dict(fetchesPerDay=user.usage.fetches_per_day)
    return d


def jsonize_clientside_init(
    state: clientside.Init, ctx: JsonizeContext
) -> Dict[str, Any]:
    """Serialize an InitialWorkflow for the user, for use in json.dumps().

    The input is user-agnostic. The output is unique to each user. (There is
    some i18n code invoked here.)
    """
    return {
        "loggedInUser": jsonize_clientside_user(state.user) if state.user else None,
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
    if update.user:
        r["updateUser"] = jsonize_clientside_user(update.user)
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
