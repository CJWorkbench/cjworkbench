# Create your models here.
from django.db import models
from server.dispatch import module_dispatch

# A Workflow is the user's "document," a series of Modules
class Workflow(models.Model):
    name = models.CharField('name',max_length=200)
    creation_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Module(models.Model):
    # UI name, can change
    name = models.CharField('name', max_length=200)

    # internal name, cannot change if you want backwards compatibility with exported workflows
    internal_name = models.CharField('internal_name', max_length=200)

    # how do we run this module?
    dispatch = models.CharField('dispatch', max_length=200)

    def __str__(self):
        return self.name

# WfModule is a Module that has been applied in a Workflow
class WfModule(models.Model):
    workflow = models.ForeignKey(Workflow, related_name='wf_modules',
                                 on_delete=models.CASCADE)  # delete WfModule if Workflow deleted
    module = models.ForeignKey(Module, related_name='wf_modules',
                               on_delete=models.SET_NULL,
                               null=True)  # goes null if referenced Module deletedp
    order = models.IntegerField('order')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.workflow.__str__() + ' - order: ' + str(self.order) + ' - ' + self.module.__str__()

    # Hydrates ParameterVal objects from ParameterSpec objects
    def create_default_parameters(self):
        for pspec in ParameterSpec.objects.filter(module=self.module):
            pv = ParameterVal.objects.create(wf_module=self, \
                                             parameter_spec=pspec, \
                                             number=pspec.def_number, \
                                             string=pspec.def_string, \
                                             text=pspec.def_text)
            pv.save()

    # Retrieve current parameter values
    def get_param_string(self, name):
        pspec = ParameterSpec.objects.get(module=self.module, name="URL")
        if pspec.type != ParameterSpec.STRING:
            raise ValueError("Request for STRING parameter " + name + " but actual type is " + pspec.type)
        pval = ParameterVal.objects.get(wf_module=self, parameter_spec=pspec)
        return pval.string

    # Modules ingest and emit a table (though may do only one, if source or sink)
    def execute(self, table):
        return module_dispatch[self.module.dispatch](self, table)


# Defines a parameter UI and defaults for a particular Module
class ParameterSpec(models.Model):
    # constants
    STRING = 'string'
    NUMERIC = 'number'
    TEXT = 'text'               # long strings, e.g. programs
    TYPE_CHOICES = (
        (STRING, 'String'),
        (NUMERIC, 'Number'),
        (TEXT, 'Text')          #
    )

    # fields
    type = models.CharField(
        max_length=8,
        choices=TYPE_CHOICES,
        default=NUMERIC,
    )

    name = models.CharField('name', max_length=32)

    module = models.ForeignKey(Module, related_name='parameter_specs',
                               on_delete=models.CASCADE)  # delete spec if Module deleted

    def_number = models.FloatField('number', null=True, blank=True)
    def_string = models.CharField('string', max_length=50, null=True, blank=True)
    def_text = models.TextField('text', null=True, blank=True)

    def __str__(self):
        return self.module.name + ' - ' + self.name


# A parameter value, which might be string or float atm
class ParameterVal(models.Model):
    number = models.FloatField('number', null=True, blank=True)
    string = models.CharField('string', max_length=50, null=True, blank=True)
    text = models.TextField('text', null=True, blank=True)

    wf_module = models.ForeignKey(WfModule, related_name='parameter_vals',
                               on_delete=models.CASCADE, null=True)  # delete spec if Module deleted
    parameter_spec = models.ForeignKey(ParameterSpec, related_name='parameter_vals',
                               on_delete=models.CASCADE, null=True)  # delete spec if Module deleted

    def __str__(self):
        if self.parameter_spec.type == 'string':
            return self.wf_module.__str__() + ' - ' + self.parameter_spec.name + ' - ' + self.string
        elif self.parameter_spec.type == 'number':
            return self.wf_module.__str__() + ' - ' + self.parameter_spec.name + ' - ' + str(self.number)
        else:
            return self.wf_module.__str__() + ' - ' + self.parameter_spec.name + ' - ' + self.text