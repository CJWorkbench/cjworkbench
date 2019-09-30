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
    def test_trans_no_default(self):
        """Tests that when no default is given, the message id is returned
        """
        self.assertEqual(trans_html(mock_context(), mock_message_id), mock_message_id)

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
        
        1) Missing variables are ignored.
        2) The order of `arg` arguments is not important.
        3) When the programmer tries to use numeric arguments, an exception is raised
           (behaviour for when the translator tries to use numeric arguments is tested elsewhere)
        """
        self.assertEqual(
            trans_html(
                mock_context(),
                mock_message_id,
                default="Hello {a} {param_b} {c}!",
                arg_param_b="there",
                arg_a="you",
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
        """ Tests that placeholder tags work as intended.
        
        1) `tag_XX_YY` arguments are used to replace placeholders
        2) Tags or placeholders that have no counterpart in the arguments are removed
        3) The order of `tag` arguments is not important
        4) Special characters, except for the ones of valid tags, are escaped
        5) In settings where there are multiple tags, some of which have to be deleted, all of them are processed
        
        Does not test what happens to nested tags, since we have no hard policy
        """
        self.assertEqual(
            trans_html(
                mock_context(),
                mock_message_id,
                default='<span0>Hello</span0><span1></span1> <a0>{a}<b></b></a0> < <a1>there<</a1>!<br /><script type="text/javascript" src="mybadscript.js"></script>',
                arg_a="you",
                tag_a0_href="/you",
                tag_a1_href="/there",
                tag_a1_class="red big",
                tag_span0_id="hi",
            ),
            '<span id="hi">Hello</span> <a href="/you">you</a> &lt; <a class="red big" href="/there">there&lt;</a>!',
        )

    def test_trans_nested_tags(self):
        """ Tests that nested tags in messages are not tolerated.
        
        At this point, nested tags are ignored, but their contents are kept.
        This may change in the future.
        """
        self.assertEqual(
            trans_html(
                mock_context(),
                mock_message_id,
                default="<a0>Hello<b0>you</b0><div>there</div></a0>",
                arg_a="you",
                tag_a0_href="/you",
                tag_b0_id="hi",
            ),
            '<a href="/you">Helloyouthere</a>',
        )

    def test_trans_params_in_tags(self):
        """ Tests that parameters are substituted within tags
        """
        self.assertEqual(
            trans_html(
                mock_context(),
                mock_message_id,
                default="<a0>Hello {name}</a0>{test}",
                arg_name="you",
                arg_test="!",
                tag_a0_href="/you",
            ),
            '<a href="/you">Hello you</a>!',
        )

    def test_trans_escapes_params(self):
        """ Tests that message parameters are escaped
        """
        self.assertEqual(
            trans_html(
                mock_context(),
                mock_message_id,
                default="<a0>Hello {name}</a0>{test}",
                arg_name="<b>you</b>",
                arg_test="<b>there</b>",
                tag_a0_href="/you",
            ),
            '<a href="/you">Hello &lt;b&gt;you&lt;/b&gt;</a>&lt;b&gt;there&lt;/b&gt;',
        )

    def test_trans_escapes_tag_attrs(self):
        """ Tests that tag attributes in messages are escaped
        """
        self.assertEqual(
            trans_html(
                mock_context(),
                mock_message_id,
                default="<a0>Hello</a0>",
                tag_a0_href="/you?a=b&c=d",
            ),
            '<a href="/you?a=b&amp;c=d">Hello</a>',
        )
