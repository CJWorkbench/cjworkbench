import logging
import re
from typing import Any, Dict, List, Optional
from allauth.account.utils import user_display
from django.contrib.auth import get_user_model
from rest_framework import serializers
from cjworkbench.settings import KB_ROOT_URL
from cjwstate.models import Workflow, WfModule, ModuleVersion, StoredObject, Tab
from cjwstate.params import get_migrated_params
from server.settingsutils import workbench_user_display
from cjwstate.models.param_spec import ParamSpec

User = get_user_model()


_NeedCamelRegex = re.compile("_(\w)")


logger = logging.getLogger(__name__)


def isoformat(dt_or_none) -> str:
    if dt_or_none is None:
        return None
    else:
        # StoredObject IDs are actually their timestamps with
        # microsecond precision, encoded as ISO-8601 with 'Z' as the time zone
        # specifier. Anything else and IDs won't match up!
        return dt_or_none.isoformat().replace("+00:00", "Z")


def _camelize_str(s: str) -> str:
    """
    Convert snake-case to camel-case.

    >>> _camelize('id_name')
    'idName'
    """
    return _NeedCamelRegex.sub(lambda s: s.group(1).upper(), s)


def _camelize_list(l: List[Any]) -> List[Any]:
    """
    Convert snake-case dicts within `l` to camel-case.

    >>> _camelize(['x_y', {'y_z': 'z_a'}])
    ['x_y', {'yZ': 'z_a'}]
    """
    return [_camelize_value(v) for v in l]


def _camelize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert snake-case keys within `d` to camel-case, recursively.

    >>> _camelize({'a_b': 'b_c', 'c_d': {'e_f': 'f_g'}})
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


class StoredObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoredObject
        fields = "__all__"


class ModuleSerializer(serializers.ModelSerializer):
    param_fields = serializers.SerializerMethodField()
    help_url = serializers.SerializerMethodField()

    def _serialize_param(self, p):
        ret = _camelize_dict(p.to_dict())
        if isinstance(p, ParamSpec.List):
            ret["childDefault"] = p.dtype.inner_dtype.default

        return ret

    def get_param_fields(self, obj):
        """
        Serializes as camel-case:

            {
                idName: 'myvar',
                visibleIf: {...},
                childParameters: {...}
            }
        """
        return [self._serialize_param(p) for p in obj.param_fields]

    def get_help_url(self, obj):
        url_pattern = re.compile("^http(?:s?)://", re.IGNORECASE)

        if re.search(url_pattern, obj.help_url):
            return obj.help_url

        return "%s%s" % (KB_ROOT_URL, obj.help_url)

    class Meta:
        model = ModuleVersion

        fields = (
            "id_name",
            "name",
            "category",
            "description",
            "deprecated",
            "icon",
            "loads_data",
            "uses_data",
            "help_url",
            "has_zen_mode",
            "row_action_menu_entry_title",
            "js_module",
            "param_fields",
        )


class TabSerializer(serializers.ModelSerializer):
    wf_module_ids = serializers.SerializerMethodField()

    def get_wf_module_ids(self, obj):
        return list(obj.live_wf_modules.values_list("id", flat=True))

    class Meta:
        model = Tab
        fields = ("slug", "name", "wf_module_ids", "selected_wf_module_position")


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    def get_display_name(self, obj):
        return user_display(obj)

    class Meta:
        model = User
        fields = ("email", "display_name", "id", "is_staff")


class WfModuleSerializer(serializers.ModelSerializer):
    params = serializers.SerializerMethodField()
    secrets = serializers.SerializerMethodField()  # NOT ACTUAL SECRETS
    html_output = serializers.SerializerMethodField()
    versions = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()
    quick_fixes = serializers.SerializerMethodField()
    module = serializers.SerializerMethodField()
    last_update_check = serializers.DateTimeField(format="iso-8601")

    def get_html_output(self, wfm):
        if wfm.module_version is not None:
            return wfm.module_version.html_output
        else:
            return False

    def get_versions(self, wfm):
        # DEPRECATED. Use `get_files` now.
        versions = [
            # XXX nonsense: Arrays instead of JSON objects.
            [isoformat(stored_at), read]
            for stored_at, read in wfm.list_fetched_data_versions()
        ]
        current_version = isoformat(wfm.stored_data_version)
        return {"versions": versions, "selected": current_version}

    def get_files(self, wfm):
        return [
            dict(uuid=uuid, name=name, size=size, createdAt=isoformat(created_at))
            for uuid, name, size, created_at in wfm.uploaded_files.values_list(
                "uuid", "name", "size", "created_at"
            )
        ]

    def get_module(self, wfm):
        return wfm.module_id_name

    def get_cached_render_result_data(self, wfm):
        cached_result = wfm.cached_render_result
        data = {
            "cached_render_result_delta_id": None,
            "output_columns": None,
            "output_n_rows": None,
        }

        if not cached_result:
            return data

        columns = [c.to_dict() for c in cached_result.table_metadata.columns]
        data["cached_render_result_delta_id"] = cached_result.delta_id
        data["output_columns"] = columns
        data["output_n_rows"] = cached_result.table_metadata.n_rows

        return data

    def get_quick_fixes(self, wfm):
        crr = wfm.cached_render_result
        if crr is None:
            return []
        else:
            return [qf.to_dict() for err in crr.errors for qf in err.quick_fixes]

    def to_representation(self, wfm):
        ret = super().to_representation(wfm)
        ret.update(self.get_cached_render_result_data(wfm))
        return ret

    def get_params(self, wfm):
        """
        WfModule.params, migrated.

        If migrate_params() gives bad results, we coerce them to _good_ results
        and email ourselves the error.
        """
        if wfm.module_version:
            param_schema = wfm.module_version.param_schema
            params = get_migrated_params(wfm)  # raise ModuleError
            try:
                param_schema.validate(params)
                return params
            except ValueError as err:
                logger.exception(
                    "%s.migrate_params() gave invalid output: %r",
                    wfm.module_id_name,
                    params,
                )
                return param_schema.coerce(params)
        else:
            return {}

    def get_secrets(self, wfm):
        """Secret *metadata* -- NOT THE ACTUAL SECRETS"""
        return wfm.secret_metadata

    class Meta:
        model = WfModule
        fields = (
            "id",
            "slug",
            "module",
            "tab_slug",
            "is_busy",
            "output_error",
            "output_status",
            "fetch_error",
            "files",
            "params",
            "secrets",
            "is_collapsed",
            "notes",
            "auto_update_data",
            "update_interval",
            "last_update_check",
            "notifications",
            "has_unseen_notification",
            "html_output",
            "versions",
            "last_relevant_delta_id",
            "quick_fixes",
        )


# Lite Workflow: Don't include any of the modules, just name and ID.
# For /workflows page
class WorkflowSerializerLite(serializers.ModelSerializer):
    acl = serializers.SerializerMethodField()
    read_only = serializers.SerializerMethodField()
    last_update = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    owner_email = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    def get_acl(self, obj):
        return [
            {"email": entry.email, "canEdit": entry.can_edit} for entry in obj.acl.all()
        ]

    def get_owner_name(self, obj):
        if obj.example:
            return "Workbench"
        else:
            return workbench_user_display(obj.owner)

    def get_owner_email(self, obj):
        if obj.owner and not obj.owner.is_anonymous:
            return obj.owner.email
        else:
            return None

    def get_last_update(self, obj):
        return obj.last_update()

    def get_read_only(self, obj):
        request = self.context["request"]
        return obj.request_read_only(request)

    def get_is_owner(self, obj):
        request = self.context["request"]
        return obj.request_authorized_owner(request)

    class Meta:
        model = Workflow
        fields = (
            "id",
            "name",
            "public",
            "read_only",
            "is_owner",
            "last_update",
            "owner_email",
            "owner_name",
            "acl",
        )


class WorkflowSerializer(WorkflowSerializerLite):
    tab_slugs = serializers.SerializerMethodField()

    def get_tab_slugs(self, obj):
        return list(obj.live_tabs.values_list("slug", flat=True))

    class Meta:
        model = Workflow
        fields = (
            "id",
            "url_id",
            "name",
            "tab_slugs",
            "public",
            "read_only",
            "last_update",
            "is_owner",
            "owner_email",
            "owner_name",
            "selected_tab_position",
            "is_anonymous",
            "acl",
        )


class LessonSerializer(serializers.BaseSerializer):
    def to_representation(self, obj):
        return {
            "course": self._course_to_representation(obj.course),
            "slug": obj.slug,
            "header": {"title": obj.header.title, "html": obj.header.html},
            "sections": list(
                self._section_to_representation(section) for section in obj.sections
            ),
            "footer": {
                "title": obj.footer.title,
                "html": obj.footer.html,
                "isFullScreen": obj.footer.is_full_screen,
            },
        }

    def _course_to_representation(self, obj: Optional["Course"]):
        if obj is None:
            return None
        else:
            return {"slug": obj.slug, "title": obj.title}

    def _section_to_representation(self, obj):
        return {
            "title": obj.title,
            "html": obj.html,
            "steps": list(self._step_to_representation(step) for step in obj.steps),
            "isFullScreen": obj.is_full_screen,
        }

    def _step_to_representation(self, obj):
        return {"html": obj.html, "highlight": obj.highlight, "testJs": obj.test_js}
