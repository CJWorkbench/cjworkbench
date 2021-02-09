import asyncio
from concurrent.futures import ThreadPoolExecutor

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.test import SimpleTestCase

from cjworkbench.sync import WorkbenchDatabaseSyncToAsync


User = get_user_model

# Connect to the database, on the main thread, and remember that connection
main_thread_connections = {name: connections[name] for name in connections}


def _inherit_main_thread_connections():
    for name in main_thread_connections:
        connections[name] = main_thread_connections[name]
        connections[name].inc_thread_sharing()


class DbTestCase(SimpleTestCase):
    allow_database_queries = True
    databases = "__all__"

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


_Tables = [
    "acl_entry",
    "block",
    "delta",
    "module_version",
    "stored_object",
    "uploaded_file",
    "step",
    "tab",
    "workflow",
    "django_session",
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
    "cjworkbench_userprofile",
    "subscription",
    "price",
    "product",
    "auth_user",
    "auth_user_groups",
    "auth_user_user_permissions",
]


def clear_db():
    deletes = [f"t{i} AS (DELETE FROM {table})" for i, table in enumerate(_Tables)]
    sql = f"WITH {', '.join(deletes)} SELECT 1"
    with connection.cursor() as c:
        c.execute(sql)
