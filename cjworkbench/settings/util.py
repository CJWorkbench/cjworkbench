from os.path import abspath, dirname

__all__ = ("FalsyStrings", "DJANGO_ROOT")

FalsyStrings = frozenset({"", "false", "False", "0", "off"})

DJANGO_ROOT = abspath(dirname(dirname(dirname(__file__))))
