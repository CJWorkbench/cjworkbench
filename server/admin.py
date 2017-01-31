from django.contrib import admin
from .models import *

admin.site.register(ParameterVal)
admin.site.register(ParameterSpec)
admin.site.register(Module)
admin.site.register(Workflow)
admin.site.register(WfModule)
admin.site.register(StoredObject)