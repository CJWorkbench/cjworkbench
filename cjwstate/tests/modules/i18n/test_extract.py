import unittest
from cjwstate.modules.i18n.extractor import _find_messages_in_module_code
from io import BytesIO


class FindMessagesInModuleCodeTest(unittest.TestCase):
    def test_no_translations(self):
        code = BytesIO(
            b"""
def render(table):
    return table
        """
        )
        result = _find_messages_in_module_code(code, "module.py")
        expected = {}
        self.assertEqual(result, expected)

    def test_translation_simple(self):
        code = BytesIO(
            b"""
from cjwmodule import i18n

def render(table):
    return (table, i18n.trans('message.id', 'Default message'))
        """
        )
        result = _find_messages_in_module_code(code, "module.py")
        expected = {
            "message.id": {
                "string": "Default message",
                "locations": [("module.py", 5)],
                "comments": [],
            }
        }
        self.assertEqual(result, expected)

    def test_translation_line_wrap(self):
        code = BytesIO(
            b"""
from cjwmodule import i18n

def render(table):
    return (table, 
        i18n.trans(
            'message.id', 
            'Default message'
        )
    )
        """
        )
        result = _find_messages_in_module_code(code, "module.py")
        expected = {
            "message.id": {
                "string": "Default message",
                "locations": [("module.py", 6)],
                "comments": [],
            }
        }
        self.assertEqual(result, expected)

    def test_translation_with_comment(self):
        code = BytesIO(
            b"""
from cjwmodule import i18n

def render(table):
    return (table, 
        # i18n: Some helpful comment
        i18n.trans('message.id', 'Default message')
    )
        """
        )
        result = _find_messages_in_module_code(code, "module.py")
        expected = {
            "message.id": {
                "string": "Default message",
                "locations": [("module.py", 7)],
                "comments": ["i18n: Some helpful comment"],
            }
        }
        self.assertEqual(result, expected)

    def test_translation_with_arguments(self):
        code = BytesIO(
            b"""
from cjwmodule import i18n
from mygreatmodule import help

def render(table):
    return (table, 
        i18n.trans('message.id', 'Default message with {parameter}', {'parameter': help()})
    )
        """
        )
        result = _find_messages_in_module_code(code, "module.py")
        expected = {
            "message.id": {
                "string": "Default message with {parameter}",
                "locations": [("module.py", 7)],
                "comments": [],
            }
        }
        self.assertEqual(result, expected)

    def test_translation_multiple_appearances(self):
        code = BytesIO(
            b"""
from cjwmodule import i18n
from mygreatmodule import this

def render(table):
    if this():
        return (table, 
            i18n.trans('message.id', 'Default message with {parameter}', {'parameter': this()})
        )
    else:
        return (table, 
            i18n.trans('message.id', 'Default message with {parameter}', {'parameter': 'other'})
        )
        """
        )
        result = _find_messages_in_module_code(code, "module.py")
        expected = {
            "message.id": {
                "string": "Default message with {parameter}",
                "locations": [("module.py", 8), ("module.py", 12)],
                "comments": [],
            }
        }
        self.assertEqual(result, expected)

    def test_multiple_translations(self):
        code = BytesIO(
            b"""
from cjwmodule import i18n
from mygreatmodule import this

def render(table):
    if this():
        return (table, 
            # i18n: Some helpful comment
            i18n.trans('message.id', 'Default message')
        )
    else:
        return (table, 
            i18n.trans(
                'other_message.id', 
                'Other default message', 
                {'param1': 'a', 'param2': 3}
            )
        )
        """
        )
        result = _find_messages_in_module_code(code, "module.py")
        expected = {
            "message.id": {
                "string": "Default message",
                "locations": [("module.py", 9)],
                "comments": ["i18n: Some helpful comment"],
            },
            "other_message.id": {
                "string": "Other default message",
                "locations": [("module.py", 13)],
                "comments": [],
            },
        }
        self.assertEqual(result, expected)

    def test_translation_with_nonstring_id(self):
        code = BytesIO(
            b"""
from cjwmodule.i18n import trans

def render(table):
    id = 'message.id'
    return (table, 
        trans(id, 'Default message')
    )
        """
        )
        result = _find_messages_in_module_code(code, "module.py")
        expected = {}
        self.assertEqual(result, expected)

    def test_translation_with_nonstring_default(self):
        code = BytesIO(
            b"""
from cjwmodule.i18n import trans

def render(table):
    default_message = 'Default message'
    return (table, 
        trans('message.id', default_message)
    )
        """
        )
        with self.assertRaises(SyntaxError):
            result = _find_messages_in_module_code(code, "module.py")

    def test_translation_with_nonstring_id_and_default(self):
        code = BytesIO(
            b"""
from cjwmodule.i18n import trans

def render(table):
    id = 'message.id'
    default_message = 'Default message'
    return (table, 
        trans(id, default_message)
    )
        """
        )
        result = _find_messages_in_module_code(code, "module.py")
        expected = {}
        self.assertEqual(result, expected)

    def test_simple_translation_without_i18n_literal(self):
        code = BytesIO(
            b"""
from cjwmodule.i18n import trans

def render(table):
    return (table, 
        # i18n: Some helpful comment
        trans('message.id', 'Default message')
    )
        """
        )
        result = _find_messages_in_module_code(code, "module.py")
        expected = {
            "message.id": {
                "string": "Default message",
                "locations": [("module.py", 7)],
                "comments": ["i18n: Some helpful comment"],
            }
        }
        self.assertEqual(result, expected)
