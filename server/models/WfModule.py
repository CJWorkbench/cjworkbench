# WfModule is a Module that has been applied in a Workflow
# We also have ParameterSpec and ParameterVal in this file, to avoid circular reference problems

from django.db import models
import pandas as pd
from server.models.Module import *
from server.models.Workflow import *
from server.dispatch import module_dispatch_render
from server.websockets import ws_client_rerender_workflow, ws_client_wf_module_status

class WfModule(models.Model):
    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.workflow.__str__() + ' - order: ' + str(self.order) + ' - ' + self.module.__str__()

    # --- Fields ----
    workflow = models.ForeignKey(Workflow, related_name='wf_modules',
                                 on_delete=models.CASCADE)  # delete WfModule if Workflow deleted
    module = models.ForeignKey(Module, related_name='wf_modules',
                               on_delete=models.SET_NULL,
                               null=True)  # goes null if referenced Module deletedp
    order = models.IntegerField('order')

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

    # ---- Persistent storage ----
    def store_bytes(self, key, data):
        StoredObject.objects.create(wf_module=self, key=key, data=data)

    def retrieve_bytes(self, key):
        objs = StoredObject.objects.filter(wf_module=self, key=key)
        if objs:
            return objs.latest('stored_at').data
        else:
            return None

    def store_text(self, key, text):
        self.store_bytes(key, bytes(text, 'UTF-8'))

    def retrieve_text(self, key):
        data = self.retrieve_bytes(key)
        if data:
            return data.decode('UTF-8')
        else:
            return None

    # --- Parameter acessors ----
    # Hydrates ParameterVal objects from ParameterSpec objects
    def create_default_parameters(self):
        for pspec in ParameterSpec.objects.filter(module=self.module):
            pv = ParameterVal.objects.create(wf_module=self, parameter_spec=pspec)
            pv.init_from_spec()
            pv.save()

    # Retrieve current parameter values
    def get_param_typecheck(self, name, param_type):
        try:
            pspec = ParameterSpec.objects.get(module=self.module, id_name=name)
        except ParameterSpec.DoesNotExist:
            raise ValueError('Request for non-existent ' + param_type + ' parameter ' + name)

        if pspec.type != param_type:
            raise ValueError('Request for ' + param_type + ' parameter ' + name + ' but actual type is ' + pspec.type)
        pval = ParameterVal.objects.get(wf_module=self, parameter_spec=pspec)
        if param_type == ParameterSpec.STRING:
            return pval.string
        elif param_type == ParameterSpec.NUMBER:
            return pval.number
        elif param_type == ParameterSpec.CHECKBOX:
            return pval.checkbox

    def get_param_string(self, name):
        return self.get_param_typecheck(name, ParameterSpec.STRING)

    def get_param_number(self, name):
        return self.get_param_typecheck(name, ParameterSpec.NUMBER)

    def get_param_checkbox(self, name):
        return self.get_param_typecheck(name, ParameterSpec.CHECKBOX)

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

    # --- Rendering ----

    # Modules ingest and emit a table (though may do only one, if source or sink)
    # Returns data only if the module is not busy (modules can return error results in table form)
    def execute(self, table):
        if (self.status == self.READY):
            return module_dispatch_render(self, table)
        else:
            return pd.DataFrame()


# ParameterSpec defines a parameter UI and defaults for a particular Module
class ParameterSpec(models.Model):
    class Meta:
        ordering = ['order']

    # constants
    STRING = 'string'
    NUMBER = 'number'
    BUTTON = 'button'
    CUSTOM = 'custom'           # rendered in front end
    CHECKBOX = 'checkbox'
    TYPE_CHOICES = (
        (STRING, 'String'),
        (NUMBER, 'Number'),
        (BUTTON, 'Button'),
        (CHECKBOX, 'Checkbox'),
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

    module = models.ForeignKey(Module, related_name='parameter_specs',
                               on_delete=models.CASCADE)  # delete spec if Module deleted

    order = models.IntegerField('order', default=0)

    def_number = models.FloatField(NUMBER, null=True, blank=True, default=0.0)
    def_string = models.TextField(STRING, blank=True, default='')
    def_checkbox = models.BooleanField(CHECKBOX, default=True)

    def_visible = models.BooleanField(default=True)
    def_ui_only = models.BooleanField(default=False)
    def_multiline = models.BooleanField(default=False)

    def __str__(self):
        return self.module.name + ' - ' + self.name


# A parameter value, which might be string or float
class ParameterVal(models.Model):
    class Meta:
        ordering = ['order']

    number = models.FloatField(ParameterSpec.NUMBER, null=True, blank=True)
    string = models.TextField(ParameterSpec.STRING, null=True, blank=True)
    checkbox = models.BooleanField(ParameterSpec.CHECKBOX, default=True)

    wf_module = models.ForeignKey(WfModule, related_name='parameter_vals',
                               on_delete=models.CASCADE, null=True)  # delete value if Module deleted
    parameter_spec = models.ForeignKey(ParameterSpec, related_name='parameter_vals',
                               on_delete=models.CASCADE, null=True)  # delete value if Spec deleted

    order = models.IntegerField('order', default=0)

    visible = models.BooleanField(default=True)
    ui_only = models.BooleanField(default=False)
    multiline = models.BooleanField(default=False)

    def init_from_spec(self):
        self.number = self.parameter_spec.def_number
        self.string = self.parameter_spec.def_string
        self.checkbox = self.parameter_spec.def_checkbox
        self.order = self.parameter_spec.order
        self.visible = self.parameter_spec.def_visible
        self.ui_only = self.parameter_spec.def_ui_only
        self.multiline = self.parameter_spec.def_multiline

    # User can access param if they can access wf_module
    def user_authorized(self, user):
        return self.wf_module.user_authorized(user)

    def __str__(self):
        if self.parameter_spec.type == ParameterSpec.STRING:
            return self.wf_module.__str__() + ' - ' + self.parameter_spec.name + ' - ' + self.string
        elif self.parameter_spec.type == ParameterSpec.NUMBER:
            return self.wf_module.__str__() + ' - ' + self.parameter_spec.name + ' - ' + str(self.number)
        elif self.parameter_spec.type == ParameterSpec.BUTTON:
            return self.wf_module.__str__() + ' - ' + self.parameter_spec.name + ' - button'
        elif self.parameter_spec.type == ParameterSpec.CUSTOM:
            return self.wf_module.__str__() + ' - ' + self.parameter_spec.name + ' - custom'
        elif self.parameter_spec.type == ParameterSpec.CHECKBOX:
            return self.wf_module.__str__() + ' - ' + ' - checkbox'
        else:
            raise ValueError("Invalid parameter type")



# StoredObject is our persistance layer.
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
