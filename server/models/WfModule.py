# WfModule is a Module that has been applied in a Workflow
# We also have ParameterSpec and ParameterVal in this file, to avoid circular reference problems

from django.db import models
import pandas as pd
from server.models.Module import *
from server.models.ModuleVersion import *
from server.models.ParameterVal import *
from django.utils import timezone
from server.models.StoredObject import StoredObject
from django.core.files.storage import default_storage
from django.db.models.signals import post_save
from django.dispatch import receiver

# Completely ridiculous work to resolve circular imports: websockets -> Workflow -> WfModule which needs websockets
# So we create an object with callbacks, which we then set in websockets.py
class WsCallbacks:
    ws_client_wf_module_status = None
    ws_client_rerender_workflow = None

ws_callbacks = WsCallbacks()

# Formatted to return milliseconds... so we are assuming that we won't store two data versions in the same ms
def current_iso_datetime_ms():
    return timezone.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


class WfModule(models.Model):
    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.workflow.__str__() + ' - order: ' + str(self.order) + ' - ' + self.module_version.__str__()

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

    # DO NOT use null=True, causes problems in test
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
    auto_update_data = models.BooleanField(default='False')
    next_update = models.DateTimeField(null=True, blank=True)    # when should next update run?
    update_interval = models.IntegerField(default=0)             # time in seconds between updates
    last_update_check = models.DateTimeField(null=True, blank=True)

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

    # ---- Authorization ----
    # User can access wf_module if they can access workflow
    def user_authorized_read(self, user):
        return self.workflow.user_authorized_read(user)

    def user_authorized_write(self, user):
        return self.workflow.user_authorized_write(user)




    # ---- Data versions ----
    # Modules that fetch data, like Load URL or Twitter or scrapers, store versions of all previously fetched data

    def store_data(self, text):
        stored_object = StoredObject.create(self, text)
        return stored_object.stored_at

    def retrieve_data(self):
        if self.stored_data_version:
            return StoredObject.objects.get(wf_module=self, stored_at=self.stored_data_version).get_data()
        else:
            return None

    def retrieve_file(self):
        if self.stored_data_version:
            return StoredObject.objects.get(wf_module=self, stored_at=self.stored_data_version).file
        else:
            return None

    # versions are ISO datetimes
    def get_stored_data_version(self):
        return self.stored_data_version

    # NOTE like all mutators, this should usually be wrapped in a command
    # In this case, a ChangeDataVersionCommand
    def set_stored_data_version(self, version):
        versions = self.list_stored_data_versions()
        if version not in versions:
            raise ValueError('No such stored data version')
        self.stored_data_version = version
        self.save()

    def list_stored_data_versions(self):
        return list(StoredObject.objects.filter(wf_module=self).order_by('stored_at').values_list('stored_at', flat=True))

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

    def get_param_column(self, name):
        return self.get_param_raw(name, ParameterSpec.COLUMN)

    def get_param_multicolumn(self, name):
        return self.get_param_raw(name, ParameterSpec.MULTICOLUMN)

    # --- Status ----
    # set error codes and status lights, notify client of changes

    # busy just changes the light on a single module, no need to reload entire wf
    def set_busy(self, notify=True):
        self.status = self.BUSY
        error_msg = ''
        if notify:
            ws_callbacks.ws_client_wf_module_status(self, self.status)
        self.save()

    # re-render entire workflow when a module goes ready or error, on the assumption that new output data is available
    def set_ready(self, notify=True):
        self.status = self.READY
        if notify:
            ws_callbacks.ws_client_rerender_workflow(self.workflow)
        self.save()

    def set_error(self, message, notify=True):
        self.error_msg = message
        self.status = self.ERROR
        if notify:
            ws_callbacks.ws_client_rerender_workflow(self.workflow)
        self.save()

    def set_is_collapsed(self, collapsed, notify=True):
        self.is_collapsed = collapsed
        if notify:
            ws_callbacks.ws_client_rerender_workflow(self.workflow)
        self.save()

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

        # don't set status/error as first render on this wfm will set that

        return new_wfm

# I don't think we want this -- API is use set_stored_data_version
@receiver(post_save, sender=StoredObject)
def update_stored_data_version(sender, **kwargs):
    kwargs['instance'].wf_module.stored_data_version = kwargs['instance'].stored_at
    kwargs['instance'].wf_module.save()