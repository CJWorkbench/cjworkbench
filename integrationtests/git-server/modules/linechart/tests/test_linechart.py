#!/usr/bin/env python3

import unittest
from linechart import Config, YColumn


class ConfigTest(unittest.TestCase):
    def test_missing_x_column(self):
        config = Config.from_params({
        })
