from django.test.runner import DiscoverRunner
import unittest
from unittest.runner import TextTestResult
import time

# Inspired by https://hackernoon.com/timing-tests-in-python-for-fun-and-profit-1663144571


class TimeLoggingTestRunner(unittest.TextTestRunner):
    def __init__(self, slow_test_threshold=0.3, *args, **kwargs):
        self.slow_test_threshold = slow_test_threshold
        return super().__init__(*args, **kwargs)

    def run(self, test):
        result = super().run(test)
        wrote = False
        for name, elapsed in result.getTestTimings():
            if elapsed > self.slow_test_threshold:
                if not wrote:
                    self.stream.writeln(
                        "\nSlow Tests (>{:.03}s):".format(self.slow_test_threshold)
                    )
                    wrote = True
                self.stream.writeln("({:.03}s) {}".format(elapsed, name))
        return result


class TimeLoggingTestResult(TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_timings = []

    def startTest(self, test):
        self._test_started_at = time.time()
        super().startTest(test)

    def addSuccess(self, test):
        elapsed = time.time() - self._test_started_at
        name = self.getDescription(test)
        self.test_timings.append((name, elapsed))
        super().addSuccess(test)

    def getTestTimings(self):
        return self.test_timings


class TimeLoggingDiscoverRunner(DiscoverRunner):
    test_runner = TimeLoggingTestRunner

    def __init__(self, *args, **kwargs):
        DiscoverRunner.__init__(self, *args, **kwargs)

    def get_resultclass(self):
        return TimeLoggingTestResult
