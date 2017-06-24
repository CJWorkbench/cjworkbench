from importlib import import_module
import os
import sys

class Class:
  def event(self):
    print("event")

  def render(self):
    print("render")

  def __init__(self, name):
    self.name = name

class AnotherClass:
  def event(self):
    print("another event")

  def render(self):
    print("another render")
