from rest_framework import serializers
from server.models import Workflow, WfModule, ParameterVal, ParameterSpec, Module, ModuleVersion, StoredObject
from server.utils import seconds_to_count_and_units
from allauth.account.utils import user_display
from django.contrib.auth import get_user_model
from server.settingsutils import *
from cjworkbench.settings import KB_ROOT_URL
import re

User = get_user_model()

class StoredObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoredObject
        fields = '__all__'

# So far, no one actually wants to see the default value.
class ParameterSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParameterSpec
        fields = ('id', 'name', 'id_name', 'type', 'multiline', 'placeholder', 'visible_if')

class ParameterValSerializer(serializers.ModelSerializer):
    parameter_spec = ParameterSpecSerializer(many=False, read_only=True)

    # Custom serialization for value, to return correct types (e.g. boolean for checkboxes)
    value = serializers.SerializerMethodField()
    def get_value(self, obj):
        return obj.get_value()

    class Meta:
        model = ParameterVal
        fields = ('id', 'parameter_spec', 'value', 'visible', 'menu_items')


class ModuleSerializer(serializers.ModelSerializer):
    help_url = serializers.SerializerMethodField()

    def get_help_url(self, obj):
        url_pattern = re.compile('^http(?:s?)://', re.IGNORECASE)

        if re.search(url_pattern, obj.help_url):
            return obj.help_url

        return "%s%s" % (KB_ROOT_URL, obj.help_url)

    class Meta:
        model = Module

        fields = ('id', 'id_name', 'name', 'category', 'description', 'link', 'author', 'icon', 'loads_data', 'help_url')

class ModuleVersionSerializer(serializers.ModelSerializer):
    module = ModuleSerializer(many=False, read_only=True)
    class Meta:
        model = ModuleVersion
        fields = ('module', 'source_version_hash', 'last_update_time')

class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    def get_display_name(self, obj):
        return user_display(obj)

    class Meta:
        model = User
        fields = ('email', 'display_name', 'id', 'google_credentials' )


class WfModuleSerializer(serializers.ModelSerializer):
    parameter_vals = ParameterValSerializer(many=True, read_only=True)

    module_version = serializers.SerializerMethodField()
    def get_module_version(self, wfm):
        if wfm.module_version is not None:
            s = ModuleVersionSerializer(wfm.module_version)
            return s.data
        else:
            # Minimal fields so front end won't crash
            return {
                'module': {
                    'name':'Missing module',
                    'loads_data' : False
                }
            }

    # update interval handling is a little tricky as we need to convert seconds to count+units
    update_interval = serializers.SerializerMethodField()
    def get_update_interval(self, wfm):
        return seconds_to_count_and_units(wfm.update_interval)['count']

    update_units = serializers.SerializerMethodField()
    def get_update_units(self, wfm):
        return seconds_to_count_and_units(wfm.update_interval)['units']

    notification_count = serializers.SerializerMethodField()
    def get_notification_count(self, wfm):
        return wfm.notification_set.count()

    html_output = serializers.SerializerMethodField()
    def get_html_output(self, wfm):
        if wfm.module_version is not None:
            return wfm.module_version.html_output
        else:
            return False

    versions = serializers.SerializerMethodField()
    def get_versions(self, wfm):
        versions = wfm.list_fetched_data_versions()
        current_version = wfm.get_fetched_data_version()
        return {'versions': versions, 'selected': current_version}

    class Meta:
        model = WfModule
        fields = ('id', 'module_version', 'workflow', 'status', 'error_msg', 'parameter_vals', 'is_collapsed',
                  'notes', 'auto_update_data', 'update_interval', 'update_units', 'last_update_check',
                  'notifications', 'notification_count', 'html_output', 'versions')


class WorkflowSerializer(serializers.ModelSerializer):
    wf_modules = WfModuleSerializer(many=True, read_only=True)
    revision = serializers.ReadOnlyField()
    read_only = serializers.SerializerMethodField()
    last_update = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()

    def get_read_only(self, obj):
        # Use 'get' in case we have a request with no user.
        return obj.read_only(self.context.get('user', False))

    def get_last_update(self, obj):
        return obj.last_update()

    def get_owner_name(self, obj):
        # don't leak user info (e.g. email) if viewer is not owner.
        # Use 'get' in case we have a request with no user.
        if (self.context.get('user', False) == obj.owner):
            return workbench_user_display(obj.owner)
        else:
            return workbench_user_display_public(obj.owner)

    class Meta:
        model = Workflow
        fields = ('id', 'name', 'revision', 'wf_modules', 'public', 'read_only', 'last_update', 'owner_name', 'module_library_collapsed', 'selected_wf_module')


# Lite Workflow: Don't include any of the modules, just name and ID. For /workflows page
class WorkflowSerializerLite(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    def get_owner_name(self, obj):
        return user_display(obj.owner)

    last_update = serializers.SerializerMethodField()
    def get_last_update(self, obj):
        if not obj.last_delta:
            return obj.creation_date
        return obj.last_delta.datetime

    read_only = serializers.SerializerMethodField()
    def get_read_only(self, obj):
        return False                    # lite serializer is only used when listing workflows, which only owner can do

    class Meta:
        model = Workflow
        fields = ('id', 'name', 'public', 'read_only', 'last_update', 'owner_name')

class LessonSerializer(serializers.BaseSerializer):
    def to_representation(self, obj):
        return {
            'slug': obj.slug,
            'header': {
                'title': obj.header.title,
                'html': obj.header.html,
            },
            'sections': list(self._section_to_representation(section) for section in obj.sections),
        }

    def _section_to_representation(self, obj):
        return {
            'title': obj.title,
            'html': obj.html,
            'steps': list(self._step_to_representation(step) for step in obj.steps),
        }

    def _step_to_representation(self, obj):
        return {
            'html': obj.html,
        }
