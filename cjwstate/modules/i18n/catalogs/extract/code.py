from babel.messages.extract import extract
import pathlib
import re
from typing import Dict, Any
from babel.util import parse_encoding, parse_future_flags
from babel._compat import PY2, text_type
from tokenize import generate_tokens, COMMENT, NAME, OP, STRING


_default_message_re = re.compile(r"\s*default-message:\s*(.*)\s*")


def find_messages_in_module_code(
    code_path: pathlib.Path, root_path: pathlib.Path
) -> Dict[str, Dict[str, Any]]:
    with open(code_path, "rb") as code_file:
        return _find_messages_in_module_code(
            code_file, str(code_path.relative_to(root_path))
        )


def _find_messages_in_module_code(
    code_file, relative_path_name: str
) -> Dict[str, Dict[str, Any]]:
    messages_data = extract(
        _extract_module_code,
        code_file,
        keywords={"trans": (1, 2)},
        comment_tags=["i18n"],
    )
    messages = {}
    for lineno, message_id, comments, context in messages_data:
        default_message = ""
        for comment in comments:
            match = _default_message_re.match(comment)
            if match:
                default_message = match.group(1).strip()
                comments.remove(comment)
        if message_id in messages:
            messages[message_id]["comments"].extend(comments)
            messages[message_id]["locations"].append((relative_path_name, lineno))
        else:
            messages[message_id] = {
                "string": default_message,
                "comments": comments,
                "locations": [(relative_path_name, lineno)],
            }
    return messages


def _extract_module_code(fileobj, keywords, comment_tags, options):
    """Extract messages from Python source code of modules.
    It returns an iterator yielding tuples in the following form ``(lineno,
    funcname, message, comments)``.
    
    Adapted from the pybabel built-in function `extract_python`,
    so that it understands the syntax of our custom `i18n.trans` function
    and correctly parses the default message.
    
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

                ### HERE start our modifications to pybabel's script
                if funcname == "trans":
                    # `messages` will have all the string parameters to our function
                    # As we specify in the documentation of `trans`,
                    # the first will be the message ID and the second will be the default message.
                    # If the message ID is a string (i.e. not a variable),
                    # then we require the default message to also be a string.

                    if messages[0] is not None:
                        if messages[1] is None:
                            error = SyntaxError(
                                "Default message must not be passed as a variable"
                            )
                            error.lineno = message_lineno
                            error.filename = "Module code"
                            raise error

                        # If we have a default, add it as a special comment
                        # that will be processed by our `merge_catalogs` script
                        translator_comments.append(
                            (message_lineno, "default-message: " + messages[1])
                        )

                    funcname = None
                ### HERE end our modifications to pybabel's script

                yield (
                    message_lineno,
                    funcname,
                    messages,
                    [comment[1] for comment in translator_comments],
                )

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
