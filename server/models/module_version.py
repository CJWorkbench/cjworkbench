# ModuleVersion is an id_name plus the code that goes along with it. We store
# multiple _versions_ of its code, but users can only access the latest
# version.

import os
import jsonschema
import yaml
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, OuterRef, Subquery
from .param_field import ParamField, ParamDType


_SpecPath = os.path.join(os.path.dirname(__file__), 'module_spec_schema.yaml')
with open(_SpecPath, 'rt') as spec_file:
    _SpecSchema = yaml.load(spec_file)
_validator = jsonschema.Draft7Validator(
    _SpecSchema,
    format_checker=jsonschema.FormatChecker()
)


def validate_module_spec(spec):
    """
    Validate that the spec is valid.

    Raise ValidationError otherwise.

    "Valid" means:

    * `spec` adheres to `server/models/module_spec_schema.yaml`
    * `spec.parameters[*].id_name` are unique
    * `spec.parameters[*].menu_items` or `.radio_items` are present if needed
    * `spec.parameters[*].visible_if[*].id_name` are valid
    """
    # No need to do i18n on these errors: they're only for admins. Good thing,
    # too -- most of the error messages come from jsonschema, and there are
    # _plenty_ of potential messages there.
    messages = []

    for err in _validator.iter_errors(spec):
        messages.append(err.message)
    if messages:
        # Don't bother validating the rest. The rest of this method assumes
        # the schema is valid.
        raise ValidationError(messages)

    param_id_names = set()
    for param in spec['parameters']:
        id_name = param['id_name']

        if id_name in param_id_names:
            messages.append(f"Param '{id_name}' appears twice")
        else:
            param_id_names.add(id_name)

        if param['type'] == 'menu' and not param.get('menu_items', ''):
            messages.append(f"Param '{id_name}' needs menu_items")
        if param['type'] == 'radio' and not param.get('radio_items', ''):
            messages.append(f"Param '{id_name}' needs radio_items")

    # Now that param_id_names is full, loop again to check visible_if refs
    for param in spec['parameters']:
        try:
            visible_if = param['visible_if']
        except KeyError:
            continue

        if visible_if['id_name'] not in param_id_names:
            param_id_name = param['id_name']
            ref_id_name = visible_if['id_name']
            messages.append(
                f"Param '{param_id_name}' has visible_if "
                f"id_name '{ref_id_name}', which does not exist",
            )

    if messages:
        raise ValidationError(messages)


class ModuleVersionManager(models.Manager):
    def all_latest(self):
        # https://docs.djangoproject.com/en/1.11/ref/models/expressions/#subquery-expressions
        latest = (
            self.get_queryset()
            .filter(id_name=OuterRef('id_name'))
            .order_by('-last_update_time')
            .values('id')
        )[:1]
        return (
            self.get_queryset()
            .annotate(_latest=Subquery(latest))
            .filter(id=F('_latest'))
        )

    def latest(self, id_name):
        try:
            return (
                self.get_queryset()
                .filter(id_name=id_name)
                .order_by('-last_update_time')
            )[0]
        except IndexError:
            raise ModuleVersion.DoesNotExist


class ModuleVersion(models.Model):
    class Meta:
        ordering = ['last_update_time']

        unique_together = ('id_name', 'last_update_time')

    objects = ModuleVersionManager()

    id_name = models.CharField(max_length=200)

    # which version of this module are we currently at (based on the source)?
    source_version_hash = models.CharField(max_length=200, default='1.0')

    # time this module was last updated
    last_update_time = models.DateTimeField(auto_now=True)

    spec = JSONField('spec', validators=[validate_module_spec])

    js_module = models.TextField('js_module', default='')

    @staticmethod
    def create_or_replace_from_spec(spec, *, source_version_hash='',
                                    js_module='') -> 'ModuleVersion':
        validate_module_spec(spec)  # raises ValidationError

        module_version, _ = ModuleVersion.objects.update_or_create(
            id_name=spec['id_name'],
            source_version_hash=source_version_hash,
            defaults={
                'spec': spec,
                'js_module': js_module,
            }
        )

        return module_version

    @property
    def name(self):
        return self.spec['name']

    @property
    def category(self):
        return self.spec['category']

    @property
    def description(self):
        return self.spec.get('description', '')

    @property
    def author(self):
        return self.spec.get('author', 'Workbench')

    @property
    def link(self):
        return self.spec.get('link', '')

    @property
    def icon(self):
        return self.spec.get('icon', 'url')

    @property
    def loads_data(self):
        return self.spec.get('loads_data', False)

    @property
    def has_zen_mode(self):
        return self.spec.get('has_zen_mode', False)

    @property
    def help_url(self):
        return self.spec.get('help_url', '')

    @property
    def row_action_menu_entry_title(self):
        return self.spec.get('row_action_menu_entry_title', '')

    @property
    def html_output(self):
        return self.spec.get('html_output', False)

    @property
    def param_fields(self):
        return [ParamField.from_dict(d) for d in self.spec['parameters']]

    @property
    def param_schema(self):
        try:
            json_schema = self.spec['param_schema']
        except KeyError:
            return ParamDType.Dict(dict((f.id_name, f.dtype)
                                        for f in self.param_fields
                                        if f.dtype is not None))

        return ParamDType.parse({
            'type': 'dict',
            'properties': json_schema
        })

    @property
    def default_params(self):
        return self.param_schema.coerce(None)

    def __str__(self):
        return '%s#%s' % (self.id_name, self.source_version_hash)
