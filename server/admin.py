from django.contrib import admin
from .models import (
    ModuleVersion,
    WfModule,
    StoredObject,
    Delta,
    Workflow,
    Tab,
    WfModule,
)

admin.site.register(ModuleVersion)
admin.site.register(Delta)


class WorkflowAdmin(admin.ModelAdmin):
    # disallow bulk-delete: we need Workflow.delete() to be called, because it
    # deletes files from S3.
    actions = None

    # don't load load every delta ever on the workflow object page
    raw_id_fields = ("last_delta",)

    search_fields = ("name", "owner__username", "owner__email")
    list_filter = ("owner",)

    def get_deleted_objects(self, objs, request):
        """
        Allow deleting Workflows by hiding Delta from confirmation page.

        Deltas depend on workflows which depend on Deltas -- a circular
        dependency. `workflow.delete()` resolves the conflict; so let's not
        let Django Admin's automated logic prevent us from calling it.

        https://www.pivotaltracker.com/story/show/164292305
        """
        assert len(objs) == 1  # we don't bulk-delete
        tabs = (
            objs[0]
            .tabs.only("id", "slug", "name", "is_deleted")
            .prefetch_related("wf_modules")
        )
        to_delete = []
        step_count = 0
        for tab in tabs:
            tab_to_delete = f"Tab {tab.id} [{tab.slug}: {tab.name}]"
            steps_to_delete = [
                f"Step {tab.slug}-{step.order} [{step.module_id_name}]"
                for step in tab.wf_modules.all()
            ]
            to_delete.append([tab_to_delete, steps_to_delete])
            step_count += len(steps_to_delete)

        return (
            to_delete,
            {
                Tab._meta.verbose_name_plural: len(tabs),
                WfModule._meta.verbose_name_plural: step_count,
            },
            set(),
            [],
        )


admin.site.register(Workflow, WorkflowAdmin)
