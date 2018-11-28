from typing import List, Tuple
from django.contrib.postgres.fields import ArrayField
from django.core.validators import int_list_validator
from django.db import models
from server.models import WfModule, Workflow


class ChangesWfModuleOutputs:
    # DEPRECATED List of wf_module.last_relevant_delta_id from _before_
    # .forward() was called, for *this* wf_module and the ones *after* it.
    #
    # Use wf_module_delta_ids instead.
    #
    # Migration strategy: if `wf_module_delta_ids` is NULL, fall back to
    # `dependent_wf_module_last_delta_ids`.
    dependent_wf_module_last_delta_ids = models.CharField(
        validators=[int_list_validator],
        blank=True,
        max_length=99999,
        null=True
    )

    # List of (id, last_relevant_delta_id) for WfModules, pre-`forward()`.
    wf_module_delta_ids = ArrayField(
        ArrayField(
            models.IntegerField(),
            size=2
        ),
        null=True
    )

    @classmethod
    def affected_wf_modules(cls, wf_module) -> models.QuerySet:
        """
        QuerySet of all WfModules that may change as a result of this Delta.

        The default implementation _includes_ the passed `wf_module`.
        """
        return WfModule.objects.filter(workflow_id=wf_module.workflow_id,
                                       order__gte=wf_module.order,
                                       is_deleted=False)

    @classmethod
    def affected_wf_module_delta_ids(cls, wf_module) -> List[Tuple[int, int]]:
        return list(cls.affected_wf_modules(wf_module)
                    .values_list('id', 'last_relevant_delta_id'))

    def forward_affected_delta_ids(self, wf_module_DEPRECATED):
        """
        Write new last_relevant_delta_id to affected WfModules.

        (This usually includes self.wf_module.)
        """
        if (
            not hasattr(self, 'wf_module_delta_ids')
            or self.wf_module_delta_ids is None
        ):
            return self._forward_dependent_wf_module_versions_DEPRECATED(
                wf_module_DEPRECATED
            )

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

    def _save_wf_module_versions_in_memory_for_ws_notify(self, wf_module):
        """DEPRECATED: Save data, specifically for .ws_notify()."""
        self._changed_wf_module_versions = list(
            wf_module.dependent_wf_modules().values_list(
                'id',
                'last_relevant_delta_id'
            )
        )

    def _forward_dependent_wf_module_versions_DEPRECATED(self, wf_module):
        """
        Write new last_relevant_delta_id to `wf_module` and its dependents.
        """
        # Calculate "old" (pre-forward) last_revision_delta_ids, via DB query
        old_ids = [wf_module.last_relevant_delta_id] + list(
            wf_module.dependent_wf_modules().values_list(
                'last_relevant_delta_id',
                flat=True
            )
        )
        # Save them here -- we're about to overwrite them
        self.dependent_wf_module_last_delta_ids = ','.join(map(str, old_ids))

        # Overwrite them, for this one and previous ones
        wf_module.last_relevant_delta_id = self.id
        wf_module.dependent_wf_modules() \
            .update(last_relevant_delta_id=self.id)

        wf_module.save(update_fields=['last_relevant_delta_id'])

        self._save_wf_module_versions_in_memory_for_ws_notify(wf_module)

    def backward_affected_delta_ids(self, wf_module_DEPRECATED):
        """
        Write new last_relevant_delta_id to `wf_module` and its dependents.
        """
        if (
            not hasattr(self, 'wf_module_delta_ids')
            or self.wf_module_delta_ids is None
        ):
            return self._backward_dependent_wf_module_versions_DEPRECATED(
                wf_module_DEPRECATED
            )

        prev_ids = self.wf_module_delta_ids
 
        for wfm_id, delta_id in prev_ids:
            WfModule.objects.filter(id=wfm_id) \
                 .update(last_relevant_delta_id=delta_id)
 
            if hasattr(self, 'wf_module_id') and wfm_id == self.wf_module_id:
                # If we have a wf_module in memory, update it
                self.wf_module.last_relevant_delta_id = delta_id

        # for ws_notify()
        self._changed_wf_module_versions = [p for p in prev_ids]

    def _backward_dependent_wf_module_versions_DEPRECATED(self, wf_module):
        """
        Write new last_relevant_delta_id to `wf_module` and its dependents.
        """
        old_ids = [int(i) for i in
                   self.dependent_wf_module_last_delta_ids.split(',') if i]

        if not old_ids:
            # This is an old Delta: it does not know the last relevant delta
            # IDs. Set all IDs to an over-estimate.
            wf_module.last_relevant_delta_id = self.prev_delta_id or 0
            wf_module.dependent_wf_modules() \
                .update(last_relevant_delta_id=self.prev_delta_id or 0)

            self._save_wf_module_versions_in_memory_for_ws_notify(wf_module)
            return

        wf_module.last_relevant_delta_id = old_ids[0] or 0

        dependent_ids = \
            wf_module.dependent_wf_modules().values_list('id', flat=True)
        for wfm_id, maybe_delta_id in zip(dependent_ids, old_ids[1:]):
            if not wfm_id:
                raise ValueError('More delta IDs than WfModules')
            delta_id = maybe_delta_id or 0
            WfModule.objects.filter(id=wfm_id) \
                .update(last_relevant_delta_id=delta_id)

        self._save_wf_module_versions_in_memory_for_ws_notify(wf_module)
        wf_module.save(update_fields=['last_relevant_delta_id'])
