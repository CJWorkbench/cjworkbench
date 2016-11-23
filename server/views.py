from django.shortcuts import render
from django.http import HttpResponse

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from server.models import Workflow
from server.serializers import WorkflowSerializer
from server.serializers import SimpleWorkflowSerializer


def index(request):
    return HttpResponse("Hello, world. You're at the workflow index. <a href=\"/admin\">Admin</a>")

def workflow(request, workflow_id):
    return HttpResponse("You're looking at workflow %s." % workflow_id)

def WfModule(request, wfmodule_id):
    response = "You're looking at the workflow module %s."
    return HttpResponse(response % wfmodule_id)


# List all workflows, or create a new workflow.
@api_view(['GET', 'POST'])
@renderer_classes((JSONRenderer,))
def workflow_list(request, format=None):
    renderer_classes = (JSONRenderer,)

    #print("\nFormat = " + str(format) + '\n')

    if request.method == 'GET':
        workflows = Workflow.objects.all()
        serializer = WorkflowSerializer(workflows, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = WorkflowSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Retrieve, update or delete a workflow instance.
@api_view(['GET', 'PATCH', 'DELETE'])
@renderer_classes((JSONRenderer,))
def workflow_detail(request, pk, format=None):
    try:
        workflow = Workflow.objects.get(pk=pk)
    except Workflow.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = WorkflowSerializer(workflow)
        return Response(serializer.data)

    # We use PATCH to set the order of the modules when the user drags
    elif request.method == 'PATCH':
        for record in request.data:
            wfm = workflow.modules.get(pk=record['id'])
            wfm.order = record['order']
            wfm.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    elif request.method == 'DELETE':
        workflow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

