import asyncio
from concurrent.futures import ThreadPoolExecutor
import pathlib
from typing import Dict, Iterable, List, Optional
from django.db import connection, connections
from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase
from server import minio
import os
import io
import pandas as pd

# --- Test data ----

mock_csv_text = 'Month,Amount\nJan,10\nFeb,20'
mock_csv_table = pd.read_csv(io.StringIO(mock_csv_text))

mock_xlsx_path = os.path.join(settings.BASE_DIR,
                              'server/tests/test_data/test.xlsx')


class DbTestCase(SimpleTestCase):
    allow_database_queries = True

    def setUp(self):
        clear_db()
        clear_minio()

    # Don't bother clearing data in tearDown(). The next test that needs the
    # database will be running setUp() anyway, so extra clearing will only cost
    # time.

    def run_with_async_db(self, task):
        """
        Like async_to_sync() but it closes the database connection.

        This is a rather expensive call: it connects and disconnects from the
        database.

        See
        https://github.com/django/channels/issues/1091#issuecomment-436067763.
        """
        # We'll execute with a 1-worker thread pool. That's because Django
        # database methods will spin up new connections and never close them.
        # (@database_sync_to_async -- which execute uses --only closes _old_
        # connections, not valid ones.)
        #
        # This hack is just for unit tests: we need to close all connections
        # before the test ends, so we can delete the entire database when tests
        # finish. We'll schedule the "close-connection" operation on the same
        # thread as @database_sync_to_async's blocking code ran on. That way,
        # it'll close the connection @database_sync_to_async was using.
        old_loop = asyncio.get_event_loop()

        loop = asyncio.new_event_loop()
        loop.set_default_executor(ThreadPoolExecutor(1))
        asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(task)
        finally:
            def close_thread_connection():
                # Close the connection that was created by
                # @database_sync_to_async.  Assumes we're running in the same
                # thread that ran the database stuff.
                connections.close_all()

            loop.run_until_complete(
                loop.run_in_executor(None, close_thread_connection)
            )

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
        keys = [o.object_name
                for o in minio.minio_client.list_objects_v2(bucket,
                                                            recursive=True)
                if not o.is_dir]
        if keys:
            for err in minio.minio_client.remove_objects(bucket, keys):
                raise err


class MockPath(pathlib.PurePosixPath):
    """
    Simulate pathlib.Path

    Features:

        * read_bytes()
        * read_text(), including encoding and errors
        * when `data` is None, raise `FileNotFoundError` when expecting a file
    """

    def __new__(cls, parts: List[str], data: Optional[bytes]):
        ret = super().__new__(cls, *parts)
        ret.data = data
        return ret

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
        return MockPath(['root', filename], data)
        try:
            return self.files[filename]
        except KeyError:
            return MockPath(['root', filename], None)

    def glob(self, pattern: str) -> Iterable[MockPath]:
        for key in self.filedata.keys():
            path = self / key
            if path.match(pattern):
                yield path
