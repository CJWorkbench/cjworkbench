from django.db import models
from server.models.Workflow import *
from server.models.ModuleVersion import *

# ParameterSpec defines a parameter UI and defaults for a particular Module
class ParameterSpec(models.Model):
    class Meta:
        ordering = ['order']

    # constants
    STRING = 'string'
    NUMBER = 'number'
    CHECKBOX = 'checkbox'
    MENU = 'menu'               # menu like HTML <select>
    BUTTON = 'button'
    CUSTOM = 'custom'           # rendered in front end
    TYPE_CHOICES = (
        (STRING, 'String'),
        (NUMBER, 'Number'),
        (BUTTON, 'Button'),
        (CHECKBOX, 'Checkbox'),
        (MENU, 'Menu'),
        (CUSTOM, 'Custom')
    )

    # fields
    type = models.CharField(
        max_length=8,
        choices=TYPE_CHOICES,
        default=NUMBER,
    )

    name = models.CharField('name', max_length=64)
    id_name = models.CharField('id_name', max_length=32)

    module_version = models.ForeignKey(ModuleVersion, related_name='parameter_specs',
                               on_delete=models.CASCADE, null=True)  # delete spec if Module deleted

    order = models.IntegerField('order', default=0)

    def_string = models.TextField('string', null=True, blank=True, default='')
    def_float = models.FloatField('float', null=True, blank=True, default=0.0)
    def_boolean = models.NullBooleanField('boolean', null=True, blank=True, default=True)
    def_integer = models.IntegerField('integer', null=True, blank=True, default=0) # which item selected

    def_menu_items = models.TextField(MENU, null=True, blank=True)       # menu items here

    def_visible = models.BooleanField(default=True)

    # Flags which cannot be set on a per-instance basic
    ui_only = models.BooleanField(default=False)            # Don't bother pushing value to server
    multiline = models.BooleanField(default=False)          # for edit fields
    derived_data = models.BooleanField(default=False)       # Don't save in the undo stack, it comes from other params


    def __str__(self):
        return self.module_version.module.name + ' - ' + self.name