from django.contrib import admin

# Register your models here.

from django.contrib import admin

from .models import Workflow,WfModule

admin.site.register(Workflow)
admin.site.register(WfModule)
