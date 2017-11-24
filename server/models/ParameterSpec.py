from django.db import models
from server.models.Workflow import *
from server.models.ModuleVersion import *

# ParameterSpec defines a parameter UI and defaults for a particular Module
class ParameterSpec(models.Model):
    class Meta:
        ordering = ['order']

    # Type constants
    STATICTEXT = 'statictext'
    STRING = 'string'
    INTEGER = 'integer'
    FLOAT = 'float'
    CHECKBOX = 'checkbox'
    MENU = 'menu'               # menu like HTML <select>
    BUTTON = 'button'
    COLUMN = 'column'
    MULTICOLUMN = 'multicolumn'
    CUSTOM = 'custom'           # rendered in front end

    TYPE_CHOICES = (
        (STATICTEXT, 'Statictext'),
        (STRING, 'String'),
        (INTEGER, 'Integer'),
        (FLOAT, 'Float'),
        (BUTTON, 'Button'),
        (CHECKBOX, 'Checkbox'),
        (MENU, 'Menu'),
        (COLUMN, 'Column'),
        (MULTICOLUMN, 'Multiple columns'),
        (CUSTOM, 'Custom')
    )

    TYPES = [x[0] for x in TYPE_CHOICES]


    # fields
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=STRING)

    name = models.CharField('name', max_length=256)          # user-visible
    id_name = models.CharField('id_name', max_length=32)    # unique to this Module

    module_version = models.ForeignKey(ModuleVersion, related_name='parameter_specs',
                               on_delete=models.CASCADE, null=True)  # delete spec if Module deleted

    order = models.IntegerField('order', default=0)         # relative to other parameters

    def_value = models.TextField(blank=True, default='')    # string representation, will be cast to field via setvalue
    def_menu_items = models.TextField(null=True, blank=True)  # initial menu items here

    # Flags which can be set per-instance
    def_visible = models.BooleanField(default=True)         # Displayed in UI?

    # Flags which cannot be set on a per-instance basis
    ui_only = models.BooleanField(default=False)            # Don't bother pushing value to server
    multiline = models.BooleanField(default=False)          # For edit fields
    derived_data = models.BooleanField(default=False)       # Don't save in the undo stack, it comes from other params


    def __str__(self):
        return self.module_version.module.name + ' - ' + self.name
