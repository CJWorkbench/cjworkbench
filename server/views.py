from django.shortcuts import render

from django.http import HttpResponse


def index(request):
    return HttpResponse("Hello, world. You're at the workflow index.")

def workflow(request, workflow_id):
    return HttpResponse("You're looking at workflow %s." % workflow_id)

def WfModule(request, wfmodule_id):
    response = "You're looking at the workflow module %s."
    return HttpResponse(response % wfmodule_id)


