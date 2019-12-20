from babel.messages.extract import extract
import pathlib
import re
from typing import Dict, Any
from cjworkbench.i18n.catalogs.extract import extract_module_code


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
        extract_module_code,
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
