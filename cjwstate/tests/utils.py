import asyncio
import hashlib
import io
import json
from typing import Any, Dict, Optional
from unittest.mock import Mock
import zipfile
from concurrent.futures import ThreadPoolExecutor
from django.db import connection, connections
from django.contrib.auth.models import User
from django.test import SimpleTestCase
from cjwkernel.types import RenderResult, FetchResult
from cjworkbench.sync import WorkbenchDatabaseSyncToAsync
from cjwstate import minio
from cjwstate.models.module_version import ModuleVersion
from cjwstate.models.module_registry import MODULE_REGISTRY
import cjwstate.modules
from cjwstate.modules.types import ModuleZipfile

# Connect to the database, on the main thread, and remember that connection
main_thread_connections = {name: connections[name] for name in connections}


def _inherit_main_thread_connections():
    for name in main_thread_connections:
        connections[name] = main_thread_connections[name]
        connections[name].inc_thread_sharing()


class DbTestCase(SimpleTestCase):
    allow_database_queries = True

    # run_with_async_db() tasks all share a single database connection. To
    # avoid concurrency issues, run them all in a single thread.
    #
    # Assumes DB connections may be passed between threads. (Only one thread
    # will make DB calls at a time.)
    async_executor = ThreadPoolExecutor(
        max_workers=1,
        thread_name_prefix="run_with_async_db_thread",
        initializer=_inherit_main_thread_connections,
    )

    def setUp(self):
        super().setUp()

        clear_db()
        clear_minio()

        # Set WorkbenchDatabaseSyncToAsync's executor on _all_ tests. This
        # supports testing sync functions that call async_to_sync().
        #
        # https://github.com/django/channels/issues/1091#issuecomment-436067763.
        self._old_executor = WorkbenchDatabaseSyncToAsync.executor
        WorkbenchDatabaseSyncToAsync.executor = self.async_executor

    def tearDown(self):
        # Don't bother clearing data in tearDown(). The next test that needs the
        # database will be running setUp() anyway, so extra clearing will only cost
        # time.
        WorkbenchDatabaseSyncToAsync.executor = self._old_executor

        super().tearDown()

    def run_with_async_db(self, task):
        """
        Runs async tasks, using the main thread's database connection.

        See
        https://github.com/django/channels/issues/1091#issuecomment-436067763.
        """
        # We'll execute with a 1-worker thread pool, shared between tests. We
        # need to limit to 1 worker, because all workers share the same
        # database connection.
        #
        # This hack is just for unit tests: the test suite will end with a
        # "delete the entire database" call, and we want it to succeed; that
        # means there need to be no other connections using the database.
        old_loop = asyncio.get_event_loop()
        asyncio.set_event_loop(None)
        try:
            return asyncio.run(task)
        finally:
            asyncio.set_event_loop(old_loop)


# Derive from this to perform all tests logged in
class LoggedInTestCase(DbTestCase):
    def setUp(self):
        super().setUp()

        self.user = create_test_user()
        self.client.force_login(self.user)


def create_test_user(
    username="username", email="user@example.org", password="password"
):
    return User.objects.create(username=username, email=email, password=password)


class DbTestCaseWithModuleRegistryAndMockKernel(DbTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cjwstate.modules.init_module_system()  # create module tempdir

    def setUp(self):
        super().setUp()

        self._old_kernel = cjwstate.modules.kernel
        self.kernel = cjwstate.modules.kernel = Mock()
        self.kernel.validate.return_value = None  # assume all modules are valid
        # default migrate_params() returns {}. If we wrote
        # `self.kernel.migrate_params.side_effect = lambda m, p: p`, then
        # callers couldn't use `self.kernel.migrate_params.return_value = ...`
        self.kernel.migrate_params.return_value = {}
        # No default implementation of self.kernel.fetch
        # No default implementation of self.kernel.render

    def tearDown(self):
        cjwstate.modules.kernel = self._old_kernel

        super().tearDown()


def create_module_zipfile(
    module_id: str = "testmodule",
    *,
    version: Optional[str] = None,
    spec_kwargs: Dict[str, Any] = {},
    python_code: str = "",
    html: Optional[str] = None,
    js_module: str = "",
) -> ModuleZipfile:
    """
    Create a ModuleZipfile, stored in the database and minio.

    If `version` is not supplied, generate one using the sha1 of the zipfile.
    This is usually what you want: minio reads on overwrites are _eventually_
    consistent, so if you 1. write a file; 2. overwrite it; and 3. read it, the
    read might result in the file from step 1 or the file from step 2. A sha1
    version means overwrites will never modify data, solving the problem.
    """
    spec = {
        "id_name": module_id,
        "name": "Test Module",
        "category": "Clean",
        "parameters": [],
        **spec_kwargs,
    }

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, mode="w") as zf:
        zf.writestr(module_id + ".yaml", json.dumps(spec))
        zf.writestr(module_id + ".py", python_code.encode("utf-8"))
        if html is not None:
            zf.writestr(module_id + ".html", html.encode("utf-8"))
        if js_module:
            zf.writestr(module_id + ".js", js_module.encode("utf-8"))
    data = bytes(bio.getbuffer())
    if version is None:
        sha1 = hashlib.sha1()
        sha1.update(data)
        version = sha1.hexdigest()

    minio.put_bytes(
        minio.ExternalModulesBucket,
        "%s/%s.%s.zip" % (module_id, module_id, version),
        data,
    )
    ModuleVersion.objects.create(
        id_name=module_id, source_version_hash=version, spec=spec, js_module=js_module
    )
    return MODULE_REGISTRY.latest(module_id)


_Tables = [
    "server_aclentry",
    "server_addmodulecommand",
    "server_addtabcommand",
    "server_changedataversioncommand",
    "server_changeparameterscommand",
    "server_changewfmodulenotescommand",
    "server_changeworkflowtitlecommand",
    "server_deletemodulecommand",
    "server_deletetabcommand",
    "server_duplicatetabcommand",
    "server_reordermodulescommand",
    "server_reordertabscommand",
    "server_settabnamecommand",
    "server_initworkflowcommand",
    "server_delta",
    "server_moduleversion",
    "server_storedobject",
    "server_uploadedfile",
    "server_inprogressupload",
    "server_wfmodule",
    "server_tab",
    "server_workflow",
    "django_session",
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
    "cjworkbench_userprofile",
    "auth_user",
    "auth_user_groups",
    "auth_user_user_permissions",
]


def clear_db():
    deletes = [f"t{i} AS (DELETE FROM {table})" for i, table in enumerate(_Tables)]
    sql = f"WITH {', '.join(deletes)} SELECT 1"
    with connection.cursor() as c:
        c.execute(sql)


def clear_minio():
    buckets = (
        minio.UserFilesBucket,
        minio.StoredObjectsBucket,
        minio.ExternalModulesBucket,
        minio.CachedRenderResultsBucket,
    )

    if not hasattr(clear_minio, "_initialized"):
        # Ensure buckets exist -- only on first call
        for bucket in buckets:
            minio.ensure_bucket_exists(bucket)
        clear_minio._initialized = True

    for bucket in buckets:
        minio.remove_recursive(bucket, "/", force=True)
