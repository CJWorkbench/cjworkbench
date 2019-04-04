import re
from typing import Optional
from allauth.account.utils import user_display
from django.contrib.auth import get_user_model
from rest_framework import serializers
from cjworkbench.settings import KB_ROOT_URL
from server.models import AclEntry, Workflow, WfModule, \
        ModuleVersion, StoredObject, Tab
from server.utils import seconds_to_count_and_units
from server.settingsutils import workbench_user_display

User = get_user_model()


class AclEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AclEntry
        fields = ('workflow_id', 'email', 'created_at', 'can_edit')


class StoredObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoredObject
        fields = '__all__'


class ParamFieldSerializer(serializers.Serializer):
    id_name = serializers.CharField()
    type = serializers.CharField(source='ftype')
    name = serializers.CharField()
    multiline = serializers.BooleanField()
    placeholder = serializers.CharField()
    items = serializers.CharField()
    enumOptions = serializers.JSONField(source='options')
    visible_if = serializers.JSONField()
    # So far, no one actually wants to see the default value.


class ModuleSerializer(serializers.ModelSerializer):
    param_fields = ParamFieldSerializer(many=True, read_only=True)
    help_url = serializers.SerializerMethodField()

    def get_help_url(self, obj):
        url_pattern = re.compile('^http(?:s?)://', re.IGNORECASE)

        if re.search(url_pattern, obj.help_url):
            return obj.help_url

        return "%s%s" % (KB_ROOT_URL, obj.help_url)

    class Meta:
        model = ModuleVersion

        fields = ('id_name', 'name', 'category', 'description',
                  'icon', 'loads_data', 'help_url', 'has_zen_mode',
                  'row_action_menu_entry_title', 'js_module',
                  'param_fields')


class TabSerializer(serializers.ModelSerializer):
    wf_module_ids = serializers.SerializerMethodField()

    def get_wf_module_ids(self, obj):
        return list(obj.live_wf_modules.values_list('id', flat=True))

    class Meta:
        model = Tab
        fields = ('slug', 'name', 'wf_module_ids',
                  'selected_wf_module_position')


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    def get_display_name(self, obj):
        return user_display(obj)

    class Meta:
        model = User
        fields = ('email', 'display_name', 'id', 'is_staff')


class WfModuleSerializer(serializers.ModelSerializer):
    params = serializers.SerializerMethodField()
    update_interval = serializers.SerializerMethodField()
    update_units = serializers.SerializerMethodField()
    html_output = serializers.SerializerMethodField()
    versions = serializers.SerializerMethodField()
    quick_fixes = serializers.SerializerMethodField()
    module = serializers.SerializerMethodField()

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
        current_version = wfm.stored_data_version
        return {'versions': versions, 'selected': current_version}

    def get_module(self, wfm):
        return wfm.module_id_name

    def get_cached_render_result_data(self, wfm):
        cached_result = wfm.cached_render_result
        data = {
            'cached_render_result_delta_id': None,
            'output_columns': None,
            'output_n_rows': None,
        }

        if not cached_result:
            return data

        columns = [c.to_dict() for c in cached_result.columns]
        data['cached_render_result_delta_id'] = cached_result.delta_id
        data['output_columns'] = columns
        data['output_n_rows'] = cached_result.nrows

        return data

    def get_quick_fixes(self, wfm):
        return wfm.cached_render_result_quick_fixes

    def to_representation(self, wfm):
        ret = super().to_representation(wfm)
        ret.update(self.get_cached_render_result_data(wfm))
        return ret

    def get_params(self, wfm):
        """WfModule.params, _plus secret metadata_"""
        wfm.get_params()
        return wfm.get_params().as_dict()

    class Meta:
        model = WfModule
        fields = ('id', 'module', 'tab_slug', 'is_busy',
                  'output_error', 'output_status', 'fetch_error',
                  'params', 'is_collapsed', 'notes', 'auto_update_data',
                  'update_interval', 'update_units', 'last_update_check',
                  'notifications', 'has_unseen_notification', 'html_output',
                  'versions', 'last_relevant_delta_id', 'quick_fixes')


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
        fields = ('id', 'name', 'public', 'read_only', 'is_owner',
                  'last_update', 'owner_email', 'owner_name')


class WorkflowSerializer(WorkflowSerializerLite):
    tab_slugs = serializers.SerializerMethodField()

    def get_tab_slugs(self, obj):
        return list(obj.live_tabs.values_list('slug', flat=True))

    class Meta:
        model = Workflow
        fields = ('id', 'url_id', 'name', 'tab_slugs', 'public', 'read_only',
                  'last_update', 'is_owner', 'owner_email', 'owner_name',
                  'selected_tab_position', 'is_anonymous')


class LessonSerializer(serializers.BaseSerializer):
    def to_representation(self, obj):
        return {
            'course': self._course_to_representation(obj.course),
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
                'isFullScreen': obj.footer.is_full_screen,
            }
        }

    def _course_to_representation(self, obj: Optional['Course']):
        if obj is None:
            return None
        else:
            return {
                'slug': obj.slug,
                'title': obj.title,
            }

    def _section_to_representation(self, obj):
        return {
            'title': obj.title,
            'html': obj.html,
            'steps': list(self._step_to_representation(step)
                          for step in obj.steps),
            'isFullScreen': obj.is_full_screen,
        }

    def _step_to_representation(self, obj):
        return {
            'html': obj.html,
            'highlight': obj.highlight,
            'testJs': obj.test_js,
        }
