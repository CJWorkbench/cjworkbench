import asyncio
from concurrent.futures import ThreadPoolExecutor
import pathlib
from typing import Dict, Iterable, List, Optional
from django.db import connection, connections
from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase
from cjworkbench.sync import WorkbenchDatabaseSyncToAsync
from server import minio
import os
import io
import pandas as pd

# --- Test data ----

mock_csv_text = 'Month,Amount\nJan,10\nFeb,20'
mock_csv_table = pd.read_csv(io.StringIO(mock_csv_text))

mock_xlsx_path = os.path.join(settings.BASE_DIR,
                              'server/tests/test_data/test.xlsx')

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
        thread_name_prefix='run_with_async_db_thread',
        initializer=_inherit_main_thread_connections
    )

    def setUp(self):
        clear_db()
        clear_minio()

    # Don't bother clearing data in tearDown(). The next test that needs the
    # database will be running setUp() anyway, so extra clearing will only cost
    # time.

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
        old_executor = WorkbenchDatabaseSyncToAsync.executor
        asyncio.set_event_loop(None)
        try:
            WorkbenchDatabaseSyncToAsync.executor = self.async_executor
            return asyncio.run(task)
        finally:
            WorkbenchDatabaseSyncToAsync.executor = old_executor
            asyncio.set_event_loop(old_loop)


# Derive from this to perform all tests logged in
class LoggedInTestCase(DbTestCase):
    def setUp(self):
        super().setUp()

        self.user = create_test_user()
        self.client.force_login(self.user)


def create_test_user(username='username', email='user@example.org',
                     password='password'):
    return User.objects.create(username=username, email=email,
                               password=password)


_Tables = [
    'server_aclentry',
    'server_addmodulecommand',
    'server_addtabcommand',
    'server_changedataversioncommand',
    'server_changeparameterscommand',
    'server_changewfmodulenotescommand',
    'server_changeworkflowtitlecommand',
    'server_deletemodulecommand',
    'server_deletetabcommand',
    'server_duplicatetabcommand',
    'server_reordermodulescommand',
    'server_reordertabscommand',
    'server_settabnamecommand',
    'server_initworkflowcommand',
    'server_delta',
    'server_moduleversion',
    'server_storedobject',
    'server_uploadedfile',
    'server_wfmodule',
    'server_tab',
    'server_workflow',
    'django_session',
    'auth_group',
    'auth_group_permissions',
    'auth_permission',
    'cjworkbench_userprofile',
    'auth_user',
    'auth_user_groups',
    'auth_user_user_permissions',
]


def clear_db():
    deletes = [f't{i} AS (DELETE FROM {table})'
               for i, table in enumerate(_Tables)]
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

    if not hasattr(clear_minio, '_initialized'):
        # Ensure buckets exist -- only on first call
        for bucket in buckets:
            minio.ensure_bucket_exists(bucket)
        clear_minio._initialized = True

    for bucket in buckets:
        minio.remove_recursive(bucket, '/', force=True)


class MockPath(pathlib.PurePosixPath):
    """
    Simulate pathlib.Path

    Features:

        * read_bytes()
        * read_text(), including encoding and errors
        * open()
        * when `data` is None, raise `FileNotFoundError` when expecting a file
    """

    def __new__(cls, parts: List[str], data: Optional[bytes],
                parent: Optional[pathlib.PurePosixPath] = None):
        ret = super().__new__(cls, *parts)
        ret.data = data
        ret._parent = parent
        return ret

    # override
    @property
    def parent(self):
        return self._parent

    # Path interface
    def read_bytes(self):
        if self.data is None:
            raise FileNotFoundError(self.name)

        return self.data

    # Path interface
    def read_text(self, encoding='utf-8', errors='strict'):
        if self.data is None:
            raise FileNotFoundError(self.name)

        return self.data.decode(encoding, errors)

    def open(self, mode):
        assert mode == 'rb'
        return io.BytesIO(self.data)


class MockDir(pathlib.PurePosixPath):
    """
    Mock filesystem directory using pathlib.Path interface.

    Usage:

        dirpath: PurePath = MockDir({
            'xxx.yaml': b'id_name: xxx...'
            'xxx.py': b'def render(
        })

        yaml_text = (dirpath / 'xxx.yaml').read_text()
    """

    def __new__(cls, filedata: Dict[str, bytes]):  # filename => bytes
        ret = super().__new__(cls, pathlib.PurePath('root'))
        ret.filedata = filedata
        return ret

    # override
    def __truediv__(self, filename: str) -> MockPath:
        data = self.filedata.get(filename)  # None if file does not exist
        return MockPath(['root', filename], data, parent=self)
        try:
            return self.files[filename]
        except KeyError:
            return MockPath(['root', filename], None)

    def glob(self, pattern: str) -> Iterable[MockPath]:
        for key in self.filedata.keys():
            path = self / key
            if path.match(pattern):
                yield path
