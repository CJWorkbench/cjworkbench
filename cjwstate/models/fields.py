from dataclasses import asdict
from enum import Enum
from typing import Any, Dict

from django.core.exceptions import ValidationError
from django.db.models import Field, JSONField

from cjwkernel.types import (
    Column,
    ColumnType,
    I18nMessage,
    PrependStepQuickFixAction,
    QuickFix,
    QuickFixAction,
    RenderError,
)


def _i18n_message_to_dict(value: I18nMessage) -> Dict[str, Any]:
    if value.source:
        return {"id": value.id, "arguments": value.arguments, "source": value.source}
    else:
        return {"id": value.id, "arguments": value.arguments}


def _dict_to_i18n_message(value: Dict[str, Any]) -> I18nMessage:
    arguments = value["arguments"]
    # Compatibility for https://www.pivotaltracker.com/story/show/174865394
    # DELETEME when there are no CachedRenderResults from before 2020-10-01
    if not value.get("source") and value["id"] in (
        "py.renderer.execute.types.PromptingError.WrongColumnType.as_quick_fixes.general",
        "py.renderer.execute.types.PromptingError.WrongColumnType.as_error_message.general",
    ):
        for key in ("found_type", "best_wanted_type"):
            if arguments.get(key) == "datetime":
                arguments = {**arguments, key: "timestamp"}
    return I18nMessage(value["id"], arguments, value.get("source"))


def _quick_fix_action_to_dict(value: QuickFixAction) -> Dict[str, Any]:
    if isinstance(value, PrependStepQuickFixAction):
        return {
            "type": "prependStep",
            "moduleSlug": value.module_slug,
            "partialParams": value.partial_params,
        }
    else:
        raise NotImplementedError


def _dict_to_quick_fix_action(value: Dict[str, Any]) -> QuickFixAction:
    if value["type"] == "prependStep":
        return PrependStepQuickFixAction(value["moduleSlug"], value["partialParams"])
    else:
        raise ValueError("Unhandled type in QuickFixAction: %r", value)


def _quick_fix_to_dict(value: QuickFix) -> Dict[str, Any]:
    return {
        "buttonText": _i18n_message_to_dict(value.button_text),
        "action": _quick_fix_action_to_dict(value.action),
    }


def _dict_to_quick_fix(value: Dict[str, Any]) -> QuickFix:
    return QuickFix(
        _dict_to_i18n_message(value["buttonText"]),
        _dict_to_quick_fix_action(value["action"]),
    )


def _render_error_to_dict(value: RenderError) -> Dict[str, Any]:
    return {
        "message": _i18n_message_to_dict(value.message),
        "quickFixes": [_quick_fix_to_dict(qf) for qf in value.quick_fixes],
    }


def _dict_to_render_error(value: Dict[str, Any]) -> RenderError:
    return RenderError(
        _dict_to_i18n_message(value["message"]),
        [_dict_to_quick_fix(qf) for qf in value["quickFixes"]],
    )


def _column_to_dict(value: Column) -> Dict[str, Any]:
    return {"name": value.name, "type": value.type.name, **asdict(value.type)}


def _dict_to_column(value: Dict[str, Any]) -> ColumnType:
    kwargs = dict(value)
    name = kwargs.pop("name")
    type_name = kwargs.pop("type")
    try:
        type_cls = {
            "text": ColumnType.Text,
            "number": ColumnType.Number,
            "timestamp": ColumnType.Timestamp,
            "datetime": ColumnType.Timestamp,
        }[type_name]
    except KeyError:
        raise ValueError("Invalid type: %r" % type_name)

    return Column(name, type_cls(**kwargs))


class ColumnsField(JSONField):
    """
    Maps a List[Column] to a database JSON column.
    """

    description = "List of Column metadata, stored as JSON"

    def from_db_value(self, value, *args, **kwargs):
        value = super().from_db_value(value, *args, **kwargs)
        if value is None:
            return None

        return [_dict_to_column(c) for c in value]

    def validate(self, value, model_instance):
        super().validate(value, model_instance)

        if value is None:
            return

        if not isinstance(value, list):
            raise ValidationError("not a list", code="invalid", params={"value": value})

        for item in value:
            if not isinstance(item, Column):
                raise ValidationError(
                    "list item is not a column", code="invalid", params={"value": value}
                )

    def get_prep_value(self, value):
        if value is None:
            return None

        arr = [_column_to_dict(c) for c in value]
        return super().get_prep_value(arr)  # JSONField: arr->bytes


class RenderErrorsField(JSONField):
    """Maps a List[RenderError] to a database JSON column."""

    description = "List of RenderErrors, stored as JSON"

    def from_db_value(self, value, *args, **kwargs):
        value = super().from_db_value(value, *args, **kwargs)
        if value is None:
            return None

        return [_dict_to_render_error(re) for re in value]

    def validate(self, value, model_instance):
        super().validate(value, model_instance)

        if value is None:
            return

        if not isinstance(value, list):
            raise ValidationError("not a list", code="invalid", params={"value": value})

        for item in value:
            if not isinstance(item, RenderError):
                raise ValidationError(
                    "list item is not a RenderError",
                    code="invalid",
                    params={"value": value},
                )

    def get_prep_value(self, value):
        if value is None:
            return None

        arr = [_render_error_to_dict(re) for re in value]
        return super().get_prep_value(arr)  # JSONField: arr->bytes


class Role(Enum):
    """Access level of an ACL entry's user to its workflow."""

    EDITOR = "editor"
    """User may add, remove or edit steps and edit the report.

    User cannot view or edit secrets.
    """

    VIEWER = "viewer"
    """User may view steps (including their parameters) and the report.

    User cannot view secrets.
    """

    REPORT_VIEWER = "report-viewer"
    """User may view the "report" -- including all its embeds and tables.

    User cannot view any step parameters, or any embeds or tables that aren't
    included in the report. (The workflow editor is not viewable: only the
    report HTML and the data it links are viewable.)

    By default, a workflow's report includes all its embeds. So by default,
    report-viewer may view all those embeds and their tables.

    Access to an embed means access to the table data that backs it. The
    report-viewer may download all that table data.
    """


class RoleField(Field):
    """Maps a Role to a database Role (ENUM) column."""

    description = "ACL Role, in a Postgres 'acl_role' ENUM"

    def db_type(self, connection):
        return "acl_role"

    def from_db_value(self, value, *args, **kwargs):
        if value is None:
            return None

        return Role(value)

    def to_python(self, value):
        if value is None or isinstance(value, Role):
            return value

        try:
            return Role(value)
        except ValueError as err:
            raise ValidationError(str(err))

    def validate(self, value, model_instance):
        super().validate(value, model_instance)

        if not isinstance(value, Role):
            raise ValidationError("not a Role", code="invalid", params={"value": value})

    def get_prep_value(self, value):
        if value is None:
            return None

        return value.value
