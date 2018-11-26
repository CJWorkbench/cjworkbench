import json
from django.db import models
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
    RADIO = 'radio'
    MULTICOLUMN = 'multicolumn'
    SECRET = 'secret'
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
        (RADIO, 'Radio'),
        (SECRET, 'Secret'),
        (CUSTOM, 'Custom'),
    )

    TYPES = [x[0] for x in TYPE_CHOICES]


    # fields
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=STRING)

    name = models.CharField('name', max_length=256)          # user-visible
    id_name = models.CharField('id_name', max_length=200)    # unique to this Module

    module_version = models.ForeignKey(ModuleVersion, related_name='parameter_specs',
                               on_delete=models.CASCADE, null=True)  # delete spec if Module deleted

    order = models.IntegerField('order', default=0)         # relative to other parameters

    def_value = models.TextField(blank=True, default='')    # string representation, will be cast to field via setvalue
    def_items = models.TextField(null=True, blank=True)     # initial menu and radio items here

    # Flags which can be set per-instance
    def_visible = models.BooleanField(default=True)         # Displayed in UI?

    # Flags which cannot be set on a per-instance basis
    ui_only = models.BooleanField(default=False)            # Don't bother pushing value to server
    multiline = models.BooleanField(default=False)          # For edit fields
    placeholder = models.TextField(blank=True, default='')  # Placeholder/help text. Different from default in that it's not actually a value.

    # Conditional UI
    visible_if = models.TextField('visible_if', default='')

    def __str__(self):
        return self.module_version.module.name + ' - ' + self.name

    def value_to_str(self, value):
        if (
            self.type == ParameterSpec.STRING
            or self.type == ParameterSpec.COLUMN
            or self.type == ParameterSpec.MULTICOLUMN
            or self.type == ParameterSpec.CUSTOM
            or self.type == ParameterSpec.BUTTON
            or self.type == ParameterSpec.STATICTEXT
        ):
            return value

        elif (
            self.type == ParameterSpec.INTEGER
            or self.type == ParameterSpec.MENU
            or self.type == ParameterSpec.RADIO
        ):
            try:
                return str(int(value))
            except (ValueError, TypeError):
                return '0'

        elif self.type == ParameterSpec.FLOAT:
            try:
                return str(float(value))
            except (ValueError, TypeError):
                return '0.0'

        elif self.type == ParameterSpec.CHECKBOX:
            try:
                # Be permissive, allow both actual booleans and "true"/"false" strings
                if type(value) is bool:
                    return str(value)
                elif type(value) is str:
                    return str(value.lower().strip() == 'true')
                else:
                    return str(bool(value))  # we catch number types here
            except ValueError:
                return 'False'

        elif self.type == ParameterSpec.SECRET:
            if not value:
                return ''
            else:
                if (
                    type(value) is not dict
                    or type(value.get('name')) is not str
                    or not value.get('name')
                    or not value.get('secret')
                ):
                    raise ValueError(
                        f'SECRET parameter {self.id_name} must be a dict with '
                        f'str "name": "..." and non-empty "secret"'
                    )
                return json.dumps(value)

        else:
            raise ValueError(
                f'Unknown type {self.type} for parameter {self.id_name}'
            )

    def str_to_value(self, s):
        if (
            self.type == ParameterSpec.STRING
            or self.type == ParameterSpec.COLUMN
            or self.type == ParameterSpec.MULTICOLUMN
            or self.type == ParameterSpec.CUSTOM
            or self.type == ParameterSpec.BUTTON
            or self.type == ParameterSpec.STATICTEXT
        ):
            return s

        elif (
            self.type == ParameterSpec.INTEGER
            or self.type == ParameterSpec.MENU
            or self.type == ParameterSpec.RADIO
        ):
            if s == '':
                return 0
            else:
                return int(s)

        elif self.type == ParameterSpec.FLOAT:
            if s == '':
                return 0.0
            else:
                return float(s)

        elif self.type == ParameterSpec.CHECKBOX:
            return s == 'True'

        elif self.type == ParameterSpec.SECRET:
            if s:
                parsed = json.loads(s)
                return { 'name': parsed['name'] }
            else:
                return None

        else:
            raise ValueError(
                f'Unknown type {self.type} for parameter {self.id_name}'
            )
