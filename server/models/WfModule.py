# WfModule is a Module that has been applied in a Workflow
# We also have ParameterSpec and ParameterVal in this file, to avoid circular reference problems

from django.db import models
from server.models.Module import *
from server.models.Workflow import *

class WfModule(models.Model):
    workflow = models.ForeignKey(Workflow, related_name='wf_modules',
                                 on_delete=models.CASCADE)  # delete WfModule if Workflow deleted
    module = models.ForeignKey(Module, related_name='wf_modules',
                               on_delete=models.SET_NULL,
                               null=True)  # goes null if referenced Module deletedp
    order = models.IntegerField('order')

    # status light and current error message
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    TYPE_CHOICES = (
        (READY, 'Ready'),
        (BUSY, 'Busy'),
        (ERROR, 'Error')
    )
    status = models.CharField(
        max_length=8,
        choices=TYPE_CHOICES,
        default=READY,
    )
    error_msg = models.CharField('error_msg', max_length=200, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.workflow.__str__() + ' - order: ' + str(self.order) + ' - ' + self.module.__str__()

    # Hydrates ParameterVal objects from ParameterSpec objects
    def create_default_parameters(self):
        for pspec in ParameterSpec.objects.filter(module=self.module):
            pv = ParameterVal.objects.create(wf_module=self, parameter_spec=pspec)
            pv.init_from_spec()
            pv.save()

    # Retrieve current parameter values
    def get_param_typecheck(self, name, param_type):
        pspec = ParameterSpec.objects.get(module=self.module, name=name)
        if pspec.type != param_type:
            raise ValueError('Request for ' + param_type + ' parameter ' + name + ' but actual type is ' + pspec.type)
        pval = ParameterVal.objects.get(wf_module=self, parameter_spec=pspec)
        if param_type == ParameterSpec.STRING:
            return pval.string
        elif param_type == ParameterSpec.NUMBER:
            return pval.number
        else:
            return pval.text

    def get_param_string(self, name):
        return self.get_param_typecheck(name, ParameterSpec.STRING)

    def get_param_number(self, name):
        return self.get_param_typecheck(name, ParameterSpec.NUMBER)

    def get_param_text(self, name):
        return self.get_param_typecheck(name, ParameterSpec.TEXT)

    # Modules ingest and emit a table (though may do only one, if source or sink)
    def execute(self, table):
        return module_dispatch[self.module.dispatch](self, table)


# ParameterSpec defines a parameter UI and defaults for a particular Module
class ParameterSpec(models.Model):
    # constants
    STRING = 'string'
    NUMBER = 'number'
    TEXT = 'text'               # long strings, e.g. programs
    BUTTON = 'button'
    TYPE_CHOICES = (
        (STRING, 'String'),
        (NUMBER, 'Number'),
        (TEXT, 'Text'),
        (BUTTON, 'Button')
    )

    # fields
    type = models.CharField(
        max_length=8,
        choices=TYPE_CHOICES,
        default=NUMBER,
    )

    name = models.CharField('name', max_length=64)
    id_name = models.CharField('name', max_length=32)

    module = models.ForeignKey(Module, related_name='parameter_specs',
                               on_delete=models.CASCADE)  # delete spec if Module deleted

    def_number = models.FloatField(NUMBER, null=True, blank=True, default=0.0)
    def_string = models.CharField(STRING, max_length=50, blank=True, default='')
    def_text = models.TextField(TEXT, blank=True, default='')

    def __str__(self):
        return self.module.name + ' - ' + self.name


# A parameter value, which might be string or float
class ParameterVal(models.Model):
    number = models.FloatField(ParameterSpec.NUMBER, null=True, blank=True)
    string = models.CharField(ParameterSpec.STRING, max_length=50, null=True, blank=True)
    text = models.TextField(ParameterSpec.TEXT, null=True, blank=True)

    wf_module = models.ForeignKey(WfModule, related_name='parameter_vals',
                               on_delete=models.CASCADE, null=True)  # delete value if Module deleted
    parameter_spec = models.ForeignKey(ParameterSpec, related_name='parameter_vals',
                               on_delete=models.CASCADE, null=True)  # delete value if Spec deleted

    def init_from_spec(self):
        self.number = self.parameter_spec.def_number
        self.string = self.parameter_spec.def_string
        self.text = self.parameter_spec.def_text

    def __str__(self):
        if self.parameter_spec.type == ParameterSpec.STRING:
            return self.wf_module.__str__() + ' - ' + self.parameter_spec.name + ' - ' + self.string
        elif self.parameter_spec.type == ParameterSpec.NUMBER:
            return self.wf_module.__str__() + ' - ' + self.parameter_spec.name + ' - ' + str(self.number)
        elif self.parameter_spec.type == ParameterSpec.TEXT:
            return self.wf_module.__str__() + ' - ' + self.parameter_spec.name + ' - ' + self.text
        elif self.parameter_spec.type == ParameterSpec.BUTTON:
            return self.wf_module.__str__() + ' - ' + self.parameter_spec.name + ' - button'
        else:
            raise ValueError("Invalid parameter type")
