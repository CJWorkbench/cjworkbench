from typing import Any

from cjwmodule.spec.loader import load_spec
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from cjwstate import s3


def _django_validate_module_spec(spec: Any) -> None:
    try:
        load_spec(spec)
    except ValueError as err:
        raise ValidationError(str(err))


class ModuleVersion(models.Model):
    """
    An (id_name, version) pair and all its logic.

    There are two main parts to a (id_name, version) pair: a database record
    and code. This class, ModuleVersion, is the database record. The code is in
    S3 or our repository, and it's handled by LoadedModule.
    """

    class Meta:
        app_label = "server"
        db_table = "module_version"
        ordering = ["last_update_time"]
        unique_together = ("id_name", "last_update_time")

    id_name = models.CharField(max_length=200)

    # which version of this module are we currently at (based on the source)?
    source_version_hash = models.CharField(max_length=200, default="1.0")

    # time this module was last updated
    last_update_time = models.DateTimeField(auto_now=True)

    spec = models.JSONField("spec", validators=[_django_validate_module_spec])

    js_module = models.TextField("js_module", default="")

    def __str__(self):
        return "%s#%s" % (self.id_name, self.source_version_hash)


@receiver(post_delete, sender=ModuleVersion)
def _delete_from_s3_post_delete(sender, instance, **kwargs):
    """
    Delete module _code_ from S3, now that ModuleVersion is gone.
    """
    prefix = "%s/%s/" % (sender.id_name, sender.source_version_hash)
    s3.remove_recursive(s3.ExternalModulesBucket, prefix)
