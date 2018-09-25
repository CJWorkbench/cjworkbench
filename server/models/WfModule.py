import json
from typing import List, Optional
from django.db import models
from server import websockets
from server.modules.types import Column, ProcessResult
from .CachedRenderResult import CachedRenderResult
from .ModuleVersion import ModuleVersion
from .ParameterSpec import ParameterSpec
from .ParameterVal import ParameterVal
from .StoredObject import StoredObject


# ---- Parameter Dictionary Sanitization ----

# Column sanitization: remove invalid column names
# We can get bad column names if the module is reordered, for example
# Never make the render function deal with this.
def _sanitize_column_param(pval, table_cols):
    col = pval.get_value()
    if col in table_cols:
        return col
    else:
        return ''


def _sanitize_multicolumn_param(pval, table_cols):
    cols = pval.get_value().split(',')
    cols = [c.strip() for c in cols]
    cols = [c for c in cols if c in table_cols]

    return ','.join(cols)


class WfModule(models.Model):
    """An instance of a Module in a Workflow."""
    class Meta:
        ordering = ['order']

    def __str__(self):
        if self.workflow is not None:
            wfstr = ' - workflow: ' + self.workflow.__str__()
        else:
            wfstr = ' - deleted from workflow'
        return self.get_module_name() + ' - id: ' + str(self.id) + wfstr

    def create_parameter_dict(self, table):
        """Present parameters as a dict, with some inconsistent munging.

        A `column` parameter that refers to an invalid column will be renamed
        to the empty string.

        A `multicolumn` parameter will have its values `strip()`ed and have
        invalid columns removed.
        """
        pdict = {}
        for p in self.parameter_vals.all().prefetch_related('parameter_spec'):
            type = p.parameter_spec.type
            id_name = p.parameter_spec.id_name

            if type == ParameterSpec.COLUMN:
                pdict[id_name] = _sanitize_column_param(p, table.columns)
            elif type == ParameterSpec.MULTICOLUMN:
                pdict[id_name] = _sanitize_multicolumn_param(p, table.columns)
            else:
                pdict[id_name] = p.get_value()

        return pdict

    # --- Fields ----
    workflow = models.ForeignKey(
        'Workflow',
        related_name='wf_modules',
        null=True,                     # null means this is a deleted WfModule
        on_delete=models.CASCADE)      # delete WfModule if Workflow deleted

    module_version = models.ForeignKey(
        ModuleVersion,
        related_name='wf_modules',
        on_delete=models.SET_NULL,
        null=True  # goes null if referenced Module deleted
    )

    order = models.IntegerField()

    notes = models.TextField(
        null=True,
        blank=True)

    stored_data_version = models.DateTimeField(
        null=True,
        blank=True)                      # we may not have stored data

    # drives whether the module is expanded or collapsed on the front-end.
    is_collapsed = models.BooleanField(
        default=False,
        blank=False,
        null=False
    )

    # For modules that fetch data: how often do we check for updates, and do we
    # switch to latest version automatically
    auto_update_data = models.BooleanField(default=False)

    # when should next update run?
    next_update = models.DateTimeField(null=True, blank=True)
    # time in seconds between updates, default of 1 day
    update_interval = models.IntegerField(default=86400)
    last_update_check = models.DateTimeField(null=True, blank=True)

    # true means, 'email owner when output changes'
    notifications = models.BooleanField(default=False)

    # true means user has not acknowledged email
    has_unseen_notification = models.BooleanField(default=False)

    # Our undo mechanism assigns None to self.workflow_id sometimes. We need to
    # also store the ID, so we can reference it while deleting.
    cached_render_result_workflow_id = models.IntegerField(null=True,
                                                           blank=True)
    cached_render_result_delta_id = models.IntegerField(null=True, blank=True)
    cached_render_result_error = models.TextField(blank=True)
    cached_render_result_json = models.BinaryField(blank=True)

    READY = "ready"
    BUSY = "busy"
    ERROR = "error"

    # TODO once we auto-compute stale module outputs, nix is_busy -- it will
    # be implied by the fact that the cached output revision is wrong.
    is_busy = models.BooleanField(default=False, null=False)

    # There's fetch_error and there's cached_render_result_error.
    fetch_error = models.CharField('fetch_error', max_length=2000, blank=True)

    # Most-recent delta that may possibly affect the output of this module.
    # This isn't a ForeignKey because many deltas have a foreign key pointing
    # to the WfModule, so we'd be left with a chicken-and-egg problem.
    last_relevant_delta_id = models.IntegerField(default=0, null=False)

    # ---- Utilities ----

    # navigate through a stack
    def previous_in_stack(self):
        if self.order == 0:
            return None
        else:
            return WfModule.objects.get(workflow=self.workflow,
                                        order=self.order-1)

    def dependent_wf_modules(self) -> List['WfModule']:
        """QuerySet of all WfModules that come after this one, in order."""
        return self.workflow.wf_modules.filter(order__gt=self.order)

    def get_module_name(self):
        if self.module_version is not None:
            return self.module_version.module.name
        else:
            return 'Missing module'  # deleted from server

    @property
    def status(self):
        """
        Return READY, BUSY or ERROR.

        BUSY: is_busy is True
        ERROR: fetch_error or cached_render_result_error is set
        READY: anything else
        """
        if self.is_busy:
            return WfModule.BUSY
        elif self.fetch_error or self.cached_render_result_error:
            return WfModule.ERROR
        else:
            return WfModule.READY

    @property
    def error_msg(self):
        if self.is_busy:
            return ''
        return self.fetch_error or self.cached_render_result_error or ''

    # ---- Authorization ----
    # User can access wf_module if they can access workflow
    def request_authorized_read(self, request):
        return self.workflow.request_authorized_read(request)

    def request_authorized_write(self, request):
        return self.workflow.request_authorized_write(request)

    # ---- Data versions ----
    # Modules that fetch data, like Load URL or Twitter or scrapers, store
    # versions of all previously fetched data

    # Note: does not switch to new version automatically
    def store_fetched_table(self, table):
        stored_object = StoredObject.create_table(self, table)
        return stored_object.stored_at

    # Compares against latest version (which may not be current version)
    # Note: does not switch to new version automatically
    def store_fetched_table_if_different(self, table, metadata=''):
        reference_so = StoredObject.objects.filter(
            wf_module=self
        ).order_by('-stored_at').first()

        new_version = StoredObject.create_table_if_different(self,
                                                             reference_so,
                                                             table,
                                                             metadata=metadata)
        return new_version.stored_at if new_version else None

    def retrieve_fetched_table(self):
        if self.stored_data_version:
            return StoredObject.objects.get(
                wf_module=self,
                stored_at=self.stored_data_version
            ).get_table()
        else:
            return None

    # versions are ISO datetimes
    def get_fetched_data_version(self):
        return self.stored_data_version

    # Like all mutators, this should usually be wrapped in a Command so it is
    # undoable. In this case, a ChangeDataVersionCommand
    def set_fetched_data_version(self, version):
        if version is None or not \
            StoredObject.objects.filter(wf_module=self,
                                        stored_at=version).exists():
            raise ValueError('No such stored data version')

        self.stored_data_version = version
        self.save()

    def list_fetched_data_versions(self):
        return list(StoredObject.objects.filter(wf_module=self)
                                        .order_by('-stored_at')
                                        .values_list('stored_at', 'read'))

    # --- Parameter acessors ----
    # Hydrates ParameterVal objects from ParameterSpec objects
    def create_default_parameters(self):
        for pspec in ParameterSpec.objects \
                     .filter(module_version__id=self.module_version_id) \
                     .all():
            pv = ParameterVal(wf_module=self, parameter_spec=pspec)
            pv.init_from_spec()
            pv.save()

    def get_parameter_val(self, name, expected_type):
        try:
            pspec = ParameterSpec.objects.get(
                id_name=name,
                module_version__id=self.module_version_id
            )
        except ParameterSpec.DoesNotExist:
            raise ValueError(
                f'Request for non-existent {expected_type} parameter {name}'
            )

        if pspec.type != expected_type:
            raise ValueError(
                f'Request for {expected_type} parameter {name} '
                f'but actual type is {pspec.type}'
            )

        pval = self.parameter_vals.get(parameter_spec=pspec)
        return pval

    # Retrieve current parameter values.
    # Should never throw ValueError on type conversions because
    # ParameterVal.set_value coerces
    def get_param_raw(self, name, expected_type):
        pval = self.get_parameter_val(name, expected_type)
        return pval.value

    def get_param(self, name, expected_type):
        pval = self.get_parameter_val(name, expected_type)
        return pval.get_value()

    def get_param_string(self, name):
        return self.get_param(name, ParameterSpec.STRING)

    def get_param_integer(self, name):
        return self.get_param(name, ParameterSpec.INTEGER)

    def get_param_float(self, name):
        return self.get_param(name, ParameterSpec.FLOAT)

    def get_param_checkbox(self, name):
        return self.get_param(name, ParameterSpec.CHECKBOX)

    def get_param_radio_idx(self, name):
        return self.get_param(name, ParameterSpec.RADIO)

    def get_param_radio_string(self, name):
        pval = self.get_parameter_val(name, ParameterSpec.RADIO)
        return pval.selected_radio_item_string()

    def get_param_menu_idx(self, name):
        return self.get_param(name, ParameterSpec.MENU)

    def get_param_menu_string(self, name):
        pval = self.get_parameter_val(name, ParameterSpec.MENU)
        return pval.selected_menu_item_string()

    def get_param_secret_secret(self, id_name: str):
        """Get a secret's "secret" data, or None."""
        pval = self.get_parameter_val(id_name, ParameterSpec.SECRET)

        # Don't use get_value(), since it hides the secret. (We're paranoid
        # about leaking users' secrets.)
        json_val = pval.value
        if json_val:
            try:
                val = json.loads(json_val)
            except json.decoder.JSONDecodeError:
                return None

            return val['secret']
        else:
            return None

    def get_param_column(self, name):
        return self.get_param(name, ParameterSpec.COLUMN)

    def get_param_multicolumn(self, name):
        return self.get_param(name, ParameterSpec.MULTICOLUMN)

    # --- Status ----
    # set error codes and status lights, notify client of changes

    # busy just changes the light on a single module, no need to reload entire
    # workflow
    async def set_busy(self):
        self.is_busy = True
        self.save(update_fields=['is_busy'])
        await websockets.ws_client_wf_module_status_async(self, self.status)

    # re-render entire workflow when a module goes ready or error, on the
    # assumption that new output data is available
    def set_ready(self):
        self.is_busy = False
        self.fetch_error = ''
        self.save()

    # --- Duplicate ---
    # used when duplicating a whole workflow
    def duplicate(self, to_workflow):
        new_wfm = WfModule.objects.create(
            workflow=to_workflow,
            module_version=self.module_version,
            fetch_error=self.fetch_error,
            stored_data_version=self.stored_data_version,
            order=self.order,
            notes=self.notes,
            is_collapsed=self.is_collapsed,
            auto_update_data=self.auto_update_data,
            next_update=self.next_update,
            update_interval=self.update_interval,
            last_update_check=self.last_update_check,
            cached_render_result_workflow_id=None,
            cached_render_result_delta_id=None,
            cached_render_result_error='',
            cached_render_result_json=b'null'
        )

        # copy all parameter values
        for pv in ParameterVal.objects.filter(wf_module=self):
            pv.duplicate(new_wfm)

        # Duplicate the current stored data only, not the history
        if self.stored_data_version is not None:
            self.stored_objects.get(stored_at=self.stored_data_version) \
                    .duplicate(new_wfm)

        return new_wfm

    def get_cached_render_result(self) -> CachedRenderResult:
        """Load this WfModule's CachedRenderResult from disk."""
        return CachedRenderResult.from_wf_module(self)

    def cache_render_result(self, delta_id: Optional[int],
                            result: ProcessResult) -> CachedRenderResult:
        """Save the given ProcessResult (or None) for later viewing."""
        return CachedRenderResult.assign_wf_module(self, delta_id, result)

    def get_cached_output_columns(self) -> List[Column]:
        """
        If the cached result is valid, return a list of columns.

        This doesn't instantiate any DataFrames, so it's cheap. (It does read
        a file header from disk, though.)
        """
        cached_result = self.get_cached_render_result()
        if not cached_result:
            return None
        if cached_result.delta_id != self.last_relevant_delta_id:
            return None

        return cached_result.columns

    def delete(self, *args, **kwargs):
        self.cache_render_result(None, None)
        super().delete(*args, **kwargs)
