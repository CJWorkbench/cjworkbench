from rest_framework import serializers
from server.models import Workflow, WfModule, ParameterVal, ParameterSpec, Module

class ParameterSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParameterSpec
        fields = ('id', 'name', 'id_name', 'type', 'def_number', 'def_string', 'def_text')

class ParameterValSerializer(serializers.ModelSerializer):
    parameter_spec = ParameterSpecSerializer(many=False, read_only=True)
    class Meta:
        model = ParameterVal
        fields = ('id', 'parameter_spec', 'number', 'string', 'text')

class ModuleSerializer(serializers.ModelSerializer):
    parameter_vals = ParameterValSerializer(many=True, read_only=True)
    class Meta:
        model = Module
        fields = ('id', 'name', 'parameter_vals')

class WfModuleSerializer(serializers.ModelSerializer):
    parameter_vals = ParameterValSerializer(many=True, read_only=True)
    module = ModuleSerializer(many=False, read_only=True)
    workflow = ModuleSerializer(many=False, read_only=True)
    class Meta:
        model = WfModule
        fields = ('id', 'module', 'workflow', 'status', 'error_msg', 'parameter_vals')

class WorkflowSerializer(serializers.ModelSerializer):
    wf_modules = WfModuleSerializer(many=True, read_only=True)
    class Meta:
        model = Workflow
        fields = ('id', 'name', 'revision', 'wf_modules')