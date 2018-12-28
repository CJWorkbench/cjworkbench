from django.contrib import admin
from .models import *

admin.site.register(ParameterSpec)
admin.site.register(Module)
admin.site.register(ModuleVersion)
admin.site.register(WfModule)
admin.site.register(StoredObject)
admin.site.register(Delta)

class WorkflowAdmin(admin.ModelAdmin):
    raw_id_fields = ("last_delta",)   # don't load load every delta ever on the workflow object page

    search_fields = ('name', 'owner__username', 'owner__email' )
    list_filter = ('owner',)

admin.site.register(Workflow, WorkflowAdmin)
