from django.db import models
from server.models.Workflow import *
from server.models.ParameterSpec import *

# A parameter value, which might be string or float
class ParameterVal(models.Model):
    class Meta:
        ordering = ['order']

    wf_module = models.ForeignKey('WfModule', related_name='parameter_vals',
                               on_delete=models.CASCADE, null=True)  # delete value if Module deleted
    parameter_spec = models.ForeignKey(ParameterSpec, related_name='parameter_vals',
                               on_delete=models.CASCADE, null=True)  # delete value if Spec deleted

    order = models.IntegerField('order', default=0)

    value = models.TextField(blank=True, default='')

    menu_items = models.TextField(null=True, blank=True)

    visible = models.BooleanField(default=True)

    def init_from_spec(self):
        self.set_value(self.parameter_spec.def_value)
        self.order = self.parameter_spec.order
        self.menu_items = self.parameter_spec.def_menu_items
        self.visible = self.parameter_spec.def_visible

    # User can access param if they can access wf_module
    def user_authorized(self, user):
        return self.wf_module.user_authorized(user)

    # Return selected menu item index. Insensitive to menu item text, either in config json or at runtime.
    def selected_menu_item_idx(self):
        if self.parameter_spec.type != ParameterSpec.MENU:
            raise ValueError('Request for current item of non-menu parameter ' + self.parameter_spec.name)
        return int(self.value)

    # Return text of currently selected menu item. Warning: will vary between locales etc.
    def selected_menu_item_string(self):
        if self.parameter_spec.type != ParameterSpec.MENU:
            raise ValueError('Request for current item of non-menu parameter ' + self.parameter_spec.name)

        items = self.menu_items
        if (items is not None):
            items = items.split('|')
            idx = int(self.value)
            if items != [''] and idx >=0 and idx < len(items):
                return items[idx]
            else:
                return ''  # return empty if bad idx, to allow for possible errors when menu items changed

    # This is where type checking / coercion happens.
    def set_value(self, new_value):
        type = self.parameter_spec.type

        if type == ParameterSpec.STRING:
            self.value = new_value

        elif type == ParameterSpec.INTEGER:
            try:
                self.value = int(float(new_value))
            except ValueError:
                self.value = '0'

        elif type == ParameterSpec.FLOAT:
            try:
                self.value = str(float(new_value))
            except ValueError:
                self.value = '0.0'

        elif type == ParameterSpec.CHECKBOX:
            try:
                # Be permissive, allow both '1' and 'True' ('True' used in json spec)
                self.value = '1' if (new_value.strip().lower() == 'true' or (new_value) == 1) else '0'
            except ValueError:
                self.value = '0'

        elif type == ParameterSpec.MENU:
            try:
                self.value = str(int(new_value))
            except ValueError:
                self.value = '0'

        elif type == ParameterSpec.COLUMN or \
             type == ParameterSpec.MULTICOLUMN or \
             type == ParameterSpec.CUSTOM or \
             type == ParameterSpec.BUTTON:
            self.value = new_value

        else:
            raise ValueError('Unknown parameter type ' + type + ' for parameter ' + self.parameter_spec.name + ' in ParameterVal.set_value')

        self.save()


    def get_value(self):
        return self.value

    def __str__(self):
        return self.wf_module.__str__() + ' - ' + self.parameter_spec.name + ' - ' + str(self.get_value())