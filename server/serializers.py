from rest_framework import serializers
from server.models import Workflow, WfModule, ParameterVal, ParameterSpec, Module

class ParameterValSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParameterVal
        fields = ('type', 'numVal', 'strVal')

class ParameterSpecSerializer(serializers.ModelSerializer):
    defaultVal = ParameterValSerializer(many=False, read_only=True)
    class Meta:
        model = ParameterSpec
        fields = ('name', 'defaultVal')

class ModuleSerializer(serializers.ModelSerializer):
    parameterSpecs = ParameterSpecSerializer(many=True, read_only=True)
    class Meta:
        model = Module
        fields = ('name', 'parameterSpecs')

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

