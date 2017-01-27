# Utilities for testing, mostly around constructing test Workflows

from server.models import Module, Workflow

def add_new_workflow(name):
    workflow = Workflow(name=name)
    workflow.save()
    return workflow.id

def add_new_module(name):
    module = Module(name=name)
    module.save()
    return module.id