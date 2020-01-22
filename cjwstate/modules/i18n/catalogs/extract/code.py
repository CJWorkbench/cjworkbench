import io
import re
from typing import Dict, Any
from babel.messages.extract import extract
from cjworkbench.i18n.catalogs.extract import extract_module_code


_default_message_re = re.compile(r"\s*default-message:\s*(.*)\s*")


def find_messages_in_module_code(
    code_io: io.BytesIO, filename: str
) -> Dict[str, Dict[str, Any]]:
    messages_data = extract(extract_module_code, code_io)
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
            messages[message_id]["locations"].append((filename, lineno))
        else:
            messages[message_id] = {
                "string": default_message,
                "comments": comments,
                "locations": [(filename, lineno)],
            }
    return messages
