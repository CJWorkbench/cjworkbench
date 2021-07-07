import asyncio

from django.db import connection
from django.http import HttpResponse

import cjwstate.rabbitmq.connection
from cjworkbench.sync import database_sync_to_async
from cjwstate import s3


@database_sync_to_async
def _assert_database_ok():
    """Crash if DB is not available."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")


async def _assert_s3_ok():
    """Crash if S3 is not available."""
    # The file doesn't need to be there; the request need only complete
    s3.exists(s3.UserFilesBucket, "healthz")


async def _assert_carehare_ok():
    """Crash if carehare is not connected."""
    await cjwstate.rabbitmq.connection.get_global_connection()


_assertions = [
    _assert_database_ok,
    _assert_s3_ok,
    _assert_carehare_ok,
]


async def healthz(request):
    """Return 200 OK if database and s3 connections are ok."""
    assertions = [asyncio.create_task(f()) for f in _assertions]
    try:
        await asyncio.gather(*assertions)
    finally:
        # Clean up
        await asyncio.gather(*assertions, return_exceptions=True)

    return HttpResponse(b"OK", content_type="text/plain; charset=utf-8")
