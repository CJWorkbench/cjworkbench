from django.forms import ModelForm
from server.models import StoredObject

#  Processes submitted file upload
class StoredObjectForm(ModelForm):
    class Meta:
        model = StoredObject
        fields = ['wf_module', 'file', 'name', 'size', 'uuid']
