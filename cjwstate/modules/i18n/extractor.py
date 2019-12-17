from babel.messages.extract import extract
from cjworkbench.i18n.catalogs.merge import default_message_re
import pathlib
from cjworkbench.i18n.catalogs.extract import extract_python
from typing import Dict, Any


def find_messages_in_module_code(
    code_path: pathlib.Path, root_path: pathlib.Path
) -> Dict[str, Dict[str, Any]]:
    messages = {}
    with open(code_path, "rb") as code_file:
        messages_data = extract(extract_python, code_file)
        relative_path_name = str(code_path.relative_to(root_path))
        for lineno, message_id, comments, context in messages_data:
            default_message = ""
            for comment in comments:
                match = default_message_re.match(comment)
                if match:
                    default_message = match.group(1).strip()
                    comments.remove(comment)
            messages[message_id] = {
                "string": default_message,
                "comments": comments,
                "locations": [(relative_path_name, lineno)],
            }
    return messages
