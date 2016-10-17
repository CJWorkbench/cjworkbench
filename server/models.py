from django.db import models

# Create your models here.
from django.db import models


class Workflow(models.Model):
    name = models.CharField('name',max_length=200)
    creation_date = models.DateTimeField('creation date')

    def __str__(self):
        return self.name

class WfModule(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE)
    parameters = models.CharField('parameters',max_length=200)


    def __str__(self):
        return self.parameters


