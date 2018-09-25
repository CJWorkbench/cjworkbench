# A Command changes the state of a Workflow, by producing and executing a Delta
import json
import logging
import threading  # FIXME nix this -- it can't work for our multi-process env
from django.core.validators import int_list_validator
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from server.models import WfModule, ParameterVal, Delta

logger = logging.getLogger(__name__)

# --- Utilities ---

# Give the new WfModule an 'order' of insert_before, and add 1 to all following WfModules
def insert_wf_module(wf_module, workflow, insert_before):
    if insert_before < 0:
        insert_before = 0

    # This algorithm is deliberately robust to non-standard ordering (not 0..n-1)
    pos = 0
    for wfm in WfModule.objects.filter(workflow=workflow):
        if pos == insert_before:
            pos += 1
        if wfm.order != pos:
            wfm.order = pos
            wfm.save()
        pos += 1

    # normalize insert_before so it's always the index where the new WfModule ends up
    if insert_before > pos:
        insert_before = pos

    # save new position if needed
    if wf_module.order != insert_before:
        wf_module.order = insert_before


# Forces canonical values of 'order' field: 0..n-1
# Used after deleting a WfModule
def renumber_wf_modules(workflow):
    pos = 0
    for wfm in WfModule.objects.filter(workflow=workflow):
        if wfm.order != pos:
            wfm.order = pos
            wfm.save()
        pos += 1


class _ChangesWfModuleOutputs:
    # List of wf_module.last_relevant_delta_id from _before_ .forward() was
    # called, for *this* wf_module and the ones *after* it.
    dependent_wf_module_last_delta_ids = models.CharField(
        validators=[int_list_validator],
        blank=True,
        max_length=99999
    )

    def save_wf_module_versions_in_memory_for_ws_notify(self, wf_module):
        """Save data, specifically for .ws_notify()."""
        self._changed_wf_module_versions = dict(
            wf_module.dependent_wf_modules().values_list(
                'id',
                'last_relevant_delta_id'
            )
        )

    def forward_dependent_wf_module_versions(self, wf_module):
        """
        Write new last_relevant_delta_id to `wf_module` and its dependents.

        You must call `wf_module.save()` after calling this method. Dependents
        will be saved as a side-effect.
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

        self.save_wf_module_versions_in_memory_for_ws_notify(wf_module)

    def backward_dependent_wf_module_versions(self, wf_module):
        """
        Write new last_relevant_delta_id to `wf_module` and its dependents.

        You must call `wf_module.save()` after calling this method. Dependents
        will be saved as a side-effect.
        """
        old_ids = [int(i) for i in
                   self.dependent_wf_module_last_delta_ids.split(',') if i]

        if not old_ids:
            # This is an old Delta: it does not know the last relevant delta
            # IDs. Set all IDs to an over-estimate.
            wf_module.last_relevant_delta_id = self.prev_delta_id or 0
            wf_module.dependent_wf_modules() \
                .update(last_relevant_delta_id=self.prev_delta_id or 0)

            self.save_wf_module_versions_in_memory_for_ws_notify(wf_module)
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

        self.save_wf_module_versions_in_memory_for_ws_notify(wf_module)



# --- Commands ----

# The only tricky part AddModule is what we do with the module in backward()
# We detach the WfModule from the workflow, but keep it around for possible later forward()
class AddModuleCommand(Delta, _ChangesWfModuleOutputs):
    # must not have cascade on WfModule because we may delete it first when we are deleted
    wf_module = models.ForeignKey(WfModule, null=True, default=None,
                                  blank=True, on_delete=models.SET_DEFAULT)
    order = models.IntegerField()
    applied = models.BooleanField(default=True, null=False)             # is this command currently applied?
    selected_wf_module = models.IntegerField(null=True, blank=True)     # what was selected before we were added?
    dependent_wf_module_last_delta_ids = \
        _ChangesWfModuleOutputs.dependent_wf_module_last_delta_ids

    def forward_impl(self):
        self.selected_wf_module = self.workflow.selected_wf_module
        insert_wf_module(self.wf_module, self.workflow, self.order)     # may alter wf_module.order without saving
        self.wf_module.workflow = self.workflow                         # attach to workflow
        self.forward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.save()
        self.workflow.selected_wf_module = self.wf_module.order
        self.workflow.save()
        self.applied = True
        self.save()

    def backward_impl(self):
        self.backward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.workflow = None                                  # detach from workflow
        self.wf_module.save()
        # [adamhooper, 2018-06-19] I don't think there's any hope we can
        # actually restore selected_wf_module correctly, because sometimes we
        # update it without a command. But we still need to set
        # workflow.selected_wf_module to a _valid_ integer if the
        # currently-selected module is the one we're deleting now and is also
        # the final wf_module in the list.
        self.workflow.selected_wf_module = self.selected_wf_module      # go back to old selection when deleted
        self.workflow.save()
        renumber_wf_modules(self.workflow)                              # fix up ordering on the rest
        self.applied = False
        self.save()

    @staticmethod
    async def create(workflow, module_version, insert_before):
        with workflow.cooperative_lock():
            newwfm = WfModule.objects.create(workflow=None,
                                             module_version=module_version,
                                             order=insert_before,
                                             is_collapsed=False)
            newwfm.create_default_parameters()

            delta = await Delta.create_impl(AddModuleCommand,
                                            workflow=workflow,
                                            wf_module=newwfm,
                                            order=insert_before)

        return delta

    @property
    def command_description(self):
        return f'Add WfModule {self.wf_module}'


# When we are deleted, delete the module if it's not in use by the Workflow (if we are *not* currently applied)
@receiver(pre_delete, sender=AddModuleCommand, dispatch_uid='addmodulecommand')
def addmodulecommand_delete_callback(sender, instance, **kwargs):
    if instance.applied == False:
        instance.wf_module.delete()


delete_lock = threading.Lock()


# Deletion works by simply "orphaning" the wf_module, setting its workflow reference to null
class DeleteModuleCommand(Delta, _ChangesWfModuleOutputs):
    # must not have cascade on WfModule because we may delete it first when we are deleted
    wf_module = models.ForeignKey(WfModule, null=True, default=None, blank=True, on_delete=models.SET_DEFAULT)
    selected_wf_module = models.IntegerField(null=True, blank=True)
    applied = models.BooleanField(default=True, null=False)             # is this command currently applied?
    dependent_wf_module_last_delta_ids = \
        _ChangesWfModuleOutputs.dependent_wf_module_last_delta_ids

    def forward_impl(self):
        # If we are deleting the selected module, then set the previous module
        # in stack as selected (behavior same as in workflow-reducer.js)
        selected = self.workflow.selected_wf_module
        if selected is not None and selected >= self.wf_module.order:
            selected -= 1
            if selected >= 0:
                self.workflow.selected_wf_module = selected
            else:
                self.workflow.selected_wf_module = None
            self.workflow.save()

        self.forward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.workflow = None                                  # detach from workflow
        self.wf_module.save()
        renumber_wf_modules(self.workflow)                              # fix up ordering on the rest
        self.applied = True
        self.save()

    def backward_impl(self):
        insert_wf_module(self.wf_module, self.workflow, self.wf_module.order)
        self.wf_module.workflow = self.workflow                         # attach to workflow
        self.backward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.save()
        # [adamhooper, 2018-06-19] I don't think there's any hope we can
        # actually restore selected_wf_module correctly, because sometimes we
        # update it without a command. But I think focusing the restored module
        # is something a user could expect.
        self.workflow.selected_wf_module = self.selected_wf_module
        self.workflow.save()
        self.applied = False
        self.save()

    @staticmethod
    async def create(wf_module):
        # critical section to make double delete check work correctly
        with delete_lock:
            workflow = wf_module.workflow
            if workflow is None:
                return None     # this wfm was already deleted, do nothing

            delta = await Delta.create_impl(
                DeleteModuleCommand,
                workflow=workflow,
                wf_module=wf_module,
                selected_wf_module=workflow.selected_wf_module
            )

            return delta

    @property
    def command_description(self):
        return f'Delete WfModule {self.wf_module}'

# When we are deleted, delete the module if it's not in use by the Workflow (i.e. if we are currently applied)
@receiver(pre_delete, sender=DeleteModuleCommand, dispatch_uid='deletemodulecommand')
def deletemodulecommand_delete_callback(sender, instance, **kwargs):
    if instance.applied == True:
        try:
            # We've had cases where two DeleteModuleCommands pointed to the same wf, due to race conditions
            # (now fixed via delete_lock). To prevent future similar fails, wrap the delete in a try
            instance.wf_module.delete()
        except Exception as e:
            logger.exception("Error deleting wf_module for DeleteModuleCommand " + str(instance))


class ReorderModulesCommand(Delta, _ChangesWfModuleOutputs):
    # For simplicity and compactness, we store the order of modules as json strings
    # in the same format as the patch request: [ { id: x, order: y}, ... ]
    old_order = models.TextField()
    new_order = models.TextField()
    dependent_wf_module_last_delta_ids = \
        _ChangesWfModuleOutputs.dependent_wf_module_last_delta_ids

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

    @staticmethod
    async def create(workflow, new_order):
        # Validation: all id's and orders exist and orders are in range 0..n-1
        wfms = WfModule.objects.filter(workflow=workflow)

        ids = [wfm.id for wfm in wfms]
        for record in new_order:
            if not isinstance(record, dict):
                raise ValueError('JSON data must be an array of {id:x, order:y} objects')
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

        # Looks good, let's reorder
        delta = await Delta.create_impl(
            ReorderModulesCommand,
            workflow=workflow,
            old_order=json.dumps([{'id': wfm.id, 'order': wfm.order} for wfm in wfms]),
            new_order=json.dumps(new_order)
        )

        return delta

    @property
    def command_description(self):
        return f'Reorder modules to {self.new_order}'


class ChangeDataVersionCommand(Delta, _ChangesWfModuleOutputs):
    wf_module = models.ForeignKey(WfModule, null=True, default=None, blank=True, on_delete=models.SET_DEFAULT)
    old_version = models.DateTimeField('old_version', null=True)    # may not have had a previous version
    new_version = models.DateTimeField('new_version')
    dependent_wf_module_last_delta_ids = \
        _ChangesWfModuleOutputs.dependent_wf_module_last_delta_ids

    def forward_impl(self):
        self.wf_module.set_fetched_data_version(self.new_version)
        self.forward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.save()

    def backward_impl(self):
        self.backward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.save()
        self.wf_module.set_fetched_data_version(self.old_version)

    @staticmethod
    async def create(wf_module, version):
        delta = await Delta.create_impl(
            ChangeDataVersionCommand,
            wf_module=wf_module,
            new_version=version,
            old_version=wf_module.get_fetched_data_version(),
            workflow=wf_module.workflow
        )

        return delta

    @property
    def command_description(self):
        return f'Change {self.wf_module.get_module_name()} data version to {self.version}'


class ChangeParameterCommand(Delta, _ChangesWfModuleOutputs):
    parameter_val = models.ForeignKey(ParameterVal, null=True, default=None,
                                      blank=True, on_delete=models.SET_DEFAULT)
    new_value = models.TextField('new_value')
    old_value = models.TextField('old_value')
    dependent_wf_module_last_delta_ids = \
        _ChangesWfModuleOutputs.dependent_wf_module_last_delta_ids

    # Implement wf_module for self.ws_notify()
    @property
    def wf_module(self):
        return self.parameter_val.wf_module

    @property
    def wf_module_id(self):
        return self.parameter_val.wf_module_id

    def forward_impl(self):
        self.parameter_val.set_value(self.new_value)

        self.forward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.save()

    def backward_impl(self):
        self.backward_dependent_wf_module_versions(self.wf_module)
        self.wf_module.save()

        self.parameter_val.set_value(self.old_value)

    @staticmethod
    async def create(parameter_val, value):
        workflow = parameter_val.wf_module.workflow

        delta = await Delta.create_impl(
            ChangeParameterCommand,
            parameter_val=parameter_val,
            new_value=value,
            old_value=parameter_val.get_value(),
            workflow=workflow
        )

        return delta

    @property
    def command_description(self):
        return f'Change param {self.parameter_val} to {self.new_value}'


class ChangeWorkflowTitleCommand(Delta):
    new_value = models.TextField('new_value')
    old_value = models.TextField('old_value')

    def forward_impl(self):
        self.workflow.name = self.new_value
        self.workflow.save(update_fields=['name'])

    def backward_impl(self):
        self.workflow.name = self.old_value
        self.workflow.save(update_fields=['name'])

    @staticmethod
    async def create(workflow, name):
        old_name = workflow.name

        delta = await Delta.create_impl(
            ChangeWorkflowTitleCommand,
            workflow=workflow,
            new_value=name,
            old_value=old_name
        )

        return delta

    @property
    def command_description(self):
        return f'Change workflow name to {self.new_value}'


class ChangeWfModuleNotesCommand(Delta):
    wf_module = models.ForeignKey(WfModule, null=True, default=None,
                                  blank=True, on_delete=models.SET_DEFAULT)
    new_value = models.TextField('new_value')
    old_value = models.TextField('old_value')

    def forward_impl(self):
        self.wf_module.notes = self.new_value
        self.wf_module.save()

    def backward_impl(self):
        self.wf_module.notes = self.old_value
        self.wf_module.save()

    @staticmethod
    async def create(wf_module, notes):
        old_value = wf_module.notes if wf_module.notes else ''

        delta = await Delta.create_impl(
            ChangeWfModuleNotesCommand,
            workflow=wf_module.workflow,
            wf_module=wf_module,
            new_value=notes,
            old_value=old_value
        )

        return delta

    @property
    def command_description(self):
        return f'Change WfModule note to {self.new_value}'


class ChangeWfModuleUpdateSettingsCommand(Delta):
    wf_module = models.ForeignKey(WfModule, null=True, default=None,
                                  blank=True, on_delete=models.SET_DEFAULT)
    new_auto = models.BooleanField()
    old_auto = models.BooleanField()
    new_next_update = models.DateField(null=True)
    old_next_update = models.DateField(null=True)
    new_update_interval = models.IntegerField()
    old_update_interval = models.IntegerField()

    def forward_impl(self):
        self.wf_module.auto_update_data = self.new_auto
        self.wf_module.next_update = self.new_next_update
        self.wf_module.update_interval = self.new_update_interval
        self.wf_module.save()

    def backward_impl(self):
        self.wf_module.auto_update_data = self.old_auto
        self.wf_module.next_update = self.old_next_update
        self.wf_module.update_interval = self.old_update_interval
        self.wf_module.save()

    @staticmethod
    async def create(wf_module, auto_update_data,
                     next_update, update_interval):
        delta = await Delta.create_impl(
            ChangeWfModuleUpdateSettingsCommand,
            workflow=wf_module.workflow,
            wf_module=wf_module,
            old_auto=wf_module.auto_update_data,
            new_auto=auto_update_data,
            old_next_update=wf_module.next_update,
            new_next_update=next_update,
            old_update_interval=wf_module.update_interval,
            new_update_interval=update_interval
        )

        return delta

    @property
    def command_description(self):
        return f'Change Workflow update settings'
