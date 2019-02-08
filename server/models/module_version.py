import os
import json
import jsonschema
import yaml
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, OuterRef, Subquery
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from .param_field import ParamField, ParamDType
from server import minio
from server.modules import SpecPaths as InternalModuleSpecPaths


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

    param_id_types = {}
    for param in spec['parameters']:
        id_name = param['id_name']

        if id_name in param_id_types:
            messages.append(f"Param '{id_name}' appears twice")
        else:
            param_id_types[id_name] = param['type']

    # Now that param_id_types is full, loop again to check visible_if refs
    for param in spec['parameters']:
        try:
            visible_if = param['visible_if']
        except KeyError:
            continue

        if visible_if['id_name'] not in param_id_types:
            param_id_name = param['id_name']
            ref_id_name = visible_if['id_name']
            messages.append(
                f"Param '{param_id_name}' has visible_if "
                f"id_name '{ref_id_name}', which does not exist",
            )

    # Now that param_id_types is full, loop again to check tab_parameter refs
    for param in spec['parameters']:
        try:
            tab_parameter = param['tab_parameter']
        except KeyError:
            continue  # we aren't referencing a "tab" parameter

        param_id_name = param['id_name']
        if tab_parameter not in param_id_types:
            messages.append(
                f"Param '{param_id_name}' has a 'tab_parameter' "
                "that is not in 'parameters'"
            )
        elif param_id_types[tab_parameter] != 'tab':
            messages.append(
                f"Param '{param_id_name}' has a 'tab_parameter' "
                "that is not a 'tab'"
            )

    if messages:
        raise ValidationError(messages)


class ModuleVersionManager(models.Manager):
    """
    Juggle internal and external modules.

    _Internal_ modules are defined by source code: they do not change while the
    program is running. Edit them in `server/modules/` and load the new
    versions by restarting Workbench.

    _External_ modules are in the database. Upload a directory to S3 and create
    a matching ModuleVersion database object to create them; then they can be
    queried through the Django object manager.

    `.get_all_latest()` and `.latest(id_name)` are the shortcuts to list and
    get modules, regardless of whether they're internal or external. (Internal
    modules take precedence.)
    """

    def __init__(self):
        super().__init__()

        # We can't load self.internal right here, because we're called before
        # ModuleVersion is defined and self.internal is a dict from id_name to
        # ModuleVersion.
        self.internal = None

    def _ensure_internal_loaded(self):
        # Pre-load all internal modules on first access. Raise error if a
        # module is buggy.
        if self.internal is not None:
            return

        self.internal = {}
        for spec_path in InternalModuleSpecPaths:
            with spec_path.open('rb') as spec_file:
                spec = json.load(spec_file)  # raises ValueError
            validate_module_spec(spec)
            module_version = ModuleVersion(
                id_name=spec['id_name'],
                source_version_hash='internal',
                spec=spec,
                last_update_time=timezone.now()
            )
            self.internal[module_version.id_name] = module_version

    def get_all_latest(self):
        self._ensure_internal_loaded()

        # https://docs.djangoproject.com/en/1.11/ref/models/expressions/#subquery-expressions
        latest = (
            self.get_queryset()
            .filter(id_name=OuterRef('id_name'))
            .order_by('-last_update_time')
            .values('id')
        )[:1]
        all_external = list(
            self.get_queryset()
            .annotate(_latest=Subquery(latest))
            .filter(id=F('_latest'))
            .exclude(id_name__in=self.internal.keys())
        )
        all_internal = list(self.internal.values())
        both = all_internal + all_external
        return sorted(both, key=lambda mv: mv.last_update_time, reverse=True)

    def latest(self, id_name):
        self._ensure_internal_loaded()

        try:
            return self.internal[id_name]
        except KeyError:
            pass

        try:
            return (
                self.get_queryset()
                .filter(id_name=id_name)
                .order_by('-last_update_time')
            )[0]
        except IndexError:
            raise ModuleVersion.DoesNotExist


class ModuleVersion(models.Model):
    """
    An (id_name, version) pair and all its logic.

    There are two main parts to a (id_name, version) pair: a database record
    and code. This class, ModuleVersion, is the database record. The code is in
    S3 or our repository, and it's handled by LoadedModule.
    """

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


@receiver(post_delete, sender=ModuleVersion)
def _delete_from_s3_post_delete(sender, instance, **kwargs):
    """
    Delete module _code_ from S3, now that ModuleVersion is gone.
    """
    prefix = '%s/%s/' % (sender.id_name, sender.source_version_hash)
    minio.remove_recursive(minio.ExternalModulesBucket, prefix)
