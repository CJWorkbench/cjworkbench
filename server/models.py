from django.db import models

# Create your models here.
from django.db import models

# A module contains a name (which is used to bind to the actual function that executes) and parameterSpecs
class Module(models.Model):
    name = models.CharField('name', max_length=200)

    def __str__(self):
        return self.name

# A parameter value, which might be string or float atm
class ParameterVal(models.Model):
    STRING = 'string'
    NUMERIC = 'number'
    TEXT = 'text'
    TYPE_CHOICES = (
        (STRING, 'String'),
        (NUMERIC, 'Number'),
        (TEXT, 'Text')          # long strings, e.g. programs
    )
    type = models.CharField(
        max_length=8,
        choices=TYPE_CHOICES,
        default=NUMERIC,
    )
    number = models.FloatField('number', null=True, blank=True)
    string = models.CharField('string', max_length=50, null=True, blank=True)
    text = models.TextField('text', null=True, blank=True)

    def __str__(self):
        if self.type == 'STR':
            return self.string
        elif self.type == 'NUM':
            return self.number
        else:
            return self.text


# Defines a parameter UI and defaults for a particular Module
class ParameterSpec(models.Model):
    name = models.CharField('name', max_length=32)
    module = models.ForeignKey(Module, related_name='parameter_specs', on_delete=models.CASCADE)  # delete spec if Module deleted
    default = models.ForeignKey(ParameterVal, on_delete=models.PROTECT)  # can't delete ParameterVal referenced by Spec

    def __str__(self):
        return self.name


# A Workflow is the user's "document," a series of Modules
class Workflow(models.Model):
    name = models.CharField('name',max_length=200)
    creation_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# WfModule is a Module that has been applied in a Workflow
class WfModule(models.Model):
    workflow = models.ForeignKey(Workflow, related_name='modules', on_delete=models.CASCADE)            # delete WfModule if Workflow deleted
    module = models.ForeignKey(Module, on_delete=models.SET_NULL, null=True)    # goes null if referenced Module deletedp
    parameters = models.ManyToManyField(ParameterVal)
    order = models.IntegerField('order')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.module.__str__() ## use name of underlying Module, for the moment


