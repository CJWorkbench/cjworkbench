from rest_framework import serializers
from server.models import Workflow, WfModule


class WorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = ('id', 'name')