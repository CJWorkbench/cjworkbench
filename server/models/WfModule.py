from typing import Optional, Union
from django.contrib.postgres.fields import JSONField
from django.db import models
from cjworkbench.types import ProcessResult
from server import minio
from server.models import loaded_module
from .fields import ColumnsField
from .Params import Params
from .param_dtype import ParamDTypeDict
from .param_spec import ParamSpec
from .CachedRenderResult import CachedRenderResult
from .module_version import ModuleVersion
from .StoredObject import StoredObject
from .Tab import Tab
from .workflow import Workflow


class WfModule(models.Model):
    """An instance of a Module in a Workflow."""
    class Meta:
        ordering = ['order']

    def __str__(self):
        # Don't use DB queries here.
        return 'wf_module[%d] at position %d' % (self.id, self.order)

    @property
    def workflow(self):
        return Workflow.objects.get(tabs__wf_modules__id=self.id)

    @property
    def workflow_id(self):
        return self.tab.workflow_id

    @property
    def tab_slug(self):
        return self.tab.slug

    @property
    def uploaded_file_prefix(self):
        return f'wf-{self.workflow_id}/wfm-{self.id}/'

    @classmethod
    def live_in_workflow(cls,
                         workflow: Union[int, Workflow]) -> models.QuerySet:
        """
        QuerySet of not-deleted WfModules in `workflow`.

        You may specify `workflow` by its `pk` or as an object.

        Deleted WfModules and WfModules in deleted Tabs will omitted.
        """
        if isinstance(workflow, int):
            workflow_id = workflow
        else:
            workflow_id = workflow.pk

        return cls.objects.filter(
            tab__workflow_id=workflow_id,
            tab__is_deleted=False,
            is_deleted=False
        )

    tab = models.ForeignKey(
        Tab,
        related_name='wf_modules',
        on_delete=models.CASCADE
    )

    module_id_name = models.CharField(max_length=200, default='')

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

    is_deleted = models.BooleanField(default=False, null=False)

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

    cached_render_result_delta_id = models.IntegerField(null=True, blank=True)
    cached_render_result_status = models.CharField(
        null=True,
        blank=True,
        choices=[('ok', 'ok'), ('error', 'error'),
                 ('unreachable', 'unreachable')],
        max_length=20
    )
    cached_render_result_error = models.TextField(blank=True)
    # should be JSONField but we need backwards-compatibility
    cached_render_result_json = models.BinaryField(blank=True)
    cached_render_result_quick_fixes = JSONField(blank=True, default=list)
    cached_render_result_columns = ColumnsField(null=True, blank=True)
    cached_render_result_nrows = models.IntegerField(null=True, blank=True)

    # TODO once we auto-compute stale module outputs, nix is_busy -- it will
    # be implied by the fact that the cached output revision is wrong.
    is_busy = models.BooleanField(default=False, null=False)

    # There's fetch_error and there's cached_render_result_error.
    fetch_error = models.CharField('fetch_error', max_length=2000, blank=True)

    # Most-recent delta that may possibly affect the output of this module.
    # This isn't a ForeignKey because many deltas have a foreign key pointing
    # to the WfModule, so we'd be left with a chicken-and-egg problem.
    last_relevant_delta_id = models.IntegerField(default=0, null=False)

    # All current parameter values. This data has been validated at the time of writing
    # using ParamDType.validate() and module_version.param_schema. However it may not match
    # the current module version, and must be migrated when serialized.
    params = JSONField(default={})

    # Stores things like login information for Twitter and other APIs, must not be copied when duplicating the wf
    secrets = JSONField(default={})

    inprogress_file_upload_id = models.CharField(max_length=255, blank=True,
                                                 null=True, default=None)
    """
    S3 ID used by the client during upload.

    We store it here so we can authorize client requests. Users may only upload
    using for this WfModule using this UploadID. If the UploadID does not match
    the key the client sends, then S3 will complain.
    """

    inprogress_file_upload_key = models.CharField(max_length=100, null=True,
                                                  blank=True, default=None)
    """
    Key (in the minio.UserFilesBucket) matching `inprogress_file_upload_id`.

    We store the key so we can delete it. The Bucket is always
    minio.UserFilesBucket.

    TODO add constraint: (inprogress_file_upload_id IS NULL) = (key IS NULL).
    """

    inprogress_file_upload_last_accessed_at = models.DateTimeField(
        null=True,
        blank=True,
        default=None
    )
    """
    When the `upload_id` was created.

    Stale uploads can be deleted.
    """

    @property
    def module_version(self):
        if not hasattr(self, '_module_version'):
            try:
                self._module_version = ModuleVersion.objects.latest(
                    self.module_id_name
                )
            except ModuleVersion.DoesNotExist:
                self._module_version = None

        return self._module_version

    @property
    def output_status(self):
        """
        Return 'ok', 'busy', 'error' or 'unreachable'.

        'busy': render is pending
        'error': render produced an error and no table
        'unreachable': a previous module had 'error' so we will not run this
        'ok': render produced a table
        """
        crr = self.cached_render_result
        if crr is None:
            return 'busy'
        else:
            return crr.status

    @property
    def output_error(self):
        crr = self.cached_render_result
        if crr is None:
            return ''
        else:
            return crr.error

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
        try:
            return self.stored_objects.get(
                stored_at=self.stored_data_version
            ).get_table()
        except StoredObject.DoesNotExist:
            # Either self.stored_data_version is None or it has been deleted.
            return None

    def abort_inprogress_upload(self):
        """
        Delete data from S3 marked as in-progress uploads by  `wf_module`.

        * Delete incomplete multi-part upload
        * Delete completed upload, multipart or otherwise
        * Set `.inprogress_file_upload_*` to `None` (and save those fields)
        * Never raise `NoSuchUpload` or `FileNotFoundError`.
        """
        if (
            not self.inprogress_file_upload_id
            and not self.inprogress_file_upload_key
        ):
            return

        if self.inprogress_file_upload_id:
            # If we're uploading a multipart file, delete all parts
            try:
                minio.abort_multipart_upload(minio.UserFilesBucket,
                                             self.inprogress_file_upload_key,
                                             self.inprogress_file_upload_id)
            except minio.error.NoSuchUpload:
                pass
        if self.inprogress_file_upload_key:
            # If we _nearly_ completed a multipart upload, or if we wrote data via
            # regular upload but didn't mark it completed, delete the file
            try:
                minio.remove(minio.UserFilesBucket,
                             self.inprogress_file_upload_key)
            except FileNotFoundError:
                pass
        self.inprogress_file_upload_id = None
        self.inprogress_file_upload_key = None
        self.inprogress_file_upload_last_accessed_at = None
        self.save(update_fields=['inprogress_file_upload_id',
                                 'inprogress_file_upload_key',
                                 'inprogress_file_upload_last_accessed_at'])

    def get_fetch_result(self) -> Optional[ProcessResult]:
        """Load the result of a Fetch, if there was one."""
        table = self.retrieve_fetched_table()
        if table is None:
            return None

        return ProcessResult(table, self.fetch_error)

    def list_fetched_data_versions(self):
        return list(self.stored_objects
                    .order_by('-stored_at')
                    .values_list('stored_at', 'read'))

    def get_params(self) -> Params:
        """
        Hydrates our params field, plus secrets, into the Params dict which will be passed to
        the front end, and to the module's render() and fetch().

        Also handles migration from parameter sets created by previous versions of the module.

        Raise ValueError on _programmer_ error. That's usually the module author's problem
        (e.g. bad migration) and we'll want to display the error to the user so
        the user can pester the module author.
        """
        if self.module_version is None:
            return Params(ParamDTypeDict({}), {}, {})

        schema = self.module_version.param_schema
        lm = (
            # we don't import LoadedModule directly, because we'll mock it
            # out in unit tests.
            loaded_module.LoadedModule.for_module_version_sync(
                self.module_version
            )
        )
        # raises ValueError if there's a problem migrating, which indicates programmer error (probably module author)
        values = lm.migrate_params(schema, self.params)

        # "migrate" secrets: exactly the id_names specified in module_version
        # spec, with values maybe None
        secrets = {}
        for field in self.module_version.param_fields:
            if isinstance(field, ParamSpec.Secret):
                secrets[field.id_name] = self.secrets.get(field.id_name)

        return Params(schema, values, secrets)

    # re-render entire workflow when a module goes ready or error, on the
    # assumption that new output data is available
    def set_ready(self):
        self.is_busy = False
        self.fetch_error = ''
        self.save(update_fields=['is_busy', 'fetch_error'])

    # --- Duplicate ---
    # used when duplicating a whole workflow
    def duplicate(self, to_tab):
        to_workflow = to_tab.workflow

        # Initialize but don't save
        new_wfm = WfModule(
            tab=to_tab,
            module_id_name=self.module_id_name,
            fetch_error=self.fetch_error,
            stored_data_version=self.stored_data_version,
            order=self.order,
            notes=self.notes,
            is_collapsed=self.is_collapsed,
            auto_update_data=False,
            next_update=self.next_update,
            update_interval=self.update_interval,
            last_update_check=self.last_update_check,
            # to_workflow has exactly one delta, and that's the version of all
            # its modules. This is so we can cache render results. (Cached
            # render results require a delta ID.)
            last_relevant_delta_id=to_workflow.last_delta_id,
            params=self.params,
            secrets={}  # DO NOT COPY SECRETS
        )

        # Copy cached render result, if there is one.
        #
        # If we duplicate a Workflow mid-render, the cached render result might
        # not have any useful data. But that's okay: just kick off a new
        # render. The common case (all-rendered Workflow) will produce a
        # fully-rendered duplicate Workflow.
        cached_result = self.cached_render_result
        if cached_result is not None:
            # assuming file-copy succeeds, copy cached results.
            # Not using `new_wfm.cache_render_result(cached_result.result)`
            # because that would involve reading the whole thing.
            new_wfm.cached_render_result_delta_id = \
                new_wfm.last_relevant_delta_id
            for attr in ('status', 'error', 'json', 'quick_fixes', 'columns',
                         'nrows'):
                full_attr = f'cached_render_result_{attr}'
                setattr(new_wfm, full_attr, getattr(self, full_attr))

            new_wfm.save()  # so there is a new_wfm.id for parquet_key

            # Now new_wfm.cached_render_result will return a
            # CachedRenderResult, because all the DB values are set. It'll have
            # a .parquet_key ... but there won't be a file there (because we
            # never wrote it).
            parquet_key = new_wfm.cached_render_result.parquet_key

            try:
                minio.copy(
                    minio.CachedRenderResultsBucket,
                    parquet_key,
                    '%(Bucket)s/%(Key)s' % {
                        'Bucket': minio.CachedRenderResultsBucket,
                        'Key': cached_result.parquet_key,
                    }
                )
            except minio.error.NoSuchKey:
                # DB and filesystem are out of sync. CachedRenderResult handles
                # such cases gracefully. So `new_result` will behave exactly
                # like `cached_result`.
                pass
        else:
            new_wfm.save()

        # Duplicate the current stored data only, not the history
        if self.stored_data_version is not None:
            self.stored_objects.get(stored_at=self.stored_data_version) \
                    .duplicate(new_wfm)

        return new_wfm

    @property
    def cached_render_result(self) -> CachedRenderResult:
        """
        Build a CachedRenderResult with this WfModule's rendered output.

        Return `None` if there is a cached result but it is not fresh.

        Beware we build a CachedRenderResult without reading the actual Parquet
        file from disk. The _correct_ way of reading the Parquet file is:

            with wf_module.workflow.cooperative_lock():
                wf_module.refresh_from_db()  # re-read DB data
                crr = wf_module.cached_render_result  # uses DB columns
                dataframe = crr.read_dataframe()

        Without a lock and the refresh_from_db() within it, a
        CachedRenderResult's `.read_dataframe()` function will typically raise
        FileNotFoundError if called while a render is happening.
        """
        result = CachedRenderResult.from_wf_module(self)
        if result and result.delta_id != self.last_relevant_delta_id:
            return None
        return result

    def get_stale_cached_render_result(self):
        """
        Build a CachedRenderResult with this WfModule's stale rendered output.

        Return `None` if there is a cached result but it is fresh.
        """
        result = CachedRenderResult.from_wf_module(self)
        if result and result.delta_id == self.last_relevant_delta_id:
            return None
        return result

    def cache_render_result(self, delta_id: int,
                            result: ProcessResult) -> CachedRenderResult:
        """
        Save the given ProcessResult for later viewing.

        Raise AssertionError if `delta_id` is not what we expect.

        Since this alters data, be sure to call it within a lock:

            with wf_module.workflow.cooperative_lock():
                wf_module.refresh_from_db()
                wf_module.cache_render_result(delta_id, result)
        """
        assert delta_id == self.last_relevant_delta_id
        assert result is not None

        return CachedRenderResult.assign_wf_module(self, delta_id, result)

    def clear_cached_render_result(self) -> None:
        """
        Delete our CachedRenderResult, if it exists.

        This deletes the Parquet file from disk, _then_ empties relevant
        database fields and saves them (and only them).

        Since this alters data, be sure to call it within a lock:

            with wf_module.workflow.cooperative_lock():
                wf_module.refresh_from_db()
                wf_module.clear_cached_render_result()
        """
        CachedRenderResult.clear_wf_module(self)

    def delete(self, *args, **kwargs):
        if self.inprogress_file_upload_key:
            try:
                minio.abort_multipart_upload(minio.UserFilesBucket,
                                             self.inprogress_file_upload_key,
                                             self.inprogress_file_upload_id)
            except minio.error.NoSuchUpload:
                pass
        minio.remove_recursive(minio.UserFilesBucket, self.uploaded_file_prefix)
        CachedRenderResult.clear_wf_module(self)
        super().delete(*args, **kwargs)
