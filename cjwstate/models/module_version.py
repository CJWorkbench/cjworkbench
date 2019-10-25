from typing import Any, Dict, List, Optional
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, OuterRef, Subquery
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from cjwkernel.param_dtype import ParamDType
from cjwstate import minio
from cjwstate.modules.module_loader import validate_module_spec
import cjwstate.modules.staticregistry
from .param_spec import ParamSpec


def _django_validate_module_spec(spec: Any) -> None:
    try:
        validate_module_spec(spec)
    except ValueError as err:
        raise ValidationError(str(err))


class ModuleVersionManager(models.Manager):
    """
    Juggle internal and external modules.

    _Internal_ modules are defined by source code: they do not change while the
    program is running. Edit them in `staticmodules/` and load the new
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

        for spec in cjwstate.modules.staticregistry.Specs.values():
            module_version = ModuleVersion(
                id_name=spec.id_name,
                source_version_hash="internal",
                spec=spec,
                last_update_time=timezone.now(),
            )
            self.internal[spec.id_name] = module_version

    def get_all_latest(self):
        self._ensure_internal_loaded()

        # https://docs.djangoproject.com/en/1.11/ref/models/expressions/#subquery-expressions
        latest = (
            self.get_queryset()
            .filter(id_name=OuterRef("id_name"))
            .order_by("-last_update_time")
            .values("id")
        )[:1]
        all_external = list(
            self.get_queryset()
            .annotate(_latest=Subquery(latest))
            .filter(id=F("_latest"))
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
                .order_by("-last_update_time")
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
        app_label = "server"
        db_table = "server_moduleversion"
        ordering = ["last_update_time"]
        unique_together = ("id_name", "last_update_time")

    objects = ModuleVersionManager()

    id_name = models.CharField(max_length=200)

    # which version of this module are we currently at (based on the source)?
    source_version_hash = models.CharField(max_length=200, default="1.0")

    # time this module was last updated
    last_update_time = models.DateTimeField(auto_now=True)

    spec = JSONField("spec", validators=[_django_validate_module_spec])

    js_module = models.TextField("js_module", default="")

    @staticmethod
    def create_or_replace_from_spec(
        spec, *, source_version_hash="", js_module=""
    ) -> "ModuleVersion":
        validate_module_spec(dict(spec))  # raises ValueError

        module_version, _ = ModuleVersion.objects.update_or_create(
            id_name=spec["id_name"],
            source_version_hash=source_version_hash,
            defaults={"spec": dict(spec), "js_module": js_module},
        )

        return module_version

    @property
    def name(self):
        return self.spec["name"]

    @property
    def category(self):
        return self.spec["category"]

    @property
    def description(self):
        return self.spec.get("description", "")

    @property
    def icon(self):
        return self.spec.get("icon", "url")

    @property
    def deprecated(self) -> Optional[Dict[str, str]]:
        return self.spec.get("deprecated")

    @property
    def loads_data(self):
        return self.spec.get("loads_data", False)

    @property
    def uses_data(self):
        return self.spec.get("uses_data", not self.loads_data)

    @property
    def has_zen_mode(self):
        return self.spec.get("has_zen_mode", False)

    @property
    def help_url(self):
        return self.spec.get("help_url", "")

    @property
    def row_action_menu_entry_title(self):
        return self.spec.get("row_action_menu_entry_title", "")

    @property
    def html_output(self):
        return self.spec.get("html_output", False)

    @property
    def param_fields(self) -> List[ParamSpec]:
        return [ParamSpec.from_dict(d) for d in self.spec["parameters"]]

    # Returns a dict of DTypes for all parameters
    @property
    def param_schema(self) -> ParamDType.Dict:
        if "param_schema" in self.spec:
            # Module author wrote a schema in the YAML, to define storage of 'custom' parameters
            json_schema = self.spec["param_schema"]
            return ParamDType.parse({"type": "dict", "properties": json_schema})
        else:
            # Usual case: infer schema from module parameter types
            # Use of dict here means schema is not sensitive to parameter ordering, which is good
            return ParamDType.Dict(
                dict(
                    (f.id_name, f.dtype)
                    for f in self.param_fields
                    if f.dtype is not None
                )
            )

    @property
    def default_params(self) -> Dict[str, Any]:
        return self.param_schema.coerce(None)

    @property
    def param_schema_version(self) -> str:
        """
        Version of param_schema. Changes whenever param_schema changes.

        This is used in caching: if params were cached under
        param_schema_version=v1 and now the module has param_schema_version=v2,
        then we must call the module's migrate_params() on the params.
        """
        if self.source_version_hash == "internal":
            return "v%d" % self.spec["parameters_version"]
        else:
            return self.source_version_hash

    def __str__(self):
        return "%s#%s" % (self.id_name, self.source_version_hash)


@receiver(post_delete, sender=ModuleVersion)
def _delete_from_s3_post_delete(sender, instance, **kwargs):
    """
    Delete module _code_ from S3, now that ModuleVersion is gone.
    """
    prefix = "%s/%s/" % (sender.id_name, sender.source_version_hash)
    minio.remove_recursive(minio.ExternalModulesBucket, prefix)
