from django.forms import ModelForm
from server.models.UploadedFile import UploadedFile

#  Processes submitted file upload
class UploadedFileForm(ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['wf_module', 'file', 'name', 'size', 'uuid']
