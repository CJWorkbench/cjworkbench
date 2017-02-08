# Utilities for testing, mostly around constructing test Workflows

from server.models import Module, Workflow, WfModule, ParameterSpec

def add_new_module(name, dispatch=''):
    return Module.objects.create(name=name, dispatch=dispatch)

def add_new_parameter_spec(module, id_name, type, order=0):
    return ParameterSpec.objects.create(module=module, id_name=id_name, type=type, order=order)

def add_new_workflow(name):
    return Workflow.objects.create(name=name)

def add_new_wf_module(workflow, module, order=1):
    return WfModule.objects.create(workflow=workflow, module=module, order=order)

# Encodes a DataFrame to the expected response format form render API
def table_to_content(table):
    return table.reset_index().to_json(orient='records').encode('UTF=8')