# WfModule is a Module that has been applied in a Workflow
# We also have ParameterSpec and ParameterVal in this file, to avoid circular reference problems

from django.db import models
import pandas as pd
from server.models.Module import *
from server.models.ModuleVersion import *
from server.models.Workflow import *
from server.models.ParameterVal import *
from server.websockets import ws_client_rerender_workflow, ws_client_wf_module_status
from django.utils import timezone

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
        Workflow,
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

    stored_data_version = models.CharField(
        max_length=32,
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
    def user_authorized(self, user):
        return self.workflow.user_authorized(user)

    # For now, all render output is publicly acessible
    def public_authorized(self):
        return True


    # ---- Data versions ----
    # Modules that fetch data, like Load URL or Twitter or scrapers, store versions of all previously fetched data

    def store_data(self, text):
        # uses current datetime as key; assumes we don't store more than one version per millisecond
        data_version = current_iso_datetime_ms()
        StoredObject.objects.create(
            wf_module=self,
            key=data_version,
            data=bytes(text, 'UTF-8'))
        return data_version

    def retrieve_data(self):
        if self.stored_data_version:
            data = StoredObject.objects.get(wf_module=self, key=self.stored_data_version).data
            return bytearray(data).decode('UTF-8')
                # copy to bytearray as data is a memoryview in prod, which has no decode method
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
        return list(StoredObject.objects.filter(wf_module=self).order_by('stored_at').values_list('key', flat=True))

    # --- Parameter acessors ----
    # Hydrates ParameterVal objects from ParameterSpec objects
    def create_default_parameters(self):
        for pspec in ParameterSpec.objects.filter(module_version=self.module_version):
            pv = ParameterVal.objects.create(wf_module=self, parameter_spec=pspec)
            pv.init_from_spec()
            pv.save()

    # Retrieve current parameter values
    def get_param_typecheck(self, name, param_type):
        try:
            pspec = ParameterSpec.objects.get(module_version=self.module_version, id_name=name)
        except ParameterSpec.DoesNotExist:
            raise ValueError('Request for non-existent ' + param_type + ' parameter ' + name)

        if pspec.type != param_type:
            raise ValueError('Request for ' + param_type + ' parameter ' + name + ' but actual type is ' + pspec.type)
        pval = ParameterVal.objects.get(wf_module=self, parameter_spec=pspec)
        if param_type == ParameterSpec.STRING:
            return pval.string
        elif param_type == ParameterSpec.NUMBER:
            return pval.float
        elif param_type == ParameterSpec.CHECKBOX:
            return pval.boolean

    def get_param_string(self, name):
        return self.get_param_typecheck(name, ParameterSpec.STRING)

    def get_param_number(self, name):
        return self.get_param_typecheck(name, ParameterSpec.NUMBER)

    def get_param_checkbox(self, name):
        return self.get_param_typecheck(name, ParameterSpec.CHECKBOX)

    def get_param_menu_idx(self, name):
        try:
            pspec = ParameterSpec.objects.get(module_version=self.module_version, id_name=name)
        except ParameterSpec.DoesNotExist:
            raise ValueError('Request for non-existent ' + param_type + ' parameter ' + name)
        pval = ParameterVal.objects.get(wf_module=self, parameter_spec=pspec)
        return pval.selected_menu_item_idx()

    def get_param_menu_string(self, name):
        try:
            pspec = ParameterSpec.objects.get(module_version=self.module_version, id_name=name)
        except ParameterSpec.DoesNotExist:
            raise ValueError('Request for non-existent ' + param_type + ' parameter ' + name)
        pval = ParameterVal.objects.get(wf_module=self, parameter_spec=pspec)
        return pval.selected_menu_item_string()



    # --- Status ----
    # set error codes and status lights, notify client of changes

    # busy just changes the light on a single module, no need to reload entire wf
    def set_busy(self, notify=True):
        self.status = self.BUSY
        error_msg = ''
        if notify:
            ws_client_wf_module_status(self, self.status)
        self.save()

    # re-render entire workflow when a module goes ready or error, on the assumption that new output data is available
    def set_ready(self, notify=True):
        self.status = self.READY
        if notify:
            ws_client_rerender_workflow(self.workflow)
        self.save()

    def set_error(self, message, notify=True):
        self.error_msg = message
        self.status = self.ERROR
        if notify:
            ws_client_rerender_workflow(self.workflow)
        self.save()

    def set_is_collapsed(self, collapsed, notify=True):
        self.is_collapsed = collapsed
        if notify:
            ws_client_rerender_workflow(self.workflow)
        self.save()

# StoredObject is our persistence layer.
# Allows WfModules to store keyed, versioned binary objects
class StoredObject(models.Model):
    wf_module = models.ForeignKey(WfModule, related_name='wf_module', on_delete=models.CASCADE)  # delete stored data if WfModule deleted

    key = models.CharField('key', max_length = 64, blank=True, default='')

    data = models.BinaryField(blank=True)

    stored_at = models.DateTimeField('stored_at', auto_now=True)

    # String accessors for ease of use
    def set_string(self, s):
        data = bytes(s, 'UTF-8')

    def get_string(self):
        return data.decode('UTF-8')
