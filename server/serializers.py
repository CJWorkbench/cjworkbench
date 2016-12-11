from rest_framework import serializers
from server.models import Workflow, WfModule, ParameterVal, ParameterSpec, Module

class ParameterValSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParameterVal
        fields = ('type', 'number', 'string', 'text')

class ParameterSpecSerializer(serializers.ModelSerializer):
    defaultVal = ParameterValSerializer(many=False, read_only=True)
    class Meta:
        model = ParameterSpec
        fields = ('name', 'default')

class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ('id','name')

class WfModuleSerializer(serializers.ModelSerializer):
    module = ModuleSerializer(many=False, read_only=True)
    parameters = ParameterValSerializer(many=True, read_only=True)
    class Meta:
        model = WfModule
        fields = ('id', 'order', 'module', 'parameters')

class WorkflowSerializer(serializers.ModelSerializer):
    modules = WfModuleSerializer(many=True, read_only=True)
    class Meta:
        model = Workflow
        fields = ('id', 'name', 'modules')

