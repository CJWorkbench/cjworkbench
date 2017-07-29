from rest_framework import serializers
from server.models import Workflow, WfModule, ParameterVal, ParameterSpec, Module, ModuleVersion
from server.utils import seconds_to_count_and_units

# So far, no one actually wants to see the default values.
# They'd be a bit trick to serialize anyway, as we'd want to hide the underlying storage (float/string/int/boolean)
class ParameterSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParameterSpec
        fields = ('id', 'name', 'id_name', 'type', 'multiline')


class ParameterValSerializer(serializers.ModelSerializer):
    parameter_spec = ParameterSpecSerializer(many=False, read_only=True)

    # Custom serialization for ParameterVal: maps internal primitive types to fields named for the parameter type
    value = serializers.SerializerMethodField()
    def get_value(self, obj):
        if obj.parameter_spec.type == ParameterSpec.NUMBER:
            return obj.float
        elif obj.parameter_spec.type == ParameterSpec.STRING:
            return obj.string
        elif obj.parameter_spec.type == ParameterSpec.CHECKBOX:
            return obj.boolean
        elif obj.parameter_spec.type == ParameterSpec.MENU:
            return obj.integer
        else:
            return None

    class Meta:
        model = ParameterVal
        fields = ('id', 'parameter_spec', 'value', 'visible', 'menu_items')


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ('id', 'name', 'category', 'description', 'link', 'author')

class ModuleVersionSerializer(serializers.ModelSerializer):
    module = ModuleSerializer(many=False, read_only=True)
    class Meta:
        model = ModuleVersion
        fields = ('module', 'source_version_hash', 'last_update_time')


class WfModuleSerializer(serializers.ModelSerializer):
    parameter_vals = ParameterValSerializer(many=True, read_only=True)
    module_version = ModuleVersionSerializer(many=False, read_only=True)

    # update interval handling is a little tricky as we need to convert seconds to count+units
    update_interval = serializers.SerializerMethodField()
    def get_update_interval(self, wfm):
        return seconds_to_count_and_units(wfm.update_interval)['count']

    update_units = serializers.SerializerMethodField()
    def get_update_units(self, wfm):
        return seconds_to_count_and_units(wfm.update_interval)['units']

    class Meta:
        model = WfModule
        fields = ('id', 'module_version', 'workflow', 'status', 'error_msg', 'parameter_vals',
                  'notes', 'auto_update_data', 'update_interval', 'update_units', 'last_update_check')


class WorkflowSerializer(serializers.ModelSerializer):
    wf_modules = WfModuleSerializer(many=True, read_only=True)
    revision = serializers.ReadOnlyField()

    class Meta:
        model = Workflow
        fields = ('id', 'name', 'revision', 'wf_modules')


# Lite Workflow: Don't include any of the modules, just name and ID. For /workflows page
class WorkflowSerializerLite(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = ('id', 'name')
