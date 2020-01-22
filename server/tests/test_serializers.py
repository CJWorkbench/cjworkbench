import unittest
from cjwkernel.types import I18nMessage, QuickFix, QuickFixAction, RenderError
from server.serializers import jsonize_i18n_message, JsonizeContext
from cjworkbench.i18n.trans import MessageTranslator
from unittest.mock import patch
from babel.messages.catalog import Catalog


def mock_jsonize_context(user=None, session=None, locale_id=None):
    return JsonizeContext(user=user, session=session, locale_id=locale_id)


class JsonizeI18nMessageTest(unittest.TestCase):
    def test_TODO_i18n(self):
        self.assertEqual(
            jsonize_i18n_message(
                I18nMessage.TODO_i18n("hello"), mock_jsonize_context(locale_id="en")
            ),
            "hello",
        )

    def test_source_None_message_exists_in_given_locale(self):
        def mock_get_translations(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello")
            else:
                catalog.add("id", string="Hey")
            return MessageTranslator(locale, catalog)

        with patch("cjworkbench.i18n.trans._get_translations", mock_get_translations):
            self.assertEqual(
                jsonize_i18n_message(
                    I18nMessage("id"), mock_jsonize_context(locale_id="el")
                ),
                "Hey",
            )

    def test_source_None_message_exists_only_in_default_locale(self):
        def mock_get_translations(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello")
            return MessageTranslator(locale, catalog)

        with patch("cjworkbench.i18n.trans._get_translations", mock_get_translations):
            self.assertEqual(
                jsonize_i18n_message(
                    I18nMessage("id"), mock_jsonize_context(locale_id="el")
                ),
                "Hello",
            )

    def test_source_None_message_exists_in_no_locales(self):
        def mock_get_translations(locale):
            return MessageTranslator(locale, Catalog())

        with patch("cjworkbench.i18n.trans._get_translations", mock_get_translations):
            with self.assertRaises(KeyError):
                jsonize_i18n_message(
                    I18nMessage("id"), mock_jsonize_context(locale_id="el")
                )
