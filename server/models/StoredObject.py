from django.db import models
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# StoredObject is our persistence layer.
# Allows WfModules to store keyed, versioned binary objects
class StoredObject(models.Model):
    wf_module = models.ForeignKey('WfModule', related_name='wf_module', on_delete=models.CASCADE)  # delete stored data if WfModule deleted
    file = models.FileField(upload_to='media')
    stored_at = models.DateTimeField('stored_at', auto_now=True)

    @staticmethod
    def __filename_for_id(id):
        return 'media/' + str(id) + '.dat'

    @staticmethod
    def create(wf_module, text):
        file = default_storage.save(StoredObject.__filename_for_id(wf_module.id), ContentFile(bytes(text, 'UTF-8')))
        return StoredObject.objects.create(wf_module=wf_module, file=file)

    def get_data(self):
        self.file.open(mode='rb')
        data = self.file.read()
        self.file.close()
        # copy to bytearray as data is a memoryview in prod, which has no decode method
        return bytearray(data).decode('UTF-8')

    # make a deep copy for another WfModule
    def duplicate(self, to_wf_module):
        new_file = default_storage.save(StoredObject.__filename_for_id(to_wf_module.id), self.file)
        new_so = StoredObject.objects.create(wf_module=to_wf_module,
                                             stored_at=self.stored_at,
                                             file = new_file)