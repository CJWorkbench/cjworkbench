import os
import sys

from .util import FalsyStrings

__all__ = ("DEBUG", "I_AM_TESTING", "TEST_RUNNER")

DEBUG = os.environ.get("CJW_PRODUCTION", "False") in FalsyStrings
I_AM_TESTING = "test" in sys.argv
TEST_RUNNER = "server.tests.runner.TimeLoggingDiscoverRunner"  # only for unittests
