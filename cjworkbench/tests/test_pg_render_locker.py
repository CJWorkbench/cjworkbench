import asyncio
import unittest
from cjworkbench.pg_render_locker import PgRenderLocker, WorkflowAlreadyLocked


def _run_async(task):
    asyncio.get_event_loop().run_until_complete(task)


class PgRenderLockerTest(unittest.TestCase):
    def test_hold_lock(self):
        async def inner():
            async with PgRenderLocker() as locker1:
                async with PgRenderLocker() as locker2:
                    async with locker1.render_lock(1) as lock1:
                        with self.assertRaises(WorkflowAlreadyLocked):
                            async with locker2.render_lock(1) as lock2:
                                await lock2.stall_others()
                        await lock1.stall_others()

        _run_async(inner())

    def test_release_lock(self):
        async def inner():
            async with PgRenderLocker() as locker1:
                async with PgRenderLocker() as locker2:
                    async with locker1.render_lock(1) as lock1:
                        await lock1.stall_others()

                    # do not raise WorkflowAlreadyLocked here
                    async with locker2.render_lock(1) as lock1:
                        await lock1.stall_others()

        _run_async(inner())

    def test_lock_only_one_workflow(self):
        async def inner():
            async with PgRenderLocker() as locker1:
                async with PgRenderLocker() as locker2:
                    async with locker1.render_lock(1) as lock1:
                        # do not raise WorkflowAlreadyLocked here: it's a
                        # different workflow
                        async with locker2.render_lock(2) as lock2:
                            await lock2.stall_others()
                        await lock1.stall_others()

        _run_async(inner())

    def test_locker_can_be_reused_in_same_event_loop(self):
        async def inner():
            async with PgRenderLocker() as locker:
                async with locker.render_lock(1) as lock1:
                    async with locker.render_lock(2) as lock2:
                        await lock2.stall_others()

                    async with locker.render_lock(2) as lock2:
                        await lock2.stall_others()
                    await lock1.stall_others()

        _run_async(inner())

    def test_locker_can_try_to_lock_its_own_lock(self):
        async def inner():
            async with PgRenderLocker() as locker:
                async with locker.render_lock(1) as lock1:
                    with self.assertRaises(WorkflowAlreadyLocked):
                        async with locker.render_lock(1) as lock2:
                            await lock2.stall_others()
                    await lock1.stall_others()

        _run_async(inner())

    def test_concurrent_locks_on_one_connection(self):
        """
        Avoid InterfaceError: "another operation is in progress"
        """
        async def use_lock(locker, workflow_id):
            async with locker.render_lock(workflow_id) as lock1:
                await lock1.stall_others()

        async def inner():
            async with PgRenderLocker() as locker:
                done, _ = await asyncio.wait(
                    {use_lock(locker, i) for i in range(5)}
                )
                for task in done:
                    task.result()  # throw error, if any

        _run_async(inner())

    def test_acquire_render_lock_after_refused(self):
        async def inner():
            async with PgRenderLocker() as locker1:
                async with PgRenderLocker() as locker2:
                    async with locker1.render_lock(1) as lock1:
                        # "break" locker2: make it raise an exception
                        with self.assertRaises(WorkflowAlreadyLocked):
                            async with locker2.render_lock(1) as lock2:
                                await lock2.stall_others()
                        await lock1.stall_others()
                    # now locker2 should be reset to its original state --
                    # meaning it can acquire a lock just fine
                    async with locker2.render_lock(1) as lock2:
                        await lock2.stall_others()
        _run_async(inner())

    def test_stall_others_prevents_raise_remotely(self):
        async def inner():
            async with PgRenderLocker() as locker1:
                async with PgRenderLocker() as locker2:
                    last_line = 'the initial value'
                    async with locker1.render_lock(1) as lock1:
                        await lock1.stall_others()
                        async def stalling_op():
                            nonlocal last_line
                            async with locker2.render_lock(1) as lock2:
                                last_line = 'entered stalling_op'
                                await lock2.stall_others()
                            last_line = 'exited stalling_op'
                        task = asyncio.create_task(stalling_op())
                        await asyncio.sleep(0)
                        # Even though we started stalling_op(), it will stall
                        # rather than acquire a lock.
                        self.assertEqual(last_line, 'the initial value')
                    await task
                    self.assertEqual(last_line, 'exited stalling_op')
        _run_async(inner())

    def test_stall_others_prevents_raise_locally(self):
        async def inner():
            async with PgRenderLocker() as locker:
                last_line = 'the initial value'
                async with locker.render_lock(1) as lock1:
                    await lock1.stall_others()
                    async def stalling_op():
                        nonlocal last_line
                        async with locker.render_lock(1) as lock2:
                            last_line = 'entered stalling_op'
                            await lock2.stall_others()
                        last_line = 'exited stalling_op'
                    task = asyncio.create_task(stalling_op())
                    await asyncio.sleep(0)
                    # Even though we started stalling_op(), it will stall
                    # rather than acquire a lock.
                    self.assertEqual(last_line, 'the initial value')
                await task
                self.assertEqual(last_line, 'exited stalling_op')
        _run_async(inner())
