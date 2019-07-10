from importlib import import_module
import os
import sys


class Class:
    def fetch(self):
        print("fetch")

    def render(self):
        print("render")

    def __init__(self, name):
        self.name = name


class AnotherClass:
    def fetch(self):
        print("another fetch")

    def render(self):
        print("another render")
