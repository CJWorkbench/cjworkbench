from rest_framework import serializers
from server.models import AclEntry, Workflow, WfModule, ParameterVal, \
        ParameterSpec, Module, ModuleVersion, StoredObject
from server.utils import seconds_to_count_and_units
from allauth.account.utils import user_display
from django.contrib.auth import get_user_model
from server.settingsutils import workbench_user_display
from cjworkbench.settings import KB_ROOT_URL
import re

User = get_user_model()


class AclEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AclEntry
        fields = ('workflow_id', 'email', 'created_at', 'can_edit')


class StoredObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoredObject
        fields = '__all__'


# So far, no one actually wants to see the default value.
class ParameterSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParameterSpec
        fields = ('id', 'name', 'id_name', 'type', 'multiline', 'placeholder',
                  'visible_if')


class ParameterValSerializer(serializers.ModelSerializer):
    parameter_spec = ParameterSpecSerializer(many=False, read_only=True)

    # Custom serialization for value, to return correct types
    # (e.g. boolean for checkboxes)
    value = serializers.SerializerMethodField()

    def get_value(self, obj):
        return obj.get_value()

    class Meta:
        model = ParameterVal
        fields = ('id', 'parameter_spec', 'value', 'visible', 'items')


class ModuleSerializer(serializers.ModelSerializer):
    help_url = serializers.SerializerMethodField()

    def get_help_url(self, obj):
        url_pattern = re.compile('^http(?:s?)://', re.IGNORECASE)

        if re.search(url_pattern, obj.help_url):
            return obj.help_url

        return "%s%s" % (KB_ROOT_URL, obj.help_url)

    class Meta:
        model = Module

        fields = ('id', 'id_name', 'name', 'category', 'description', 'link',
                  'author', 'icon', 'loads_data', 'help_url', 'has_zen_mode',
                  'row_action_menu_entry_title')


class ModuleVersionSerializer(serializers.ModelSerializer):
    module = serializers.PrimaryKeyRelatedField(many=False, read_only=True)

    class Meta:
        model = ModuleVersion
        fields = ('module', 'source_version_hash', 'last_update_time')


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    def get_display_name(self, obj):
        return user_display(obj)

    class Meta:
        model = User
        fields = ('email', 'display_name', 'id')


class WfModuleSerializer(serializers.ModelSerializer):
    parameter_vals = ParameterValSerializer(many=True, read_only=True)
    module_version = serializers.SerializerMethodField()
    update_interval = serializers.SerializerMethodField()
    update_units = serializers.SerializerMethodField()
    html_output = serializers.SerializerMethodField()
    versions = serializers.SerializerMethodField()
    quick_fixes = serializers.SerializerMethodField()

    def get_module_version(self, wfm):
        if wfm.module_version is not None:
            s = ModuleVersionSerializer(wfm.module_version)
            return s.data
        else:
            # Minimal fields so front end won't crash
            return {'module': None}

    # update interval handling is a little tricky as we need to convert seconds
    # to count+units
    def get_update_interval(self, wfm):
        return seconds_to_count_and_units(wfm.update_interval)['count']

    def get_update_units(self, wfm):
        return seconds_to_count_and_units(wfm.update_interval)['units']

    def get_html_output(self, wfm):
        if wfm.module_version is not None:
            return wfm.module_version.html_output
        else:
            return False

    def get_versions(self, wfm):
        versions = wfm.list_fetched_data_versions()
        current_version = wfm.get_fetched_data_version()
        return {'versions': versions, 'selected': current_version}

    def get_cached_render_result_data(self, wfm):
        cached_result = wfm.get_cached_render_result()
        data = {
            'cached_render_result_delta_id': None,
            'output_columns': None,
            'output_n_rows': None,
        }

        if (
            not cached_result
            or cached_result.delta_id != wfm.last_relevant_delta_id
        ):
            return data

        try:
            columns = [{'name': c.name, 'type': c.type}
                       for c in cached_result.columns]
            data['cached_render_result_delta_id']: cached_result.delta_id
            data['output_columns'] = columns
            data['output_n_rows'] = len(cached_result)
        except FileNotFoundError:
            # We're serializing without locking the workflow, and we're in a
            # race. No biggie: the caller is probably going to request more
            # up-to-date data soon anyway.
            pass

        return data

    def get_quick_fixes(self, wfm):
        return wfm.cached_render_result_quick_fixes

    def to_representation(self, wfm):
        ret = super().to_representation(wfm)
        ret.update(self.get_cached_render_result_data(wfm))
        return ret

    class Meta:
        model = WfModule
        fields = ('id', 'module_version', 'workflow', 'status', 'error_msg',
                  'parameter_vals', 'is_collapsed', 'notes',
                  'auto_update_data', 'update_interval', 'update_units',
                  'last_update_check', 'notifications',
                  'has_unseen_notification', 'html_output', 'versions',
                  'last_relevant_delta_id', 'quick_fixes')


# Lite Workflow: Don't include any of the modules, just name and ID.
# For /workflows page
class WorkflowSerializerLite(serializers.ModelSerializer):
    read_only = serializers.SerializerMethodField()
    last_update = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    owner_email = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    def get_owner_name(self, obj):
        if obj.example:
            return 'Workbench'
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
        request = self.context['request']
        return obj.request_read_only(request)

    def get_is_owner(self, obj):
        request = self.context['request']
        return obj.request_authorized_owner(request)

    class Meta:
        model = Workflow
        fields = ('id', 'name', 'public', 'read_only', 'is_owner', 'last_update',
                  'owner_email', 'owner_name')


class WorkflowSerializer(WorkflowSerializerLite):
    wf_modules = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    revision = serializers.ReadOnlyField()

    class Meta:
        model = Workflow
        fields = ('id', 'url_id', 'name', 'revision', 'wf_modules', 'public',
                  'read_only', 'last_update', 'is_owner', 'owner_email',
                  'owner_name', 'selected_wf_module', 'is_anonymous')


class LessonSerializer(serializers.BaseSerializer):
    def to_representation(self, obj):
        return {
            'slug': obj.slug,
            'header': {
                'title': obj.header.title,
                'html': obj.header.html,
            },
            'sections': list(self._section_to_representation(section)
                             for section in obj.sections),
            'footer': {
                'title': obj.footer.title,
                'html': obj.footer.html,
            }
        }

    def _section_to_representation(self, obj):
        return {
            'title': obj.title,
            'html': obj.html,
            'steps': list(self._step_to_representation(step)
                          for step in obj.steps),
        }

    def _step_to_representation(self, obj):
        return {
            'html': obj.html,
            'highlight': obj.highlight,
            'testJs': obj.test_js,
        }
