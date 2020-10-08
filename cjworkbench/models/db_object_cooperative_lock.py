import contextlib
from typing import Callable, ContextManager

from django.db import models, transaction


class DbObjectCooperativeLock:
    def __init__(self, object_name, _object):
        self._object = object
        setattr(self, object_name, _object)
        self._after_commit_callbacks = []

    def after_commit(self, fn: Callable[[], None]):
        """Register `fn` to be called after database commit.

        Specifically, in the following example:

            def x():
                # Timing 1
                with Workflow.lookup_and_cooperative_lock(id=123) as lock:
                    # Timing 2
                    workflow = lock.workflow
                    workflow.name = "Changed"
                    workflow.save(update_fields=["name"])
                    update = workflow.to_clientside()  # uses DB
                    def notify_websockets():
                        new_json = jsonize_clientside_workflow(update, ctx)
                        async_to_sync(async_notify_websockets)(workflow.id, new_json)
                    lock.after_commit(notify_websockets)
                    return True  # Timing 3
            success = x()  # Timing 4

        * Timing 1: there is no database transaction.
        * Timing 2: a transaction is open, and `workflow` is selected for update.
                    If an exception was raised during lookup, the call to `x()`
                    will raise it and no database modifications will occur.
        * Timing 3: a value is returned. If an exception was raised in the code
                    block, the call to `x()` will raise it and the database
                    transaction will be rolled back. `lock.workflow` may be in
                    an inconsistent state.
        * Timing 4: `notify_websockets()` has been called. If an exception was
                    raised within it, the call to `x()` will raise it. The
                    database transaction will NOT be rolled back (since the
                    exception happened after commit). `lock.workflow` may be in
                    an inconsistent state.
        """
        self._after_commit_callbacks.append(fn)

    def _invoke_after_commit_callbacks(self):
        for fn in self._after_commit_callbacks:
            fn()


@contextlib.contextmanager
def lookup_and_cooperative_lock(
    objects: models.Manager, object_name: str, **kwargs
) -> ContextManager[DbObjectCooperativeLock]:
    """Yield in a database transaction with an object selected FOR UPDATE.

    Example:

        with Workflow.lookup_and_cooperative_lock(pk=123) as lock:
            workflow = lock.workflow
            # ... do stuff
            lock.after_commit(lambda: print("called after commit, before True is returned"))
            return True

    This is _cooperative_. It only works if every write uses this method.

    It is safe to call cooperative_lock() within a cooperative_lock(). The inner
    one will behave as a no-op.

    If the context-managed block raises an error, that error will be re-raised
    and no further callbacks will be called.

    If any registered callback raises an error, that error will be re-raised
    and no further callbacks will be called.

    If any registered callback accesses the database, that will (obviously) be
    _outside_ the transaction, with the object _unlocked_.

    Take care with async functions. Transactions don't cross async boundaries;
    anything you `await` while you hold the cooperative lock won't be rolled
    back with the same rules as non-awaited code. You can still use
    cooperative locking; but instead of behaving like a database transaction,
    it will behave like a simple advisory lock; and _it cannot be nested_.

    Raises ObjectType.DoesNotExist. Re-raises any error from the inner code block
    and registered callbacks.
    """
    with transaction.atomic():
        obj = objects.select_for_update().get(**kwargs)
        lock = DbObjectCooperativeLock(object_name, obj)
        retval = yield lock

    # If we reach here, COMMIT was called and we're returning whatever the
    # `yield` block returned.
    lock._invoke_after_commit_callbacks()
    return retval
