# Utilities for testing, mostly around constructing test Workflows

from server.models import Module, Workflow

def add_new_workflow(name):
    workflow = Workflow(name=name)
    workflow.save()
    return workflow

def add_new_module(name):
    module = Module(name=name)
    module.save()
    return module

def add_new_wf_module(module, workflow, order=1):
    wf_module = WfModule(workflow=workflow, module=module, order=order)
    wf_module.save()
    return wf_module