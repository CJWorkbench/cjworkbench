"""
sqlite3 backend that uses BEGIN IMMEDIATE instead of BEGIN.

This helps because one of our main uses of BEGIN is in
workflow.cooperative_lock(). It runs SELECT FOR UPDATE to lock the workflow.
But sqlite3 ignores FOR UPDATE. We can alter sqlite3 so it does a
BEGIN IMMEDIATE instead of BEGIN: that will effectively turn the BEGIN
itself into a lock, which helps in workflow.cooperative_lock().

sqlite3: is it worth it?
"""

from django.db.backends.sqlite3.base import (
    DatabaseWrapper as Sqlite3Wrapper,
    DatabaseFeatures,
    DatabaseOperations,
)

__all__ = ['DatabaseWrapper', 'DatabaseFeatures', 'DatabaseOperations']

class DatabaseWrapper(Sqlite3Wrapper):
    def _start_transaction_under_autocommit(self):
        """
        Start a transaction explicitly in autocommit mode.
        Staying in autocommit mode works around a bug of sqlite3 that breaks
        savepoints when autocommit is disabled.
        """
        self.cursor().execute('BEGIN IMMEDIATE')
