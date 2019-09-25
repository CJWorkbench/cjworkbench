from django.test import SimpleTestCase
from cjworkbench.i18n.trans import trans, MessageTranslator, InvalidICUParameters
from cjworkbench.i18n import default_locale


mock_message_id = (
    "some+crazy+id+that+will+never+be+actually+used+in+real+translation+files"
)


class TransTest(SimpleTestCase):
    def test_format_invalid_default(self):
        """Tests that a programmer will get an exception when including a numeric variable in the message
        """
        with self.assertRaises(InvalidICUParameters):
            trans(
                default_locale,
                mock_message_id,
                default="Hello {a} {0} {b}",
                parameters={"a": "you", "0": "!", "b": "2"},
            ),

    def test_format_invalid_message(self):
        """Tests that a translator can't break our system by including a numeric variable in the message
        """
        self.assertEqual(
            MessageTranslator(default_locale).process_message(
                "Hello {a} {0} {b}", "Hello {a} {b}", parameters={"a": "you", "b": "!"}
            ),
            "Hello you !",
        )
