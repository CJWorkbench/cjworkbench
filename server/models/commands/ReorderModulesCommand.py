import json
from django.db import models
from django.dispatch import receiver
from server.models import Delta, WfModule
from .util import ChangesWfModuleOutputs


class ReorderModulesCommand(Delta, ChangesWfModuleOutputs):
    # For simplicity and compactness, we store the order of modules as json
    # strings in the same format as the patch request:
    # [ { id: x, order: y}, ... ]
    old_order = models.TextField()
    new_order = models.TextField()
    dependent_wf_module_last_delta_ids = \
        ChangesWfModuleOutputs.dependent_wf_module_last_delta_ids

    def apply_order(self, order):
        for record in order:
            # may raise WfModule.DoesNotExist if bad ID's
            wfm = self.workflow.wf_modules.get(pk=record['id'])
            if wfm.order != record['order']:
                wfm.order = record['order']
                wfm.save()

    def forward_impl(self):
        new_order = json.loads(self.new_order)

        self.apply_order(new_order)

        min_order = min(record['order'] for record in new_order)
        wf_module = self.workflow.wf_modules.get(order=min_order)
        self.forward_dependent_wf_module_versions(wf_module)
        wf_module.save()

    def backward_impl(self):
        new_order = json.loads(self.new_order)

        min_order = min(record['order'] for record in new_order)
        wf_module = self.workflow.wf_modules.get(order=min_order)
        self.backward_dependent_wf_module_versions(wf_module)
        wf_module.save()

        self.apply_order(json.loads(self.old_order))

    @classmethod
    def amend_create_kwargs(cls, *, workflow, new_order, **kwargs):
        # Validation: all id's and orders exist and orders are in range 0..n-1
        wfms = list(workflow.wf_modules.all())

        ids = [wfm.id for wfm in wfms]
        for record in new_order:
            if not isinstance(record, dict):
                raise ValueError(
                    'JSON data must be an array of {id:x, order:y} objects'
                )
            if 'id' not in record:
                raise ValueError('Missing WfModule id')
            if record['id'] not in ids:
                raise ValueError('Bad WfModule id')
            if 'order' not in record:
                raise ValueError('Missing WfModule order')

        orders = [record['order'] for record in new_order]
        orders.sort()
        if orders != list(range(0, len(orders))):
            raise ValueError('WfModule orders must be in range 0..n-1')

        return {
            **kwargs,
            'workflow': workflow,
            'old_order': json.dumps([{'id': wfm.id, 'order': wfm.order}
                                     for wfm in wfms]),
            'new_order': json.dumps(new_order),
        }

    @classmethod
    async def create(cls, workflow, new_order):
        return await cls.create_impl(workflow=workflow, new_order=new_order)

    @property
    def command_description(self):
        return f'Reorder modules to {self.new_order}'


