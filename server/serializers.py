from collections import namedtuple
import contextlib
import datetime
import logging
import re
from typing import Any, Dict, Iterable, List, Optional, Union
from allauth.account.utils import user_display
from django.contrib.auth import get_user_model
from rest_framework import serializers
from cjwkernel.types import I18nMessage, QuickFix, RenderError
from cjworkbench.settings import KB_ROOT_URL
from cjwstate.models import Workflow, WfModule, ModuleVersion, StoredObject, Tab
from cjwstate.params import get_migrated_params
from server.settingsutils import workbench_user_display
from cjwstate.models.param_spec import ParamSpec
from cjwstate import clientside
from cjwkernel.types import RenderError
from cjworkbench.i18n import default_locale
from cjworkbench.i18n.trans import localize

User = get_user_model()


_NeedCamelRegex = re.compile("_(\w)")


logger = logging.getLogger(__name__)


def _camelize_str(s: str) -> str:
    """
    Convert snake-case to camel-case.

    >>> _camelize_str('id_name')
    'idName'
    """
    return _NeedCamelRegex.sub(lambda s: s.group(1).upper(), s)


def _camelize_list(l: List[Any]) -> List[Any]:
    """
    Convert snake-case dicts within `l` to camel-case.

    >>> _camelize_list(['x_y', {'y_z': 'z_a'}])
    ['x_y', {'yZ': 'z_a'}]
    """
    return [_camelize_value(v) for v in l]


def _camelize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert snake-case keys within `d` to camel-case, recursively.

    >>> _camelize_dict({'a_b': 'b_c', 'c_d': {'e_f': 'f_g'}})
    {'aB': 'b_c', 'cD': {'eF': 'f_g'}}
    """
    return {_camelize_str(k): _camelize_value(v) for k, v in d.items()}


def _camelize_value(v: Any) -> Any:
    """
    Camelize keys of dicts within `v`, recursively.

    `v` must be a JSON-serializable dict.
    """
    if isinstance(v, dict):
        return _camelize_dict(v)
    elif isinstance(v, list):
        return _camelize_list(v)
    else:
        return v


JsonizeContext = namedtuple("JsonizeContext", ["user", "session", "locale_id"])


def jsonize_datetime(dt_or_none: Optional[datetime.datetime]) -> str:
    if dt_or_none is None:
        return None
    else:
        # StoredObject IDs are actually their timestamps with
        # microsecond precision, encoded as ISO-8601 with 'Z' as the time zone
        # specifier. Anything else and IDs won't match up!
        return dt_or_none.isoformat().replace("+00:00", "Z")


def jsonize_user(user: User) -> Dict[str, Any]:
    return {
        "display_name": user_display(user),
        "email": user.email,
        "is_staff": user.is_staff,
    }


def _maybe_yield(value: Optional[Union[clientside._Null, Any]]) -> Iterable[Any]:
    """
    Yield `value` if it is not None.

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
    """
    Set `d[key] = value` if `value` is not `None`.

    Special case: if `value` is `Null`, set `d[key] = None`.
    """
    for value in _maybe_yield(value):
        d[key] = value


def jsonize_clientside_acl_entry(entry: clientside.AclEntry) -> Dict[str, Any]:
    return {"email": entry.email, "canEdit": entry.can_edit}


def jsonize_param_spec(p: ParamSpec, ctx: JsonizeContext) -> Dict[str, Any]:
    # TODO_i18n translate during output. May require a singledispatch.
    ret = _camelize_dict(p.to_dict())
    if isinstance(p, ParamSpec.List):
        ret["childDefault"] = p.dtype.inner_dtype.default
    return ret


def _ctx_authorized_write(
    workflow: clientside.WorkflowUpdate, ctx: JsonizeContext
) -> bool:
    owner = workflow.owner
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
    """
    Build a JSON-ready dict representation of `workflow`.

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


def jsonize_clientside_module(
    module: clientside.Module, ctx: JsonizeContext
) -> Dict[str, Any]:
    spec = module.spec

    help_url = spec.get("help_url", "")
    if help_url and not (
        help_url.startswith("http://")
        or help_url.startswith("https://")
        or help_url.startswith("//")
    ):
        help_url = KB_ROOT_URL + help_url

    return {
        "id_name": spec["id_name"],
        "name": spec["name"],  # TODO i18n
        "category": spec["category"],
        "description": spec.get("description", ""),  # TODO i18n
        "deprecated": spec.get("deprecated"),  # TODO i18n
        "icon": spec.get("icon", "url"),
        "loads_data": spec.get("loads_data", False),
        "uses_data": spec.get("uses_data", not spec.get("loads_data", False)),
        "help_url": spec.get("help_url", ""),
        "has_zen_mode": spec.get("has_zen_mode", False),
        "has_html_output": spec.get("html_output", False),
        "row_action_menu_entry_title": (
            spec.get("row_action_menu_entry_title", "")  # TODO i18n
        ),
        "js_module": module.js_module,
        "param_fields": [
            jsonize_param_spec(ParamSpec.from_dict(p), ctx) for p in spec["parameters"]
        ],
    }


def jsonize_clientside_tab(tab: clientside.TabUpdate) -> Dict[str, Any]:
    d = {}
    for k, v in (
        ("slug", tab.slug),
        ("name", tab.name),
        ("wf_module_ids", tab.step_ids),
        ("selected_wf_module_position", tab.selected_step_index),
    ):
        _maybe_set(d, k, v)
    return d


def jsonize_i18n_message(message: I18nMessage, ctx: JsonizeContext) -> Optional[str]:
    assert message.source is None
    if message.id == "TODO_i18n":
        return message.args["text"]
    else:
        # Attempt to localize in the locale given by `ctx`.
        return localize(ctx.locale_id, message.id, parameters=message.args)


def jsonize_quick_fix(quick_fix: QuickFix, ctx: JsonizeContext) -> Dict[str, Any]:
    return {
        "buttonText": jsonize_i18n_message(quick_fix.button_text, ctx),
        "action": quick_fix.action.to_dict(),
    }


def jsonize_render_error(error: RenderError, ctx: JsonizeContext) -> Dict[str, Any]:
    return {
        "message": jsonize_i18n_message(error.message, ctx),
        "quickFixes": [jsonize_quick_fix(qf, ctx) for qf in error.quick_fixes],
    }


def jsonize_fetched_version_list(
    versions: clientside.FetchedVersionList
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
                    "output_status": "busy",  # TODO derive this on the client
                    "output_n_rows": 0,
                }
            )
        else:
            d.update(
                {
                    "cached_render_result_delta_id": crr.delta_id,
                    "output_columns": [c.to_dict() for c in crr.table_metadata.columns],
                    "output_n_rows": crr.table_metadata.n_rows,
                    "output_status": crr.status,
                    "output_errors": [jsonize_render_error(e, ctx) for e in crr.errors],
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
    """
    Serialize an InitialWorkflow for the user, for use in json.dumps().

    The input is user-agnostic. The output is unique to each user. (There is
    some i18n code invoked here.)
    """
    return {
        "loggedInUser": None if ctx.user.is_anonymous else jsonize_user(ctx.user),
        "modules": {
            k: jsonize_clientside_module(v, ctx) for k, v in state.modules.items()
        },
        "tabs": {k: jsonize_clientside_tab(v) for k, v in state.tabs.items()},
        "wfModules": {
            str(k): jsonize_clientside_step(v, ctx) for k, v in state.steps.items()
        },
        "workflowId": state.workflow.id,
        "workflow": jsonize_clientside_workflow(state.workflow, ctx, is_init=True),
    }


def jsonize_clientside_update(
    update: clientside.Update, ctx: JsonizeContext
) -> Dict[str, Any]:
    """
    Serialize an InitialWorkflow for the user, for use in json.dumps().

    The input is user-agnostic. The output is unique to each user. (There is
    some i18n code invoked here.)
    """
    r = {}
    if update.workflow:
        r["updateWorkflow"] = jsonize_clientside_workflow(
            update.workflow, ctx, is_init=False
        )
    if update.modules:
        r["updateModules"] = {
            k: jsonize_clientside_module(v, ctx) for k, v in update.modules.items()
        }
    if update.steps:
        r["updateWfModules"] = {
            str(k): jsonize_clientside_step(v, ctx) for k, v in update.steps.items()
        }
    if update.tabs:
        r["updateTabs"] = {k: jsonize_clientside_tab(v) for k, v in update.tabs.items()}
    if update.clear_tab_slugs:
        r["clearTabSlugs"] = list(update.clear_tab_slugs)
    if update.clear_step_ids:
        r["clearWfModuleIds"] = list(str(id) for id in update.clear_step_ids)
    return r
