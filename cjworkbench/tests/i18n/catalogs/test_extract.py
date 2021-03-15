import unittest
from babel.messages.catalog import Catalog
from cjworkbench.i18n.catalogs.extract import extract_python, extract_django
from cjworkbench.tests.i18n.catalogs.util import assert_catalogs_deeply_equal
from io import BytesIO
from typing import List, Tuple, Union

ExtractionTuple = Tuple[int, str, Union[str, List[str]], List[str]]


def _extract_python(code: BytesIO) -> List[ExtractionTuple]:
    return list(extract_python(code, None, None, {}))


def _mock_django_extraction_tuple(
    lineno: int,
    message_id: str,
    default: str,
    context: str = None,
    comments: List[str] = [],
) -> ExtractionTuple:
    i18n_comments = [f"default-message: {default}"]
    i18n_comments.extend(comments)
    if context:
        return (lineno, "pgettext", [context, message_id], i18n_comments)
    else:
        return (lineno, None, message_id, i18n_comments)


def _extract_django(code: BytesIO) -> List[ExtractionTuple]:
    return list(extract_django(code, None, None, {}))


def _mock_python_extraction_tuple(
    lineno: int, message_id: str, default: str, comments: List[str] = []
) -> ExtractionTuple:
    i18n_comments = list(comments)
    i18n_comments.append(f"default-message: {default}")
    return (lineno, None, message_id, i18n_comments)


class ExtractDjangoTest(unittest.TestCase):
    def test_no_translations(self):
        code = BytesIO(
            b"""
        {% if that %}
            {{ this }}
        {% else %}
            {{ the_other }}
        {% endif %}
        """
        )
        expected = []
        self.assertEqual(_extract_django(code), expected)

    def test_trans_html_simple_message(self):
        code = BytesIO(
            b"""{% load i18n_icu %}
    {% trans_html "id" default="default" %}
        """
        )
        expected = [_mock_django_extraction_tuple(2, "id", "default")]
        self.assertEqual(_extract_django(code), expected)

    def test_trans_html_with_parameters(self):
        code = BytesIO(
            b"""{% load i18n_icu %}
    {% trans_html "id" default="default {a}" arg_a='b' %}
        """
        )
        expected = [_mock_django_extraction_tuple(2, "id", "default {a}")]
        self.assertEqual(_extract_django(code), expected)

    def test_trans_html_with_parameters_and_comment(self):
        code = BytesIO(
            b"""{% load i18n_icu %}
    {% trans_html "id" default="default {a}" comment="Some comment" arg_a='b' %}
        """
        )
        expected = [
            _mock_django_extraction_tuple(
                2, "id", "default {a}", comments=["Some comment"]
            )
        ]
        self.assertEqual(_extract_django(code), expected)

    def test_trans_html_with_tag(self):
        code = BytesIO(
            b"""{% load i18n_icu %}
    {% trans_html "id" default="<a0>default</a0>" tag_a0_href='/b' %}
        """
        )
        expected = [_mock_django_extraction_tuple(2, "id", "<a0>default</a0>")]
        self.assertEqual(_extract_django(code), expected)

    def test_trans_html_with_context(self):
        code = BytesIO(
            b"""{% load i18n_icu %}
    {% trans_html "id" default="default" ctxt='ctxt' %}
        """
        )
        expected = [_mock_django_extraction_tuple(2, "id", "default", context="ctxt")]
        self.assertEqual(_extract_django(code), expected)

    def test_trans_html_with_context_and_comment(self):
        code = BytesIO(
            b"""{% load i18n_icu %}
    {% trans_html "id" default="default" ctxt='ctxt' comment="Some comment" %}
        """
        )
        expected = [
            _mock_django_extraction_tuple(
                2, "id", "default", context="ctxt", comments=["Some comment"]
            )
        ]
        self.assertEqual(_extract_django(code), expected)

    def test_trans_html_with_context_comment_and_parameters(self):
        code = BytesIO(
            b"""{% load i18n_icu %}
    {% trans_html "id" default="default {a}" ctxt='ctxt' arg_a='b' comment="Some comment" %}
        """
        )
        expected = [
            _mock_django_extraction_tuple(
                2, "id", "default {a}", context="ctxt", comments=["Some comment"]
            )
        ]
        self.assertEqual(_extract_django(code), expected)


class ExtractPythonTest(unittest.TestCase):
    def test_no_translations(self):
        code = BytesIO(
            b"""
def test():
    return 1
        """
        )
        expected = []
        self.assertEqual(_extract_python(code), expected)

    def test_trans_simple_message(self):
        code = BytesIO(
            b"""
def test():
    return trans('id', default='default')
        """
        )
        expected = [_mock_python_extraction_tuple(3, "id", "default")]
        self.assertEqual(_extract_python(code), expected)

    def test_trans_with_parameters(self):
        code = BytesIO(
            b"""
def test():
    return trans('id', default='default {a}', parameters={'a': 'b'})
        """
        )
        expected = [_mock_python_extraction_tuple(3, "id", "default {a}")]
        self.assertEqual(_extract_python(code), expected)

    def test_trans_with_comment_and_parameters(self):
        code = BytesIO(
            b"""
def test():
    # i18n: Some comment
    return trans('id', default='default {a}', parameters={'a': 'b'})
        """
        )
        expected = [
            _mock_python_extraction_tuple(
                4, "id", "default {a}", comments=["i18n: Some comment"]
            )
        ]
        self.assertEqual(_extract_python(code), expected)

    def test_i18n_message_simple_message(self):
        code = BytesIO(
            b"""
def test():
    return trans('id', default='default')
        """
        )
        expected = [_mock_python_extraction_tuple(3, "id", "default")]
        self.assertEqual(_extract_python(code), expected)

    def test_i18n_message_with_parameters(self):
        code = BytesIO(
            b"""
def test():
    return trans('id', default='default {a}', parameters={'a': 'b'})
        """
        )
        expected = [_mock_python_extraction_tuple(3, "id", "default {a}")]
        self.assertEqual(_extract_python(code), expected)

    def test_i18n_message_with_comment_and_parameters(self):
        code = BytesIO(
            b"""
def test():
    # i18n: Some comment
    return trans('id', default='default {a}', parameters={'a': 'b'})
        """
        )
        expected = [
            _mock_python_extraction_tuple(
                4, "id", "default {a}", comments=["i18n: Some comment"]
            )
        ]
        self.assertEqual(_extract_python(code), expected)
