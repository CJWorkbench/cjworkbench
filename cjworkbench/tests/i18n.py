from django.test import SimpleTestCase
from cjworkbench.i18n.trans import trans, MessageTranslator, InvalidICUParameters
from cjworkbench.i18n import default_locale


mock_message_id = (
    "some+crazy+id+that+will+never+be+actually+used+in+real+translation+files"
)


class TransTest(SimpleTestCase):
    def test_trans_params(self):
        """Tests that `parameters` argument replaces variables in the message.
        
        1) Parameters that do not exist in the message are ignored.
        2) Variables in the message for which no parameter has been given are ignored.
        """
        self.assertEqual(
            trans(
                default_locale,
                mock_message_id,
                default="Hello {a} {param_b} {c}!",
                parameters={"param_b": "there", "a": "you", "d": "tester"},
            ),
            "Hello you there {c}!",
        )

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
            MessageTranslator(default_locale)._process_message(
                "Hello {a} {0} {b}", "Hello {a} {b}", parameters={"a": "you", "b": "!"}
            ),
            "Hello you !",
        )

    def test_trans_tags(self):
        """ Tests that tags in messages are replaced correctly.
        
        1) Tags in `tags` that are not in the message are ignored.
        2) Tags in the message but not in `tags` are ignored. At this point, their contents are kept, but this may change in the future.
        3) All attributes given for a tag in `tags` are used.
        4) Tag attributes existing in the message are ignored. 
        """
        self.assertEqual(
            trans(
                default_locale,
                mock_message_id,
                default='<a0 id="nope">Hello</a0><b0>you</b0><div>there</div>',
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

    def test_trans_nested_tags(self):
        """ Tests that nested tags in messages are not tolerated.
        
        At this point, nested tags are ignored, but their contents are kept.
        This may change in the future.
        """
        self.assertEqual(
            trans(
                default_locale,
                mock_message_id,
                default="<a0>Hello<b0>you</b0><div>there</div></a0>",
                parameters={"a": "you"},
                tags={
                    "a0": {"tag": "a", "attrs": {"href": "/you"}},
                    "b0": {"tag": "b", "attrs": {"id": "hi"}},
                },
            ),
            '<a href="/you">Helloyouthere</a>',
        )

    def test_trans_params_in_tags(self):
        """ Tests that parameters are substituted within tags
        """
        self.assertEqual(
            trans(
                default_locale,
                mock_message_id,
                default="<a0>Hello {name}</a0>{test}",
                parameters={"name": "you", "test": "!"},
                tags={"a0": {"tag": "a", "attrs": {"href": "/you"}}},
            ),
            '<a href="/you">Hello you</a>!',
        )

    def test_trans_escapes_text(self):
        """ Tests that special characters in the text are escaped, in any depth
        """
        self.assertEqual(
            trans(
                default_locale,
                mock_message_id,
                default="<a0>Hello &<b>&</b></a0>>",
                tags={"a0": {"tag": "a", "attrs": {"href": "/you"}}},
            ),
            '<a href="/you">Hello &amp;&amp;</a>&gt;',
        )

    def test_trans_escapes_params(self):
        """ Tests that message parameters are escaped
        """
        self.assertEqual(
            trans(
                default_locale,
                mock_message_id,
                default="<a0>Hello {name}</a0>{test}",
                parameters={"name": "<b>you</b>", "test": "<b>there</b>"},
                tags={"a0": {"tag": "a", "attrs": {"href": "/you"}}},
            ),
            '<a href="/you">Hello &lt;b&gt;you&lt;/b&gt;</a>&lt;b&gt;there&lt;/b&gt;',
        )

    def test_trans_escapes_tag_attrs(self):
        """ Tests that tag attributes in messages are escaped
        """
        self.assertEqual(
            trans(
                default_locale,
                mock_message_id,
                default="<a0>Hello</a0>",
                tags={"a0": {"tag": "a", "attrs": {"href": "/you?a=b&c=d"}}},
            ),
            '<a href="/you?a=b&amp;c=d">Hello</a>',
        )

    def test_trans_tag_placeholders(self):
        """ Tests the combination of properties of placeholder tags and of message parameters.
        
        0) In settings where there are multiple tags, some of which have to be deleted, all of them are processed
        1) the `tags` argument is used to replace placeholders and they are escaped correctly
        2) Tags or tag placeholders that have no counterpart in the arguments are removed
        3) Special characters, except for the ones of valid tags, are escaped
        4) Nested tags are not tolerated
        5) `arg_XX` arguments are replaced and escaped correctly
        """
        self.assertEqual(
            trans(
                default_locale,
                mock_message_id,
                default='<span0 class="nope">Hello {first}</span0><span1></span1> {second} <a0>{a}<b></b></a0> < <a1>there<</a1>!<br /><script type="text/javascript" src="mybadscript.js"></script>',
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
            '<span id="hi">Hello hello</span> &amp; <a href="/you">you</a> &lt; <a class="red big" href="/there?a=b&amp;c=d">there&lt;</a>!',
        )
