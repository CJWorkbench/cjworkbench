from asgiref.sync import async_to_sync
from server.tests.utils import DbTestCase
from worker.pg_locker import PgLocker, WorkflowAlreadyLocked


class PgLockerTest(DbTestCase):
    def test_pg_locker(self):
        async def inner():
            async with PgLocker() as locker1:
                async with PgLocker() as locker2:
                    async with locker1.render_lock(1):
                        with self.assertRaises(WorkflowAlreadyLocked):
                            async with locker2.render_lock(1):
                                pass

                    # do not raise WorkflowAlreadyLocked here
                    async with locker2.render_lock(1):
                        pass

        async_to_sync(inner)()
