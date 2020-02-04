from django.db import connection
from django.http import HttpResponse
from cjwstate import minio


def healthz(request):
    """
    Return 200 OK if database and minio connections are ok.
    """
    minio.exists(minio.UserFilesBucket, "healthz")  # do not crash
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return HttpResponse(b"OK", content_type="text/plain; charset=utf-8")
