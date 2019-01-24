from typing import List, Tuple
from django.contrib.postgres.fields import ArrayField
from django.db import models
from server.models import WfModule


class ChangesWfModuleOutputs:
    """
    Mixin that tracks wf_module.last_relevant_delta_id on affected WfModules.

    Usage:

        class MyCommand(Delta, ChangesWfModuleOutputs):
            wf_module_delta_ids = ChangesWfModuleOutputs.wf_module_delta_ids

            # override
            @classmethod
            def amend_create_kwargs(cls, *, wf_module, **kwargs):
                # You must store affected_wf_module_delta_ids.
                return {
                    **kwargs,
                    'wf_module': wf_module,
                    'wf_module_delta_ids':
                        cls.affected_wf_module_delta_ids(wf_module),
                }

            def forward_impl(self):
                ...
                # update wf_modules in database and store
                # self._changed_wf_module_delta_ids, for websockets message.
                self.forward_affected_delta_ids()

            def backward_impl(self):
                ...
                # update wf_modules in database and store
                # self._changed_wf_module_delta_ids, for websockets message.
                self.backward_affected_delta_ids()
    """

    # List of (id, last_relevant_delta_id) for WfModules, pre-`forward()`.
    wf_module_delta_ids = ArrayField(
        ArrayField(
            models.IntegerField(),
            size=2
        )
    )

    @classmethod
    def affected_wf_modules(cls, wf_module) -> models.QuerySet:
        """
        QuerySet of all WfModules that may change as a result of this Delta.

        The default implementation _includes_ the passed `wf_module`.
        """
        return WfModule.objects.filter(tab_id=wf_module.tab_id,
                                       order__gte=wf_module.order,
                                       is_deleted=False)

    @classmethod
    def affected_wf_module_delta_ids(cls, wf_module) -> List[Tuple[int, int]]:
        return list(cls.affected_wf_modules(wf_module)
                    .values_list('id', 'last_relevant_delta_id'))

    def forward_affected_delta_ids(self):
        """
        Write new last_relevant_delta_id to affected WfModules.

        (This usually includes self.wf_module.)
        """
        prev_ids = self.wf_module_delta_ids

        affected_ids = [pi[0] for pi in prev_ids]

        WfModule.objects.filter(pk__in=affected_ids) \
                .update(last_relevant_delta_id=self.id)

        # If we have a wf_module in memory, update it.
        if hasattr(self, 'wf_module_id') and self.wf_module_id in affected_ids:
            self.wf_module.last_relevant_delta_id = self.id

        # for ws_notify()
        self._changed_wf_module_versions = [(pi[0], self.id)
                                            for pi in prev_ids]

    def backward_affected_delta_ids(self):
        """
        Write new last_relevant_delta_id to `wf_module` and its dependents.
        """
        prev_ids = self.wf_module_delta_ids

        for wfm_id, delta_id in prev_ids:
            WfModule.objects.filter(id=wfm_id) \
                 .update(last_relevant_delta_id=delta_id)

            if hasattr(self, 'wf_module_id') and wfm_id == self.wf_module_id:
                # If we have a wf_module in memory, update it
                self.wf_module.last_relevant_delta_id = delta_id

        # for ws_notify()
        self._changed_wf_module_versions = prev_ids
