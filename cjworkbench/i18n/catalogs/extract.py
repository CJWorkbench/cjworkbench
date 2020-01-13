# -*- coding: utf-8 -*-
from django.template.base import Lexer, TokenType
from django.utils.translation import trim_whitespace
from django.utils.encoding import smart_text
import re
from babel.util import parse_encoding, parse_future_flags
from babel._compat import PY2, text_type
from tokenize import generate_tokens, COMMENT, NAME, OP, STRING
from cjworkbench.i18n.catalogs import COMMENT_TAG_FOR_DEFAULT_MESSAGE
from io import BytesIO
from typing import Any, Tuple, Dict, List, Generator

TOKEN_BLOCK = TokenType.BLOCK

# re adapted from django.utils.translation.template.inline_re
inline_re = re.compile(
    # Match the trans 'some text' part
    r"""^\s*trans_html\s+((?:"[^"]*?")|(?:'[^']*?'))"""
    # Match and ignore optional filters
    r"""(?:\s*\|\s*[^\s:]+(?::(?:[^\s'":]+|(?:"[^"]*?")|(?:'[^']*?')))?)*"""
    # Match the optional default argument
    r"""(\s+.*default=((?:"[^"]*?")|(?:'[^']*?')))?\s*?"""
    # Match the optional context part
    r"""(\s+.*ctxt=((?:"[^"]*?")|(?:'[^']*?')))?\s*?"""
    # Match the optional comment part
    r"""(\s+.*comment=((?:"[^"]*?")|(?:'[^']*?')))?\s*"""
)


def strip_quotes(s):
    if (s[0] == s[-1]) and s.startswith(("'", '"')):
        return s[1:-1]
    return s


def extract_django(fileobj, keywords, comment_tags, options):
    """Extract messages from Django template files.
    
    Adapted from https://github.com/python-babel/django-babel/blob/master/django_babel/extract.py
    
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
                    comments = [
                        COMMENT_TAG_FOR_DEFAULT_MESSAGE
                        + ": "
                        + strip_quotes(default_message)
                    ]
                else:
                    comments = []
                comment = imatch.group(7)
                if comment:
                    comments.append(strip_quotes(comment))
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


def extract_python(
    fileobj: BytesIO, _keywords: Any, _comment_tags: Any, options: Dict[Any, Any]
) -> Generator[Tuple[int, str, List[Any], List[str]], None, None]:
    """Extract messages from project python code.
    
    :param fileobj: the seekable, file-like object the messages should be
                    extracted from
    :param _keywords: Ignored
    :param _comment_tags: Ignored
    :param options: a dictionary of additional options (optional)
    :rtype: ``iterator``
    """
    keywords = ["trans", "trans_lazy"]
    comment_tags = ["i18n"]
    for (message_lineno, funcname, messages, translator_comments) in _parse_python(
        fileobj, keywords, comment_tags, options
    ):
        if funcname in ["trans", "trans_lazy"]:
            # `messages` will have all the string parameters to our function
            # As we specify in the documentation of `trans`,
            # the first will be the message ID, the second will be the default message
            # and the (optional) third will be the message context
            if len(messages) > 1 and messages[1]:
                # If we have a default, add it as a special comment
                # that will be processed by our `merge_catalogs` script
                translator_comments.append(
                    (message_lineno, "default-message: " + messages[1])
                )

            if len(messages) > 2 and isinstance(messages[2], str):
                context = messages[2]
            else:
                context = None

            if context:
                # if we have a context, trick pybabel to use `pgettext`
                # so that it adds the context to the translation file
                funcname = "pgettext"
                messages = [context, messages[0]]
            else:
                # Pybabel expects a `funcname` of the `gettext` family, or `None`.
                funcname = None
        yield (
            message_lineno,
            funcname,
            messages,
            [comment[1] for comment in translator_comments],
        )


def extract_module_code(
    fileobj: BytesIO, _keywords: Any, _comment_tags: Any, options: Dict[Any, Any]
) -> Generator[Tuple[int, str, List[Any], List[str]], None, None]:
    """Extract messages from module python code.
    
    :param fileobj: the seekable, file-like object the messages should be
                    extracted from
    :param _keywords: Ignored
    :param _comment_tags: Ignored
    :param options: a dictionary of additional options (optional)
    :rtype: ``iterator``
    """
    keywords = ["trans"]
    comment_tags = ["i18n"]
    for (message_lineno, funcname, messages, translator_comments) in _parse_python(
        fileobj, keywords, comment_tags, options
    ):
        # `messages` will have all the string parameters to our function
        # As we specify in the documentation of `trans`,
        # the first will be the message ID and the second will be the default message.
        # If the message ID is a string (i.e. not a variable),
        # then we require the default message to also be a string.

        if messages[0] is not None:
            if messages[1] is None:
                error = SyntaxError("Default message must not be passed as a variable")
                error.lineno = message_lineno
                error.filename = "Module code"
                raise error

            # If we have a default, add it as a special comment
            # that will be processed by our `merge_catalogs` script
            translator_comments.append(
                (message_lineno, "default-message: " + messages[1])
            )

        # Pybabel expects a `funcname` of the `gettext` family, or `None`.
        funcname = None

        yield (
            message_lineno,
            funcname,
            messages,
            [comment[1] for comment in translator_comments],
        )


def _parse_python(
    fileobj: BytesIO,
    keywords: List[str],
    comment_tags: List[str],
    options: Dict[Any, Any],
) -> Generator[Tuple[int, str, List[Any], List[Tuple[int, str]]], None, None]:
    """Extract message raw data from Python source code.
    It returns an iterator yielding tuples in the following form:
     `(lineno, funcname, message, comments)`.
    
    Adapted from the pybabel built-in `extract_python` function.
    
    :param fileobj: the seekable, file-like object the messages should be
                    extracted from
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :rtype: ``iterator``
    """
    funcname = lineno = message_lineno = None
    call_stack = -1
    buf = []
    messages = []
    translator_comments = []
    in_def = in_translator_comments = False
    comment_tag = None

    encoding = parse_encoding(fileobj) or options.get("encoding", "UTF-8")
    future_flags = parse_future_flags(fileobj, encoding)

    if PY2:
        next_line = fileobj.readline
    else:
        next_line = lambda: fileobj.readline().decode(encoding)

    tokens = generate_tokens(next_line)
    for tok, value, (lineno, _), _, _ in tokens:
        if call_stack == -1 and tok == NAME and value in ("def", "class"):
            in_def = True
        elif tok == OP and value == "(":
            if in_def:
                # Avoid false positives for declarations such as:
                # def gettext(arg='message'):
                in_def = False
                continue
            if funcname:
                message_lineno = lineno
                call_stack += 1
        elif in_def and tok == OP and value == ":":
            # End of a class definition without parens
            in_def = False
            continue
        elif call_stack == -1 and tok == COMMENT:
            # Strip the comment token from the line
            if PY2:
                value = value.decode(encoding)
            value = value[1:].strip()
            if in_translator_comments and translator_comments[-1][0] == lineno - 1:
                # We're already inside a translator comment, continue appending
                translator_comments.append((lineno, value))
                continue
            # If execution reaches this point, let's see if comment line
            # starts with one of the comment tags
            for comment_tag in comment_tags:
                if value.startswith(comment_tag):
                    in_translator_comments = True
                    translator_comments.append((lineno, value))
                    break
        elif funcname and call_stack == 0:
            nested = tok == NAME and value in keywords
            if (tok == OP and value == ")") or nested:
                if buf:
                    messages.append("".join(buf))
                    del buf[:]
                else:
                    messages.append(None)

                if len(messages) > 1:
                    messages = tuple(messages)
                else:
                    messages = messages[0]
                # Comments don't apply unless they immediately preceed the
                # message
                if (
                    translator_comments
                    and translator_comments[-1][0] < message_lineno - 1
                ):
                    translator_comments = []

                yield (message_lineno, funcname, messages, translator_comments)

                funcname = lineno = message_lineno = None
                call_stack = -1
                messages = []
                translator_comments = []
                in_translator_comments = False
                if nested:
                    funcname = value
            elif tok == STRING:
                # Unwrap quotes in a safe manner, maintaining the string's
                # encoding
                # https://sourceforge.net/tracker/?func=detail&atid=355470&
                # aid=617979&group_id=5470
                code = compile(
                    "# coding=%s\n%s" % (str(encoding), value),
                    "<string>",
                    "eval",
                    future_flags,
                )
                value = eval(code, {"__builtins__": {}}, {})
                if PY2 and not isinstance(value, text_type):
                    value = value.decode(encoding)
                buf.append(value)
            elif tok == OP and value == ",":
                if buf:
                    messages.append("".join(buf))
                    del buf[:]
                else:
                    messages.append(None)
                if translator_comments:
                    # We have translator comments, and since we're on a
                    # comma(,) user is allowed to break into a new line
                    # Let's increase the last comment's lineno in order
                    # for the comment to still be a valid one
                    old_lineno, old_comment = translator_comments.pop()
                    translator_comments.append((old_lineno + 1, old_comment))
        elif call_stack > 0 and tok == OP and value == ")":
            call_stack -= 1
        elif funcname and call_stack == -1:
            funcname = None
        elif tok == NAME and value in keywords:
            funcname = value
