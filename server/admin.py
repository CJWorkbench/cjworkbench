from django.contrib import admin

# Register your models here.

from django.contrib import admin

from .models import ParameterVal,ParameterSpec,Module,Workflow,WfModule

admin.site.register(ParameterVal)
admin.site.register(ParameterSpec)
admin.site.register(Module)
admin.site.register(Workflow)
admin.site.register(WfModule)
