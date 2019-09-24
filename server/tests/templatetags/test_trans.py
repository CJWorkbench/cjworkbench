from django.test import SimpleTestCase
from server.templatetags.i18n_icu import trans
from cjworkbench.i18n import default_locale


class MockRequest(object):
    def __init__(self, **kwargs):
        self.locale_id = kwargs.get("locale_id", default_locale)


def mock_context(**kwargs):
    return {"request": MockRequest(**kwargs)}


mock_message_id = (
    "some+crazy+id+that+will+never+be+actually+used+in+real+translation+files"
)


class TransTemplateTagTests(SimpleTestCase):
    def test_trans_default(self):
        self.assertEqual(
            trans(mock_context(), mock_message_id, default="The default"), "The default"
        )

    def test_trans_noop(self):
        self.assertIsNone(
            trans(mock_context(), mock_message_id, noop=True, default="Hello {a} {b}!")
        )

    def test_trans_params(self):
        self.assertEqual(
            trans(
                mock_context(),
                mock_message_id,
                default="Hello {a} {b}!",
                arg_a="you",
                arg_b="there",
            ),
            "Hello you there!",
        )

    def test_trans_tag_placeholders(self):
        self.assertEqual(
            trans(
                mock_context(),
                mock_message_id,
                default='<span0>Hello</span0> <a0>{a}<b></b></a0> < <a1>there<</a1>!<br /><script type="text/javascript" src="mybadscript.js"></script>',
                arg_a="you",
                tag_a0_href="/you",
                tag_a1_href="/there",
                tag_a1_class="red big",
            ),
            'Hello <a href="/you">you</a> &lt; <a class="red big" href="/there">there&lt;</a>!',
        )
