from rest_framework import serializers
from server.models import Workflow, WfModule, ParameterVal, ParameterSpec, Module

class ParameterValSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParameterVal
        fields = ('wf_module', 'parameter_specs', 'number', 'string', 'text')

class ParameterSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParameterSpec
        fields = ('name', 'type', 'module', 'default_number', 'default_string', 'default_text')

class ModuleSerializer(serializers.ModelSerializer):
    parameter_specs = ParameterSpecSerializer(many=True, read_only=True)
    class Meta:
        model = Module
        fields = ('name', 'parameter_specs')

class WfModuleSerializer(serializers.ModelSerializer):
    parameters = ParameterValSerializer(many=True, read_only=True)
    class Meta:
        model = WfModule
        fields = ('id', 'order', 'module', 'parameters')

class WorkflowSerializer(serializers.ModelSerializer):
    modules = WfModuleSerializer(many=True, read_only=True)
    class Meta:
        model = Workflow
        fields = ('id', 'name', 'creation_date', 'modules')