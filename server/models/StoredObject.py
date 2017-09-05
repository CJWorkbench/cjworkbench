from django.db import models



# StoredObject is our persistence layer.
# Allows WfModules to store keyed, versioned binary objects
class StoredObject(models.Model):
    wf_module = models.ForeignKey('WfModule', related_name='wf_module', on_delete=models.CASCADE)  # delete stored data if WfModule deleted
    file = models.FileField(upload_to='media')
    stored_at = models.DateTimeField('stored_at', auto_now=True)

