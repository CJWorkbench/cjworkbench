from django.db import models

# Create your models here.
from django.db import models


# A parameter value, which might be string or float atm
class ParameterVal(models.Model):
    STRING = 'STR'
    NUMERIC = 'NUM'
    TYPE_CHOICES = (
        (STRING, 'String'),
        (NUMERIC, 'Numeric'),
    )
    type = models.CharField(
        max_length=3,
        choices=TYPE_CHOICES,
        default=NUMERIC,
    )
    numDefaultVal = models.FloatField('numVal')
    strVal = models.CharField('strVal', max_length=20, blank=True)


# Defines a parameter UI and defaults for a particular Module
class ParameterSpec(models.Model):
    name = models.CharField('name', max_length=32)
    defaultVal = models.ForeignKey(ParameterVal, on_delete=models.PROTECT)  # can't delete ParameterVal referenced by Spec

    def __str__(self):
        return self.name


# A module contains a name (which is used to bind to the actual function that executes) and parameterSpecs
class Module(models.Model):
    name = models.CharField('name', max_length=200)
    parameterSpecs = models.ManyToManyField(ParameterSpec)

    def __str__(self):
        return self.name

# A Workflow is the user's "document," a series of Modules
class Workflow(models.Model):
    name = models.CharField('name',max_length=200)
    creation_date = models.DateTimeField(auto_now_add=True)

    modules = models.ManyToManyField('WfModule')  # quotes to resolve circular reference

    def __str__(self):
        return self.name

# WfModule is a Module that has been applied in a Workflow
class WfModule(models.Model):
    module = models.ForeignKey(Module, on_delete=models.SET_NULL, null=True)    # goes null if referenced Module disappears
    parameters = models.ManyToManyField(ParameterVal)

    def __str__(self):
        return self.module.__str__() ## use name of underlying Module, for the moment


