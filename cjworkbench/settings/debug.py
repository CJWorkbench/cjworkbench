import os
import sys

from .util import FalsyStrings

__all__ = ("DEBUG", "I_AM_TESTING", "TEST_RUNNER")

if "CJW_PRODUCTION" in os.environ:
    DEBUG = os.environ["CJW_PRODUCTION"] not in FalsyStrings
else:
    DEBUG = True

I_AM_TESTING = "test" in sys.argv
TEST_RUNNER = "server.tests.runner.TimeLoggingDiscoverRunner"  # only for unittests
