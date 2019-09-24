from django.forms import ModelForm
from cjwstate.models.UploadedFile import UploadedFile


#  Processes submitted file upload
class UploadedFileForm(ModelForm):
    class Meta:
        model = UploadedFile
        fields = ["wf_module", "bucket", "key", "name", "uuid"]
