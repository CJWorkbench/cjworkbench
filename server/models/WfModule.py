# WfModule is a Module that has been applied in a Workflow
# We also have ParameterSpec and ParameterVal in this file, to avoid circular reference problems

from django.db import models
import pandas as pd
import json
from server import websockets
from .Module import Module
from .ModuleVersion import ModuleVersion
from .ParameterSpec import ParameterSpec
from .ParameterVal import ParameterVal
from django.utils import timezone
from server.models.StoredObject import StoredObject
from django.core.files.storage import default_storage
from django.db.models.signals import post_save
from django.dispatch import receiver

# Formatted to return milliseconds... so we are assuming that we won't store two data versions in the same ms
def current_iso_datetime_ms():
    return timezone.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


# ---- Parameter Dictionary Sanitization ----

# Column sanitization: remove invalid column names
# We can get bad column names if the module is reordered, for example
# Never make the render function deal with this.
def sanitize_column_param(pval, table_cols):
    col = pval.get_value()
    if col in table_cols:
        return col
    else:
        return ''

def sanitize_multicolumn_param(pval, table_cols):
    cols = pval.get_value().split(',')
    cols = [c.strip() for c in cols]
    cols = [c for c in cols if c in table_cols]

    return ','.join(cols)


class WfModule(models.Model):
    class Meta:
        ordering = ['order']

    def __str__(self):
        if self.workflow is not None:
            wfstr = ' - workflow: ' + self.workflow.__str__()
        else:
            wfstr = ' - deleted from workflow'
        return self.get_module_name() + ' - id: ' + str(self.id) + wfstr


    def create_parameter_dict(self, table):
        """Present parameters as a dict, with some inconsistent munging.

        A `column` parameter that refers to an invalid column will be renamed
        to the empty string.

        A `multicolumn` parameter will have its values `strip()`ed and have
        invalid columns removed.
        """
        pdict = {}
        for p in self.parameter_vals.all().prefetch_related('parameter_spec'):
            type = p.parameter_spec.type
            id_name = p.parameter_spec.id_name

            if type == ParameterSpec.COLUMN:
                pdict[id_name] = sanitize_column_param(p, table.columns)
            elif type == ParameterSpec.MULTICOLUMN:
                pdict[id_name] = sanitize_multicolumn_param(p, table.columns)
            else:
                pdict[id_name] = p.get_value()

        return pdict


    # --- Fields ----
    workflow = models.ForeignKey(
        'Workflow',
        related_name='wf_modules',
        null=True,                     # null means this is a deleted WfModule
        on_delete=models.CASCADE)      # delete WfModule if Workflow deleted

    module_version = models.ForeignKey(
        ModuleVersion,
        related_name='wf_modules',
        on_delete=models.SET_NULL,
        null=True)                      # goes null if referenced Module deleted

    order = models.IntegerField()

    notes = models.TextField(
        null=True,
        blank=True)

    stored_data_version = models.DateTimeField(
        null=True,
        blank=True)                      # we may not have stored data

    # drives whether the module is expanded or collapsed on the front-end.
    is_collapsed = models.BooleanField(
        default=False,
        blank=False,
        null=False
        )

    # For modules that fetch data: how often do we check for updates, and do we switch to latest version automatically
    auto_update_data = models.BooleanField(default=False)
    next_update = models.DateTimeField(null=True, blank=True)    # when should next update run?
    update_interval = models.IntegerField(default=86400)         # time in seconds between updates, default of 1 day
    last_update_check = models.DateTimeField(null=True, blank=True)

    notifications = models.BooleanField(default=False)

    # status light and current error message
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    TYPE_CHOICES = (
        (READY, 'Ready'),
        (BUSY, 'Busy'),
        (ERROR, 'Error')
    )
    status = models.CharField(
        max_length=8,
        choices=TYPE_CHOICES,
        default=READY,
    )
    error_msg = models.CharField('error_msg', max_length=200, blank=True)

    # ---- Utilities ----

    # navigate through a stack
    def previous_in_stack(self):
        if self.order == 0:
            return None
        else:
            return WfModule.objects.get(workflow=self.workflow, order=self.order-1)

    def get_module_name(self):
        if self.module_version is not None:
            return self.module_version.module.name
        else:
            return 'Missing module'  # deleted from server

    # ---- Authorization ----
    # User can access wf_module if they can access workflow
    def user_authorized_read(self, user):
        return self.workflow.user_authorized_read(user)

    def user_authorized_write(self, user):
        return self.workflow.user_authorized_write(user)


    # ---- Data versions ----
    # Modules that fetch data, like Load URL or Twitter or scrapers, store versions of all previously fetched data

    # Note: does not switch to new version automatically
    def store_fetched_table(self, table):
         stored_object = StoredObject.create_table(self, StoredObject.FETCHED_TABLE, table)
         return stored_object.stored_at

    # Compares against latest version (which may not be current version)
    # Note: does not switch to new version automatically
    def store_fetched_table_if_different(self, table):
        reference_so = StoredObject.objects.filter(
            wf_module=self,
            type=StoredObject.FETCHED_TABLE
        ).order_by('-stored_at').first()

        new_version = StoredObject.create_table_if_different(self, reference_so, StoredObject.FETCHED_TABLE, table)
        return new_version.stored_at if new_version else None

    def retrieve_fetched_table(self):
        if self.stored_data_version:
            return StoredObject.objects.get(
                wf_module=self,
                type=StoredObject.FETCHED_TABLE,
                stored_at=self.stored_data_version
            ).get_table()
        else:
            return None

    # versions are ISO datetimes
    def get_fetched_data_version(self):
        return self.stored_data_version

    # Like all mutators, this should usually be wrapped in a Command so it is undoable
    # In this case, a ChangeDataVersionCommand
    # NB: Can set not just FETCHED_TABLE but UPLOADED_FILE
    def set_fetched_data_version(self, version):
        if version is None or not \
            StoredObject.objects.filter(wf_module=self, stored_at=version).exists():
            raise ValueError('No such stored data version')

        self.stored_data_version = version
        self.save()

    def list_fetched_data_versions(self):
        # sort newest first, get both fetch and file types (but not cached tables)
        return list(StoredObject.objects.filter(wf_module=self)
                                        .exclude(type=StoredObject.CACHED_TABLE)
                                        .order_by('-stored_at')
                                        .values_list('stored_at', 'read'))

    # --- Parameter acessors ----
    # Hydrates ParameterVal objects from ParameterSpec objects
    def create_default_parameters(self):
        for pspec in ParameterSpec.objects.filter(module_version=self.module_version):
            pv = ParameterVal.objects.create(wf_module=self, parameter_spec=pspec)
            pv.init_from_spec()
            pv.save()

    # Retrieve current parameter values.
    # Should never throw ValueError on type conversions because ParameterVal.set_value coerces

    def get_param_raw(self, name, expected_type):
        try:
            pspec = ParameterSpec.objects.get(module_version=self.module_version, id_name=name)
        except ParameterSpec.DoesNotExist:
            raise ValueError('Request for non-existent ' + expected_type + ' parameter ' + name)

        if pspec.type != expected_type:
            raise ValueError('Request for ' + expected_type + ' parameter ' + name + ' but actual type is ' + pspec.type)

        pval = ParameterVal.objects.get(wf_module=self, parameter_spec=pspec)
        return pval.value

    def get_param_string(self, name):
        return self.get_param_raw(name, ParameterSpec.STRING)

    def get_param_integer(self, name):
        return int(self.get_param_raw(name, ParameterSpec.INTEGER))

    def get_param_float(self, name):
        return float(self.get_param_raw(name, ParameterSpec.FLOAT))

    def get_param_checkbox(self, name):
        return self.get_param_raw(name, ParameterSpec.CHECKBOX) == 'True'

    def get_param_menu_idx(self, name):
        try:
            pspec = ParameterSpec.objects.get(module_version=self.module_version, id_name=name)
        except ParameterSpec.DoesNotExist:
            raise ValueError('Request for non-existent menu parameter ' + name)
        pval = ParameterVal.objects.get(wf_module=self, parameter_spec=pspec)
        return pval.selected_menu_item_idx()

    def get_param_menu_string(self, name):
        try:
            pspec = ParameterSpec.objects.get(module_version=self.module_version, id_name=name)
        except ParameterSpec.DoesNotExist:
            raise ValueError('Request for non-existent menu parameter ' + name)
        pval = ParameterVal.objects.get(wf_module=self, parameter_spec=pspec)
        return pval.selected_menu_item_string()

    def get_param_secret_secret(self, id_name: str):
        """Get a secret's "secret" data, or None."""
        try:
            pspec = ParameterSpec.objects.get(module_version=self.module_version, id_name=id_name)
        except ParameterSpec.DoesNotExist:
            raise ValueError(f'Request for non-existent secret parameter ' + id_name)
        pval = ParameterVal.objects.get(wf_module=self, parameter_spec=pspec)
        # Don't use get_value(), since it hides the secret. (We're paranoid
        # about leaking users' secrets.)
        json_val = pval.value
        if json_val:
            try:
                val = json.loads(json_val)
            except json.decoder.JSONDecodeError:
                return None

            return val['secret']
        else:
            return None

    def get_param_column(self, name):
        return self.get_param_raw(name, ParameterSpec.COLUMN)

    def get_param_multicolumn(self, name):
        return self.get_param_raw(name, ParameterSpec.MULTICOLUMN)

    # --- Status ----
    # set error codes and status lights, notify client of changes

    # busy just changes the light on a single module, no need to reload entire wf
    def set_busy(self, notify=True):
        self.status = self.BUSY
        self.error_msg = ''
        self.save()
        if notify:
            websockets.ws_client_wf_module_status(self, self.status)


    # re-render entire workflow when a module goes ready or error, on the assumption that new output data is available
    def set_ready(self, notify=True):
        self.status = self.READY
        self.error_msg = ''
        self.save()
        if notify:
            websockets.ws_client_rerender_workflow(self.workflow)

    def set_error(self, message, notify=True):
        self.error_msg = message
        self.status = self.ERROR
        self.save()
        if notify:
            websockets.ws_client_rerender_workflow(self.workflow)

    def set_is_collapsed(self, collapsed, notify=True):
        self.is_collapsed = collapsed
        self.save()
        if notify:
            websockets.ws_client_rerender_workflow(self.workflow)

    # --- Duplicate ---
    # used when duplicating a whole workflow
    def duplicate(self, to_workflow):
        new_wfm = WfModule.objects.create(workflow=to_workflow,
                                          module_version=self.module_version,
                                          order=self.order,
                                          notes=self.notes,
                                          is_collapsed=self.is_collapsed,
                                          auto_update_data = self.auto_update_data,
                                          next_update=self.next_update,
                                          update_interval=self.update_interval,
                                          last_update_check=self.last_update_check)

        # copy all parameter values
        for pv in ParameterVal.objects.filter(wf_module=self):
            pv.duplicate(new_wfm)

        # Duplicate the current stored data only, not the history
        if self.stored_data_version is not None:
            StoredObject.objects.get(wf_module=self, stored_at=self.stored_data_version).duplicate(new_wfm)
            new_wfm.stored_data_version = self.stored_data_version
            new_wfm.save()

        # don't set status/error as first render on this wfm will set that

        return new_wfm
