from django.db import models
from server.models.Workflow import *
from server.models.ParameterSpec import *

# A parameter value, which might be string or float
class ParameterVal(models.Model):
    class Meta:
        ordering = ['order']

    string = models.TextField("string", null=True, blank=True)
    float = models.FloatField("float", null=True, blank=True)
    integer = models.IntegerField("integer", blank=True, default='0')
    boolean = models.BooleanField("boolean", default=True)

    wf_module = models.ForeignKey('WfModule', related_name='parameter_vals',
                               on_delete=models.CASCADE, null=True)  # delete value if Module deleted
    parameter_spec = models.ForeignKey(ParameterSpec, related_name='parameter_vals',
                               on_delete=models.CASCADE, null=True)  # delete value if Spec deleted

    order = models.IntegerField('order', default=0)

    menu_items = models.TextField(ParameterSpec.MENU, null=True, blank=True)

    visible = models.BooleanField(default=True)

    def init_from_spec(self):
        self.string = self.parameter_spec.def_string
        self.float = self.parameter_spec.def_float
        self.boolean= self.parameter_spec.def_boolean
        self.integer = self.parameter_spec.def_integer
        self.order = self.parameter_spec.order
        self.menu_items = self.parameter_spec.def_menu_items
        self.visible = self.parameter_spec.def_visible

    # User can access param if they can access wf_module
    def user_authorized(self, user):
        return self.wf_module.user_authorized(user)

    # Return text of currently selected menu item
    def selected_menu_item_string(self):
        if self.parameter_spec.type != ParameterSpec.MENU:
            raise ValueError('Request for current item of non-menu parameter ' + self.parameter_spec.name)

        items = self.menu_items
        if (items is not None):
            items = items.split('|')
            idx = self.integer
            if items != [''] and idx >=0 and idx < len(items):
                return items[idx]
            else:
                return ''  # be a little lenient, to allow for possible errors when menu items changed

    def set_value(self, new_value):
        type = self.parameter_spec.type
        if type == ParameterSpec.STRING:
            self.string = new_value
        elif type == ParameterSpec.NUMBER:
            self.float = new_value
        elif type == ParameterSpec.CHECKBOX:
            self.boolean = new_value
        elif type == ParameterSpec.MENU:
            self.integer = new_value
        elif type == ParameterSpec.CUSTOM:
            self.string = new_value             # store custom parameter's data as string
        else:
            raise ValueError('Unknown parameter type ' + type + ' for parameter ' + self.parameter_spec.name + ' in ParameterVal.set_value')
        self.save()

    def get_value(self):
        type = self.parameter_spec.type
        if type == ParameterSpec.STRING:
            return self.string
        elif type == ParameterSpec.NUMBER:
            return self.float
        elif type == ParameterSpec.CHECKBOX:
            return self.boolean
        elif type == ParameterSpec.MENU:
            return self.integer
        elif type == ParameterSpec.CUSTOM:
            return self.string              # store custom parameter's data as string
        elif type == ParameterSpec.BUTTON:
            return None                     # buttons have no data (this line needed for Admin interface display)
        else:
            raise ValueError('Unknown parameter type ' + type + ' for parameter ' + self.parameter_spec.name + ' in ParameterVal.get_value')

    def __str__(self):
        return self.wf_module.__str__() + ' - ' + self.parameter_spec.name + ' - ' + str(self.get_value())