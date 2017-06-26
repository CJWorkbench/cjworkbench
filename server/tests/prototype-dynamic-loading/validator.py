from importlib import import_module
import os
import sys

class Validator:
  def event(self):
    print("event")

  def render(self):
    print("render")

  def __init__(self, name):
    self.name = name
