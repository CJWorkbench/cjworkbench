from django.db import models
from django.db.models import F
from server.models import Delta, ModuleVersion, WfModule
from server import rabbitmq
from .util import ChangesWfModuleOutputs


class AddModuleCommand(Delta, ChangesWfModuleOutputs):
    """
    Create a `WfModule` and insert it into the Workflow.

    Our "backwards()" logic is to "soft-delete": set
    `wfmodule.is_deleted=True`. Most facets of Workbench's API should pretend a
    soft-deleted WfModules does not exist.
    """

    # Foreign keys can get a bit confusing. Here we go:
    #
    # * AddModuleCommand can only exist if its WfModule exists.
    # * WfModule depends on Workflow.
    # * AddModuleCommand depends on Workflow.
    #
    # So it's safe to delete Commands from a Workflow (as long as the workflow
    # has at least one delta). But it's not safe to delete WfModules from a
    # workflow -- unless one clears the Deltas first.
    #
    # We set on_delete=PROTECT because if we set on_delete=CASCADE we'd be
    # ambiguous: should one delete the WfModule first, or the Delta? The answer
    # is: you _must_ delete the Delta first; after deleting the Delta, you
    # _may_ delete the WfModule.
    wf_module = models.ForeignKey(WfModule, on_delete=models.PROTECT)
    wf_module_delta_ids = ChangesWfModuleOutputs.wf_module_delta_ids

    def load_ws_data(self):
        data = super().load_ws_data()
        data['updateTabs'] = {
            self.wf_module.tab.slug: {
                'wf_module_ids': list(self.wf_module.tab.live_wf_modules
                                      .values_list('id', flat=True)),
            },
        }
        return data

    @classmethod
    def affected_wf_modules_in_tab(cls, wf_module) -> models.Q:
        # We don't need to change self.wf_module's delta_id: just the others.
        #
        # At the time this method is called, `wf_module` is "deleted" (well,
        # not yet created).
        return models.Q(tab_id=wf_module.tab_id, order__gte=wf_module.order,
                        is_deleted=False)

    def forward_impl(self):
        if not self.wf_module.last_relevant_delta_id:
            # We couldn't set self.wf_module.last_relevant_delta_id during
            # creation because `self` (the delta in question) wasn't created.
            # Set it now, before .forward_affected_delta_ids(). After this
            # first write, this Delta should never modify it.
            self.wf_module.last_relevant_delta_id = self.id
            self.wf_module.save(update_fields=['last_relevant_delta_id'])

        # Move subsequent modules over to make way for this one.
        tab = self.wf_module.tab
        tab.live_wf_modules.filter(order__gte=self.wf_module.order) \
            .update(order=F('order') + 1)

        self.wf_module.is_deleted = False
        self.wf_module.save(update_fields=['is_deleted'])

        tab.selected_wf_module_position = self.wf_module.order
        tab.save(update_fields=['selected_wf_module_position'])

        self.forward_affected_delta_ids()

    def backward_impl(self):
        self.wf_module.is_deleted = True
        self.wf_module.save(update_fields=['is_deleted'])

        # Move subsequent modules back to fill the gap created by deleting
        tab = self.wf_module.tab
        tab.live_wf_modules.filter(order__gt=self.wf_module.order) \
            .update(order=F('order') - 1)

        # Prevent tab.selected_wf_module_position from becoming invalid
        #
        # We can't make this exactly what the user has selected -- that's hard,
        # and it isn't worth the effort. But we _can_ make sure it's valid.
        n_modules = tab.live_wf_modules.count()
        if (
            tab.selected_wf_module_position is None
            or tab.selected_wf_module_position >= n_modules
        ):
            if n_modules == 0:
                tab.selected_wf_module_position = None
            else:
                tab.selected_wf_module_position = n_modules - 1
            tab.save(update_fields=['selected_wf_module_position'])

        self.backward_affected_delta_ids()

    # override
    async def schedule_execute_if_needed(self) -> None:
        """
        Force a render.

        Adding a module to an empty workflow, self._changed_wf_module_versions
        will be None -- and yet we need a render!

        TODO brainstorm other solutions to the original race -- that we can't
        know this delta's ID until after we save it to the database, yet we
        need to save its own ID in self._changed_wf_module_versions.
        """
        await rabbitmq.queue_render(self.workflow.id,
                                    self.workflow.last_delta_id)


    @classmethod
    def amend_create_kwargs(cls, *, workflow, tab, module_id_name,
                            position, param_values, **kwargs):
        """
        Add a step to the tab.

        Raise ModuleVersion.DoesNotExist if `module_id_name` is invalid.
        Raise ValueError if `param_values` do not match the module's spec.
        """
        # raises ModuleVersion.DoesNotExist
        module_version = ModuleVersion.objects.latest(module_id_name)

        # Set _all_ params (not just the user-specified ones). Our
        # dropdown-menu actions only specify the relevant params and expect us
        # to set the others to defaults.
        params = {
            **module_version.default_params,
            **param_values,
        }

        module_version.param_schema.validate(params)  # raises ValueError

        # wf_module starts off "deleted" and gets un-deleted in forward().
        wf_module = tab.wf_modules.create(module_id_name=module_id_name,
                                          order=position, is_deleted=True,
                                          params=params, secrets={})

        return {
            **kwargs,
            'workflow': workflow,
            'wf_module': wf_module,
            'wf_module_delta_ids': cls.affected_wf_module_delta_ids(wf_module),
        }

    @property
    def command_description(self):
        return f'Add WfModule {self.wf_module}'
