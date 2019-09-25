# -*- coding: utf-8 -*-
# file adapted from https://github.com/python-babel/django-babel/blob/master/django_babel/extract.py
from django.template.base import Lexer, TokenType
from django.utils.translation import trim_whitespace
from django.utils.encoding import smart_text
import re

TOKEN_BLOCK = TokenType.BLOCK

# re adapted from django.utils.translation.template.inline_re
inline_re = re.compile(
    # Match the trans 'some text' part
    r"""^\s*trans\s+((?:"[^"]*?")|(?:'[^']*?'))"""
    # Match and ignore optional filters
    r"""(?:\s*\|\s*[^\s:]+(?::(?:[^\s'":]+|(?:"[^"]*?")|(?:'[^']*?')))?)*"""
    # Match the optional default argument
    r"""(\s+.*default=((?:"[^"]*?")|(?:'[^']*?')))?\s*?"""
    # Match the optional context part
    r"""(\s+.*ctxt=((?:"[^"]*?")|(?:'[^']*?')))?\s*?"""
    # Match the optional comment part
    r"""(\s+.*comment=((?:"[^"]*?")|(?:'[^']*?')))?\s*"""
)


def join_tokens(tokens, trim=False):
    message = "".join(tokens)
    if trim:
        message = trim_whitespace(message)
    return message


def strip_quotes(s):
    if (s[0] == s[-1]) and s.startswith(("'", '"')):
        return s[1:-1]
    return s


def extract_django(fileobj, keywords, comment_tags, options):
    """Extract messages from Django template files.
    :param fileobj: the file-like object the messages should be extracted from
    :param keywords: a list of keywords (i.e. function names) that should
                     be recognized as translation functions
    :param comment_tags: a list of translator tags to search for and
                         include in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)``
             tuples
    :rtype: ``iterator``
    """
    intrans = False
    inplural = False
    trimmed = False
    message_context = None
    singular = []
    plural = []
    lineno = 1

    encoding = options.get("encoding", "utf8")
    text = fileobj.read().decode(encoding)

    try:
        text_lexer = Lexer(text)
    except TypeError:
        # Django 1.9 changed the way we invoke Lexer; older versions
        # require two parameters.
        text_lexer = Lexer(text, None)

    # raise SystemError([t.contents for t in text_lexer.tokenize()])

    for t in text_lexer.tokenize():
        lineno += t.contents.count("\n")
        if t.token_type == TOKEN_BLOCK:
            imatch = inline_re.match(t.contents)
            if imatch:
                g = imatch.group(1)
                g = strip_quotes(g)
                default_message = imatch.group(3)
                if default_message:
                    comments = ["default-message: " + strip_quotes(default_message)]
                else:
                    comments = []
                comment = imatch.group(7)
                if comment:
                    comments.append(comment)
                message_context = imatch.group(5)
                if message_context:
                    # strip quotes
                    message_context = message_context[1:-1]
                    yield (
                        lineno,
                        "pgettext",
                        [smart_text(message_context), smart_text(g)],
                        comments,
                    )
                    message_context = None
                else:
                    yield lineno, None, smart_text(g), comments
