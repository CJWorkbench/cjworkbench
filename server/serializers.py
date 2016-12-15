from rest_framework import serializers
from server.models import Workflow, WfModule, ParameterVal, ParameterSpec, Module

class ParameterSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParameterSpec
        fields = ('id', 'name', 'type', 'def_number', 'def_string', 'def_text')

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
    class Meta:
        model = WfModule
        fields = ('id', 'order', 'module', 'parameter_vals')

class WorkflowSerializer(serializers.ModelSerializer):
    wf_modules = WfModuleSerializer(many=True, read_only=True)
    class Meta:
        model = Workflow
        fields = ('id', 'name', 'creation_date', 'wf_modules')