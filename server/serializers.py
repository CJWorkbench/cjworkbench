from rest_framework import serializers
from server.models import Workflow, WfModule, ParameterVal, ParameterSpec, Module

class ParameterValSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParameterVal
        fields = ('id', 'parameter_spec', 'number', 'string', 'text')

class ParameterSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParameterSpec
        fields = ('id', 'name', 'type', 'default_number', 'default_string', 'default_text')

class ModuleSerializer(serializers.ModelSerializer):
    parameter_specs = ParameterSpecSerializer(many=True, read_only=True)
    class Meta:
        model = Module
        fields = ('id', 'name', 'parameter_specs')

class WfModuleSerializer(serializers.ModelSerializer):
    parameter_vals = ParameterValSerializer(many=True, read_only=True)
    module = ModuleSerializer(many=False, read_only=True)
    workflow = ModuleSerializer(many=False, read_only=True)
    class Meta:
        model = WfModule
        fields = ('id', 'order', 'module', 'workflow', 'parameter_vals')

class WorkflowSerializer(serializers.ModelSerializer):
    wf_modules = WfModuleSerializer(many=True, read_only=True)
    class Meta:
        model = Workflow
        fields = ('id', 'name', 'creation_date', 'wf_modules')