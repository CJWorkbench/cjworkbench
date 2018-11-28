import json
from django.db import models
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
    wf_module_delta_ids = ChangesWfModuleOutputs.wf_module_delta_ids

    def apply_order(self, order):
        # We validated Workflow IDs back in `.amend_create_args()`
        for record in order:
            WfModule.objects.filter(pk=record['id']).update(order=record['order'])

    def forward_impl(self):
        new_order = json.loads(self.new_order)

        self.apply_order(new_order)

        min_order = min(record['order'] for record in new_order)
        wf_module = self.workflow.live_wf_modules.get(order=min_order)
        self.forward_affected_delta_ids(wf_module)

    def backward_impl(self):
        new_order = json.loads(self.new_order)

        min_order = min(record['order'] for record in new_order)
        wf_module = self.workflow.live_wf_modules.get(order=min_order)
        self.backward_affected_delta_ids(wf_module)

        self.apply_order(json.loads(self.old_order))

    @classmethod
    def amend_create_kwargs(cls, *, workflow, new_order, **kwargs):
        # Validation: all id's and orders exist and orders are in range 0..n-1
        ids_orders = dict(workflow.live_wf_modules.values_list('id', 'order'))

        ids = [io[0] for io in ids_orders.items()]

        # Find first _order_ that gets a new WfModule. Only this and subsequent
        # WfModules will have their output modified.
        min_diff_order = None

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
            if (
                (min_diff_order is None or record['order'] < min_diff_order)
                and record['order'] != ids_orders[record['id']]
            ):
                min_diff_order = record['order']

        if min_diff_order is None:
            # If nothing was reordered, don't create this Command.
            return None

        new_orders = [record['order'] for record in new_order]
        new_orders.sort()
        if new_orders != list(range(0, len(new_orders))):
            raise ValueError('WfModule orders must be in range 0..n-1')

        # wf_module_delta_ids of affected WfModules will be all modules in the
        # database _before update_, starting at `order=min_diff_order`.
        #
        # This list of WfModule IDs will be the same (in a different order --
        # order doesn't matter) _after_ update.
        wf_module = workflow.live_wf_modules.get(order=min_diff_order)
        wf_module_delta_ids = cls.affected_wf_module_delta_ids(wf_module)

        return {
            **kwargs,
            'workflow': workflow,
            'old_order': json.dumps([{'id': io[0], 'order': io[1]}
                                     for io in ids_orders.items()]),
            'new_order': json.dumps(new_order),
            'wf_module_delta_ids': wf_module_delta_ids,
        }

    @classmethod
    async def create(cls, workflow, new_order):
        return await cls.create_impl(workflow=workflow, new_order=new_order)

    @property
    def command_description(self):
        return f'Reorder modules to {self.new_order}'
