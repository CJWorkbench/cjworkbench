import json
from django.db import models
from server.models.ModuleVersion import ModuleVersion


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

    type = models.CharField(max_length=16, choices=TYPE_CHOICES,
                            default=STRING)

    # user-visible
    name = models.CharField('name', max_length=256)

    # unique to this Module
    id_name = models.CharField('id_name', max_length=200)

    # delete spec if Module deleted
    module_version = models.ForeignKey(ModuleVersion,
                                       related_name='parameter_specs',
                                       on_delete=models.CASCADE, null=True)

    # relative to other parameters
    order = models.IntegerField('order', default=0)

    # Flags which can be set per-instance
    # string representation, will be cast to field via setvalue
    def_value = models.TextField(blank=True, default='')
    # initial menu and radio items here
    def_items = models.TextField(null=True, blank=True)

    # Flags which cannot be set on a per-instance basis
    # For edit fields
    multiline = models.BooleanField(default=False)
    # Placeholder/help text. Different from default in that it's not actually a
    # value.
    placeholder = models.TextField(blank=True, default='')

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
            if value is None:
                return ''
            else:
                return str(value)

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
                # Be permissive, allow both actual booleans and "true"/"false"
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
            try:
                return int(s)
            except ValueError:
                return 0

        elif self.type == ParameterSpec.FLOAT:
            try:
                return float(s)
            except ValueError:
                return 0.0

        elif self.type == ParameterSpec.CHECKBOX:
            return s == 'True'

        elif self.type == ParameterSpec.SECRET:
            if s:
                parsed = json.loads(s)
                return {'name': parsed['name']}
            else:
                return None

        else:
            raise ValueError(
                f'Unknown type {self.type} for parameter {self.id_name}'
            )
