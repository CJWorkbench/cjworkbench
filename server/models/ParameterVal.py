from django.db import models
from server.models.ParameterSpec import ParameterSpec
import json


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

    items = models.TextField(null=True, blank=True)

    def init_from_spec(self):
        self.value = self.parameter_spec.def_value
        self.order = self.parameter_spec.order
        self.items = self.parameter_spec.def_items

    def duplicate(self, to_wf_module):
        if self.parameter_spec.type == ParameterSpec.SECRET:
            value = ''
        else:
            value = self.value

        newval = ParameterVal.objects.create(
            wf_module=to_wf_module,
            parameter_spec=self.parameter_spec,
            order=self.order,
            value=value,
            items=self.items
        )
        return newval


    # User can access param if they can access wf_module
    def request_authorized_read(self, request):
        return self.wf_module.request_authorized_read(request)

    def request_authorized_write(self, request):
        return self.wf_module.request_authorized_write(request)

    # Return selected menu item index. Insensitive to menu item text, either in config json or at runtime.
    def selected_menu_item_idx(self):
        if self.parameter_spec.type != ParameterSpec.MENU:
            raise ValueError('Request for current item of non-menu parameter ' + self.parameter_spec.name)
        return int(self.value)

    # Return text of currently selected menu item. Warning: will vary between locales etc.
    def selected_menu_item_string(self):
        if self.parameter_spec.type != ParameterSpec.MENU:
            raise ValueError('Request for current item of non-menu parameter ' + self.parameter_spec.name)

        items = self.items
        if (items is not None):
            items = items.split('|')
            idx = int(self.value)
            if items != [''] and idx >=0 and idx < len(items):
                return items[idx]
            else:
                return ''  # return empty if bad idx, to allow for possible errors when menu items changed

    # Return selected radio item index. Insensitive to menu item text, either in config json or at runtime.
    def selected_radio_item_idx(self):
        if self.parameter_spec.type != ParameterSpec.RADIO:
            raise ValueError('Request for current item of non-radio parameter ' + self.parameter_spec.name)
        return int(self.value)

    # Return text of currently selected radio item. Warning: will vary between locales etc.
    def selected_radio_item_string(self):
        if self.parameter_spec.type != ParameterSpec.RADIO:
            raise ValueError('Request for current item of non-radio parameter ' + self.parameter_spec.name)

        items = self.items
        if (items is not None):
            items = items.split('|')
            idx = int(self.value)
            if items != [''] and idx >= 0 and idx < len(items):
                return items[idx]
            else:
                return ''  # return empty if bad idx, to allow for possible errors when radio items changed

    # This is where type checking / coercion happens.
    def set_value(self, new_value):
        self.value = self.parameter_spec.value_to_str(new_value)
        self.save(update_fields=['value'])

    # Coerce back to appropriate ptype
    def get_value(self):
        return self.parameter_spec.str_to_value(self.value)

    def get_secret(self):
        ptype = self.parameter_spec.type
        if ptype == ParameterSpec.SECRET:
            if self.value:
                return json.loads(self.value)['secret']
            else:
                return None

    def __str__(self):
        return self.wf_module.__str__() + ' - ' + self.parameter_spec.name + ' - ' + str(self.get_value())
