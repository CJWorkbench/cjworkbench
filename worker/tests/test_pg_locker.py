import asyncio
import unittest
from worker.pg_locker import PgLocker, WorkflowAlreadyLocked


class PgLockerTest(unittest.TestCase):
    def test_hold_lock(self):
        async def inner():
            async with PgLocker() as locker1:
                async with PgLocker() as locker2:
                    async with locker1.render_lock(1):
                        with self.assertRaises(WorkflowAlreadyLocked):
                            async with locker2.render_lock(1):
                                pass

        asyncio.run(inner())

    def test_release_lock(self):
        async def inner():
            async with PgLocker() as locker1:
                async with PgLocker() as locker2:
                    async with locker1.render_lock(1):
                        pass

                    # do not raise WorkflowAlreadyLocked here
                    async with locker2.render_lock(1):
                        pass

        asyncio.run(inner())

    def test_lock_only_one_workflow(self):
        async def inner():
            async with PgLocker() as locker1:
                async with PgLocker() as locker2:
                    async with locker1.render_lock(1):
                        # do not raise WorkflowAlreadyLocked here: it's a
                        # different workflow
                        async with locker2.render_lock(2):
                            pass


        asyncio.run(inner())

    def test_locker_can_be_reused_in_same_event_loop(self):
        async def inner():
            async with PgLocker() as locker:
                async with locker.render_lock(1):
                    async with locker.render_lock(2):
                        pass

                    async with locker.render_lock(2):
                        pass

        asyncio.run(inner())

    def test_locker_can_try_to_lock_its_own_lock(self):
        async def inner():
            async with PgLocker() as locker:
                async with locker.render_lock(1):
                    with self.assertRaises(WorkflowAlreadyLocked):
                        async with locker.render_lock(1):
                            pass

        asyncio.run(inner())

    def test_concurrent_locks_on_one_connection(self):
        """
        Avoid InterfaceError: "another operation is in progress"
        """
        async def use_lock(locker, workflow_id):
            async with locker.render_lock(workflow_id):
                pass

        async def inner():
            async with PgLocker() as locker:
                done, _ = await asyncio.wait(
                    {use_lock(locker, i) for i in range(3)}
                )
                for task in done:
                    task.result()  # throw error, if any

        asyncio.run(inner())
