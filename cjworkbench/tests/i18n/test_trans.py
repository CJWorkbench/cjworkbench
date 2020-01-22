import logging
from babel.messages.catalog import Catalog
from django.test import SimpleTestCase
from icu import ICUError, InvalidArgsError
from cjworkbench.i18n.trans import MessageTranslator, localize, localize_html
from unittest.mock import patch


class MessageTranslatorFormatTest(SimpleTestCase):
    # Tests that nonexisting message raises a `KeyError`.
    def test_missing_message(self):
        catalog = Catalog()
        with self.assertRaises(KeyError):
            MessageTranslator("en", catalog).get_and_format_message("id")

    # Tests that `parameters` argument replaces variables in the message.
    # 1) Parameters that do not exist in the message are ignored.
    # 2) Variables in the message for which no parameter has been given are ignored.
    def test_trans_params(self):
        catalog = Catalog()
        catalog.add("id", string="Hey {a} {param_b} {c}!")
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_message(
                "id", parameters={"param_b": "there", "a": "you", "d": "tester"}
            ),
            "Hey you there {c}!",
        )

    # Tests that passing a list as parameters will raise an exception
    def test_parameters_list(self):
        catalog = Catalog()
        catalog.add("id", string="Hey {0} {1}!")
        with self.assertRaises(AttributeError):
            MessageTranslator("en", catalog).get_and_format_message(
                "id", parameters=["you", "there"]
            )

    # Tests that passing a tuple as parameters will raise an exception
    def test_parameters_tuple(self):
        catalog = Catalog()
        catalog.add("id", string="Hey {0} {1}!")
        with self.assertRaises(AttributeError):
            MessageTranslator("en", catalog).get_and_format_message(
                "id", parameters=("you", "there")
            )

    # Tests that passing a list as a value for a parameter will raise an exception
    def test_parameter_list(self):
        catalog = Catalog()
        catalog.add("id", string="Hey {0} {1}!")
        with self.assertRaises(InvalidArgsError):
            MessageTranslator("en", catalog).get_and_format_message(
                "id", parameters={"0": ["you ", "there"]}
            )

    # Tests that badly formatted parameter in a catalog raises `ICUError`
    def test_message_invalid_parameter_syntax(self):
        catalog = Catalog()
        catalog.add("id", string="Hey {a b}!")
        with self.assertRaises(ICUError):
            result = MessageTranslator("en", catalog).get_and_format_message(
                "id", parameters={"a": "you", "b": "!"}
            )

    # Tests that a message in catalogs can use a numeric variable
    def test_message_numeric_parameter(self):
        catalog = Catalog()
        catalog.add("id", string="Hey {a} {0} {b}")
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_message(
                "id", parameters={"a": "you", "b": "!", "0": "there"}
            ),
            "Hey you there !",
        )

    # Tests that a message in the catalogs can't break our system by having more or missing variables relative to the default
    def test_message_different_parameters(self):
        catalog = Catalog()
        catalog.add("id", string="Hey {a} {0} {c}")
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_message(
                "id", parameters={"a": "you", "b": "!"}
            ),
            "Hey you {0} {c}",
        )

    # Tests that HTML is not escaped
    def test_no_html_escape(self):
        catalog = Catalog()
        catalog.add(
            "id", string='Hello <a href="/you?a=n&b=e">you > {param_b}</a> my & friend'
        )
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_message(
                "id", parameters={"param_b": "> there"}
            ),
            'Hello <a href="/you?a=n&b=e">you > > there</a> my & friend',
        )

    # Tests that plurals, selects and nested messages are fully supported
    def test_icu_support(self):
        catalog = Catalog()
        catalog.add(
            "id",
            string=(
                "Hello {a}, you have {g, select,"
                "   male {{n, plural,"
                "       =0 {no boys} one {# boy} other {# boys}"
                "   }}"
                "   female {{n, plural,"
                "       =0 {no girls} one {# girl} other {# girls}"
                "   }}"
                "   other {{n, plural,"
                "       =0 {no children} one {# child} other {# children}"
                "   }}"
                "}"
            ),
        )
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_message(
                "id", parameters={"a": "there", "g": "male", "n": 17}
            ),
            "Hello there, you have 17 boys",
        )
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_message(
                "id", parameters={"a": "there", "g": "female", "n": 18}
            ),
            "Hello there, you have 18 girls",
        )
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_message(
                "id", parameters={"a": "there", "g": "other", "n": 0}
            ),
            "Hello there, you have no children",
        )


class MessageTranslatorFormatHtmlTest(SimpleTestCase):
    # Tests that nonexisting message raises a `KeyError`.
    def test_missing_message(self):
        catalog = Catalog()
        with self.assertRaises(KeyError):
            MessageTranslator("en", catalog).get_and_format_html_message("id")

    # Tests that `parameters` argument replaces variables in the message.
    # 1) Parameters that do not exist in the message are ignored.
    # 2) Variables in the message for which no parameter has been given are ignored.
    def test_trans_params(self):
        catalog = Catalog()
        catalog.add("id", string="Hey {a} {param_b} {c}!")
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id", parameters={"param_b": "there", "a": "you", "d": "tester"}
            ),
            "Hey you there {c}!",
        )

    # Tests that passing a list as parameters will raise an exception
    def test_parameters_list(self):
        catalog = Catalog()
        catalog.add("id", string="Hey {0} {1}!")
        with self.assertRaises(AttributeError):
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id", parameters=["you", "there"]
            )

    # Tests that passing a tuple as parameters will raise an exception
    def test_parameters_tuple(self):
        catalog = Catalog()
        catalog.add("id", string="Hey {0} {1}!")
        with self.assertRaises(AttributeError):
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id", parameters=("you", "there")
            )

    # Tests that passing a list as a value for a parameter will raise an exception
    def test_parameter_list(self):
        catalog = Catalog()
        catalog.add("id", string="Hey {0} {1}!")
        with self.assertRaises(InvalidArgsError):
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id", parameters={"0": ["you ", "there"]}
            )

    # Tests that badly formatted parameter in a catalog raises `ICUError`
    def test_message_invalid_parameter_syntax(self):
        catalog = Catalog()
        catalog.add("id", string="Hey {a b}!")
        with self.assertRaises(ICUError):
            result = MessageTranslator("en", catalog).get_and_format_html_message(
                "id", parameters={"a": "you", "b": "!"}
            )

    # Tests that a message in catalogs can use a numeric variable
    def test_message_numeric_parameter(self):
        catalog = Catalog()
        catalog.add("id", string="Hey {a} {0} {b}")
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id", parameters={"a": "you", "b": "!", "0": "there"}
            ),
            "Hey you there !",
        )

    # Tests that a message in the catalogs can't break our system by having more or missing variables relative to the default
    def test_message_different_parameters(self):
        catalog = Catalog()
        catalog.add("id", string="Hey {a} {0} {c}")
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id", parameters={"a": "you", "b": "!"}
            ),
            "Hey you {0} {c}",
        )

    # Tests that tags in messages are replaced correctly.
    # 1) Tags in `tags` that are not in the message are ignored.
    # 2) Tags in the message but not in `tags` are ignored. At this point, their contents are kept, but this may change in the future.
    # 3) All attributes given for a tag in `tags` are used.
    # 4) Tag attributes existing in the message are ignored.
    def test_tags(self):
        catalog = Catalog()
        catalog.add("id", string='<a0 id="nope">Hello</a0><b0>you</b0><div>there</div>')
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id",
                parameters={"a": "you"},
                tags={
                    "a0": {
                        "tag": "a",
                        "attrs": {
                            "href": "/you",
                            "class": "the test",
                            "data-target": "someid",
                        },
                    },
                    "span0": {"tag": "span", "attrs": {"id": "ignore"}},
                },
            ),
            '<a class="the test" data-target="someid" href="/you">Hello</a>youthere',
        )

    # Tests that nested tags in messages are not tolerated.
    # At this point, nested tags are ignored, but their contents are kept. This may change in the future.
    def test_nested_tags(self):
        catalog = Catalog()
        catalog.add("id", string="<a0>Hello<b0>you</b0><div>there</div></a0>")
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id",
                parameters={"a": "you"},
                tags={
                    "a0": {"tag": "a", "attrs": {"href": "/you"}},
                    "b0": {"tag": "b", "attrs": {"id": "hi"}},
                },
            ),
            '<a href="/you">Helloyouthere</a>',
        )

    # Tests that parameters are substituted within tags
    def test_params_in_tags(self):
        catalog = Catalog()
        catalog.add("id", string="<a0>Hello {name}</a0>{test}")
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id",
                parameters={"name": "you", "test": "!"},
                tags={"a0": {"tag": "a", "attrs": {"href": "/you"}}},
            ),
            '<a href="/you">Hello you</a>!',
        )

    # Tests that special characters in the text are escaped, in any depth
    def test_escapes_text(self):
        catalog = Catalog()
        catalog.add("id", string="<a0>Hello &<b>&</b></a0>>")
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id", tags={"a0": {"tag": "a", "attrs": {"href": "/you"}}}
            ),
            '<a href="/you">Hello &amp;&amp;</a>&gt;',
        )

    # Tests that message parameters are escaped
    def test_escapes_params(self):
        catalog = Catalog()
        catalog.add("id", string="<a0>Hey {name}</a0>{test}")
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id",
                parameters={"name": "<b>you</b>", "test": "<b>there</b>"},
                tags={"a0": {"tag": "a", "attrs": {"href": "/you"}}},
            ),
            '<a href="/you">Hey &lt;b&gt;you&lt;/b&gt;</a>&lt;b&gt;there&lt;/b&gt;',
        )

    # Tests that tag attributes in messages are escaped
    def test_escapes_tag_attrs(self):
        catalog = Catalog()
        catalog.add("id", string="<a0>Hey</a0>")
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id", tags={"a0": {"tag": "a", "attrs": {"href": "/you?a=b&c=d"}}}
            ),
            '<a href="/you?a=b&amp;c=d">Hey</a>',
        )

    # Tests the combination of properties of placeholder tags and of message parameters.
    # 0) In settings where there are multiple tags, some of which have to be deleted, all of them are processed
    # 1) the `tags` argument is used to replace placeholders and they are escaped correctly
    # 2) Tags or tag placeholders that have no counterpart in the arguments are removed
    # 3) Special characters, except for the ones of valid tags, are escaped
    # 4) Nested tags are not tolerated
    # 5) `arg_XX` arguments are replaced and escaped correctly
    # 6) The same tag can appear multiple times
    def test_tag_placeholders(self):
        catalog = Catalog()
        catalog.add(
            "id",
            string='<span0 class="nope">Hey {first}</span0><span1></span1> <span0>{second}</span0> <a0>{a}<b></b></a0> < <a1>there<</a1>!<br /><script type="text/javascript" src="mybadscript.js"></script>',
        )
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id",
                parameters={"a": "you", "first": "hello", "second": "&"},
                tags={
                    "a0": {"tag": "a", "attrs": {"href": "/you"}},
                    "a1": {
                        "tag": "a",
                        "attrs": {"href": "/there?a=b&c=d", "class": "red big"},
                    },
                    "span0": {"tag": "span", "attrs": {"id": "hi"}},
                },
            ),
            '<span id="hi">Hey hello</span> <span id="hi">&amp;</span> <a href="/you">you</a> &lt; <a class="red big" href="/there?a=b&amp;c=d">there&lt;</a>!',
        )

    # Tests that plurals, selects and nested messages are fully supported
    def test_icu_support(self):
        catalog = Catalog()
        catalog.add(
            "id",
            string=(
                "Hello {a}, you have {g, select,"
                "   male {{n, plural,"
                "       =0 {no boys} one {# boy} other {# boys}"
                "   }}"
                "   female {{n, plural,"
                "       =0 {no girls} one {# girl} other {# girls}"
                "   }}"
                "   other {{n, plural,"
                "       =0 {no children} one {# child} other {# children}"
                "   }}"
                "}"
            ),
        )
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id", parameters={"a": "there", "g": "male", "n": 17}
            ),
            "Hello there, you have 17 boys",
        )
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id", parameters={"a": "there", "g": "female", "n": 18}
            ),
            "Hello there, you have 18 girls",
        )
        self.assertEqual(
            MessageTranslator("en", catalog).get_and_format_html_message(
                "id", parameters={"a": "there", "g": "other", "n": 0}
            ),
            "Hello there, you have no children",
        )


class LocalizeTest(SimpleTestCase):
    def test_message_exists_in_given_locale(self):
        def mock_get_translations(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello")
            else:
                catalog.add("id", string="Hey")
            return MessageTranslator(locale, catalog)

        with patch("cjworkbench.i18n.trans._get_translations", mock_get_translations):
            self.assertEqual(localize("el", "id"), "Hey")

    def test_message_exists_only_in_default_locale(self):
        def mock_get_translations(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello")
            return MessageTranslator(locale, catalog)

        with patch("cjworkbench.i18n.trans._get_translations", mock_get_translations):
            self.assertEqual(localize("el", "id"), "Hello")

    def test_message_exists_in_no_locales(self):
        def mock_get_translations(locale):
            return MessageTranslator(locale, Catalog())

        with patch("cjworkbench.i18n.trans._get_translations", mock_get_translations):
            with self.assertRaises(KeyError):
                localize("el", "id")

    # Tests that badly formatted parameter in a catalog can't break our system
    def test_message_invalid_parameter_syntax(self):
        def mock_get_translations(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello {a} {b}")
            else:
                catalog.add("id", string="Hey {a b}!")
            return MessageTranslator(locale, catalog)

        with patch("cjworkbench.i18n.trans._get_translations", mock_get_translations):
            with self.assertLogs(level=logging.ERROR):
                result = localize("el", "id", parameters={"a": "you", "b": "!"})
            self.assertEqual(result, "Hello you !")

    # Tests that badly formatted parameter in the default catalog will break our system
    def test_message_invalid_parameter_syntax_in_default(self):
        def mock_get_translations(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello {a b}")
            return MessageTranslator(locale, catalog)

        with patch("cjworkbench.i18n.trans._get_translations", mock_get_translations):
            with self.assertRaises(ICUError):
                localize("el", "id", parameters={"a": "you", "b": "!"})

    def test_message_invalid_parameter_syntax_in_both(self):
        def mock_get_translations(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello {a b}")
            else:
                catalog.add("id", string="Hello {a b}")
            return MessageTranslator(locale, catalog)

        with patch("cjworkbench.i18n.trans._get_translations", mock_get_translations):
            with self.assertLogs(level=logging.ERROR):
                with self.assertRaises(ICUError):
                    localize("el", "id", parameters={"a": "you", "b": "!"})


class LocalizeHtmlTest(SimpleTestCase):
    def test_message_exists_in_given_locale(self):
        def mock_get_translations(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello")
            else:
                catalog.add("id", string="Hey")
            return MessageTranslator(locale, catalog)

        with patch("cjworkbench.i18n.trans._get_translations", mock_get_translations):
            self.assertEqual(localize_html("el", "id"), "Hey")

    def test_message_exists_only_in_default_locale(self):
        def mock_get_translations(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello")
            return MessageTranslator(locale, catalog)

        with patch("cjworkbench.i18n.trans._get_translations", mock_get_translations):
            self.assertEqual(localize_html("el", "id"), "Hello")

    def test_message_exists_in_no_locales(self):
        def mock_get_translations(locale):
            return MessageTranslator(locale, Catalog())

        with patch("cjworkbench.i18n.trans._get_translations", mock_get_translations):
            with self.assertRaises(KeyError):
                localize_html("el", "id")

    # Tests that badly formatted parameter in a catalog can't break our system
    def test_message_invalid_parameter_syntax(self):
        def mock_get_translations(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello {a} {b}")
            else:
                catalog.add("id", string="Hey {a b}!")
            return MessageTranslator(locale, catalog)

        with patch("cjworkbench.i18n.trans._get_translations", mock_get_translations):
            with self.assertLogs(level=logging.ERROR):
                result = localize_html("el", "id", parameters={"a": "you", "b": "!"})
            self.assertEqual(result, "Hello you !")

    # Tests that badly formatted parameter in the default catalog will break our system
    def test_message_invalid_parameter_syntax_in_default(self):
        def mock_get_translations(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello {a b}")
            return MessageTranslator(locale, catalog)

        with patch("cjworkbench.i18n.trans._get_translations", mock_get_translations):
            with self.assertRaises(ICUError):
                localize_html("el", "id", parameters={"a": "you", "b": "!"})

    def test_message_invalid_parameter_syntax_in_both(self):
        def mock_get_translations(locale):
            catalog = Catalog()
            if locale == "en":
                catalog.add("id", string="Hello {a b}")
            else:
                catalog.add("id", string="Hello {a b}")
            return MessageTranslator(locale, catalog)

        with patch("cjworkbench.i18n.trans._get_translations", mock_get_translations):
            with self.assertLogs(level=logging.ERROR):
                with self.assertRaises(ICUError):
                    localize_html("el", "id", parameters={"a": "you", "b": "!"})
