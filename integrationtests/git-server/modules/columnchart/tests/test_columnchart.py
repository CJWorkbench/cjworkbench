#!/usr/bin/env python3

import unittest
from columnchart import Config, YColumn


class ConfigTest(unittest.TestCase):
    def test_missing_x_column(self):
        config = Config.from_params({
        })


class NiceRangeTest(unittest.TestCase):
    def test_big_numbers(self):
        self.assertEqual(nice_range(240, 12314, 13), (0, 13000, 13))

    def test_across_zero(self):
        self.assertEqual(nice_range(-8, 22, 4), (-10, 30, 4))

    def test_small_numbers(self):
        self.assertEqual(nice_range(0.1, 0.41, 16), (0.1, 0.42, 16))

    def test_small_numbers_across_zero(self):
        self.assertEqual(nice_range(-0.04, 0.8, 9), (-0.1, 0.8, 9))

    def test_sugests_better_n_ticks(self):
        self.assertEqual(nice_range(-0.04, 0.8, 10), (-0.1, 0.8, 9))

