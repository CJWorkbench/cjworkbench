import logging
import re
from django.test import SimpleTestCase
from cjworkbench.i18n import default_locale
from cjworkbench.tests.test_trans import mock_message_id
from server.templatetags.i18n_icu import trans_html


def mock_context(**kwargs):
    return {"i18n": {"locale_id": kwargs.get("locale_id", default_locale)}}


class TransTemplateTagTests(SimpleTestCase):
    # Tests that `noop=True` returns `None`
    def test_trans_noop(self):
        self.assertIsNone(
            trans_html(
                mock_context(), mock_message_id, noop=True, default="Hello {a} {b}!"
            )
        )

    # Tests that `arg_XX` arguments replace variables in the message.
    # 1) Parameters that do not exist in the message are ignored.
    # 2) Variables in the message for which no parameter has been given are ignored.
    # 3) The order of `arg` arguments is not important.
    # 4) When the programmer tries to use numeric arguments, an exception is raised (behaviour for when the translator tries to use numeric arguments is tested elsewhere)
    def test_trans_params(self):
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

    def test_trans_tag_without_attributes(self):
        self.assertEqual(
            trans_html(
                mock_context(),
                mock_message_id,
                default="Hello <b0>{param_b}</b0>!",
                arg_param_b="there",
                tag_b0="",
            ),
            "Hello <b>there</b>!",
        )

    # Tests the combination of properties of placeholder tags and of message parameters.
    # 0) In settings where there are multiple tags, some of which have to be deleted, all of them are processed
    # 1) `tag_XX_YY` arguments are used to replace placeholders; existing attributes are removed
    # 2) Tags without attributes are supported
    # 3) Tags or placeholders that have no counterpart in the arguments are removed
    # 4) The order of `tag` arguments is not important
    # 5) Special characters, except for the ones of valid tags, are escaped, even in tag attributes and in args
    # 6) Nested tags are not tolerated
    # 7) `arg_XX` arguments are replaced correctly
    def test_trans_tag_placeholders(self):
        self.assertEqual(
            trans_html(
                mock_context(),
                mock_message_id,
                default='<em0>Hello</em0> <span0 class="nope">{first}</span0><span1></span1> {second} <a0>{a}<b></b></a0> < <a1>there<</a1>!<br /><script type="text/javascript" src="mybadscript.js"></script>',
                arg_a="you",
                tag_a0_href="/you",
                tag_a1_href="/there?a=b&c=d",
                tag_a1_class="red big",
                tag_span0_id="hi",
                tag_em0="",
                tag_div0_class="red big",
                arg_first="hello",
                arg_second="&",
            ),
            '<em>Hello</em> <span id="hi">hello</span> &amp; <a href="/you">you</a> &lt; <a class="red big" href="/there?a=b&amp;c=d">there&lt;</a>!',
        )

    def test_trans_html_with_missing_context_i18n(self):
        # context[i18n] needs to be managed by the caller. And sometimes, the
        # caller has a bug. (Seen 2019-08-2019-12-06 01:57:19.327 GMT.) We want
        # Django's exception-handling code to be able to call trans_html().
        #
        # Calling trans_html without a context[i18n] is always a bug. So let's
        # test that it's logged.
        with self.assertLogs(level=logging.ERROR) as cm:
            result = trans_html(
                {"invalid-context": "yup"}, mock_message_id, default="Show the message"
            )
        self.assertEqual(result, "Show the message")
        self.assertRegex(
            cm.output[0],
            re.escape(
                (
                    "ERROR:server.templatetags.i18n_icu:"
                    "Missing context['i18n']['locale_id'] translating message_id "
                )
                + mock_message_id
            ),
        )
