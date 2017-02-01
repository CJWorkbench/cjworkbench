# Utilities for testing, mostly around constructing test Workflows

from server.models import Module, Workflow, WfModule

def add_new_workflow(name):
    return Workflow.objects.create(name=name)

def add_new_module(name):
    return Module.objects.create(name=name)

def add_new_wf_module(module, workflow, order=1):
    return WfModule.objects.create(workflow=workflow, module=module, order=order)
