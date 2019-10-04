from django.test import SimpleTestCase
from server.templatetags.i18n_icu import trans_html
from cjworkbench.i18n import default_locale
from cjworkbench.tests.i18n import mock_message_id


class MockRequest(object):
    def __init__(self, **kwargs):
        self.locale_id = kwargs.get("locale_id", default_locale)


def mock_context(**kwargs):
    return {"request": MockRequest(**kwargs)}


class TransTemplateTagTests(SimpleTestCase):
    def test_trans_noop(self):
        """Tests that `noop=True` returns `None`
        """
        self.assertIsNone(
            trans_html(
                mock_context(), mock_message_id, noop=True, default="Hello {a} {b}!"
            )
        )

    def test_trans_params(self):
        """Tests that `arg_XX` arguments replace variables in the message.
        
        1) Parameters that do not exist in the message are ignored.
        2) Variables in the message for which no parameter has been given are ignored.
        3) The order of `arg` arguments is not important.
        4) When the programmer tries to use numeric arguments, an exception is raised
           (behaviour for when the translator tries to use numeric arguments is tested elsewhere)
        """
        self.assertEqual(
            trans_html(
                mock_context(),
                mock_message_id,
                default="Hello {a} {param_b} {c}!",
                arg_param_b="there",
                arg_a="you",
                arg_d="tester",
            ),
            "Hello you there {c}!",
        )

        with self.assertRaises(Exception):
            trans_html(
                mock_context(),
                mock_message_id,
                default="Hello {a} {0} {b}",
                arg_a="you",
                arg_0="!",
                arg_b="2",
            ),

    def test_trans_tag_placeholders(self):
        """ Tests the combination of properties of placeholder tags and of message parameters.
        
        0) In settings where there are multiple tags, some of which have to be deleted, all of them are processed
        1) `tag_XX_YY` arguments are used to replace placeholders; existing attributes are removed
        2) Tags or placeholders that have no counterpart in the arguments are removed
        3) The order of `tag` arguments is not important
        4) Special characters, except for the ones of valid tags, are escaped, even in tag attributes and in args
        5) Nested tags are not tolerated
        6) `arg_XX` arguments are replaced correctly
        """
        self.assertEqual(
            trans_html(
                mock_context(),
                mock_message_id,
                default='<span0 class="nope">Hello {first}</span0><span1></span1> {second} <a0>{a}<b></b></a0> < <a1>there<</a1>!<br /><script type="text/javascript" src="mybadscript.js"></script>',
                arg_a="you",
                tag_a0_href="/you",
                tag_a1_href="/there?a=b&c=d",
                tag_a1_class="red big",
                tag_span0_id="hi",
                tag_div0_class="red big",
                arg_first="hello",
                arg_second="&",
            ),
            '<span id="hi">Hello hello</span> &amp; <a href="/you">you</a> &lt; <a class="red big" href="/there?a=b&amp;c=d">there&lt;</a>!',
        )
