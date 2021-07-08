import os as _os

from .debug import DEBUG as _debug
from .util import DJANGO_ROOT as _django_root, FalsyStrings as _falsy_strings

DEFAULT_FROM_EMAIL = "Workbench <hello@workbenchdata.com>"

# EMAIL_BACKEND (copied in server/settings.py)
if _debug or _os.environ.get("CJW_MOCK_EMAIL", "False") not in _falsy_strings:
    EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
    EMAIL_FILE_PATH = _os.path.join(_django_root, "local_mail")
else:
    # Default EMAIL_BACKEND => SMTP
    EMAIL_HOST = _os.environ["CJW_SMTP_HOST"]
    EMAIL_HOST_USER = _os.environ["CJW_SMTP_USER"]
    EMAIL_HOST_PASSWORD = _os.environ["CJW_SMTP_PASSWORD"]
    EMAIL_PORT = int(_os.environ["CJW_SMTP_PORT"])
    EMAIL_USE_TLS = _os.environ["CJW_SMTP_USE_TLS"] not in _falsy_strings
