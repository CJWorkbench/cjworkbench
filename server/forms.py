from django.forms import ModelForm
from server.models import StoredObject

class StoredObjectForm(ModelForm):
    class Meta:
        model = StoredObject
        fields = ['wf_module', 'file', 'name', 'size', 'uuid']
    # qqfile = forms.FileField()
    # qquuid = forms.CharField()
    # qqfilename = forms.CharField()
    # qqpartindex = forms.IntegerField(required=False)
    # qqchunksize = forms.IntegerField(required=False)
    # qqpartbyteoffset = forms.IntegerField(required=False)
    # qqtotalfilesize = forms.IntegerField(required=False)
    # qqtotalparts = forms.IntegerField(required=False)