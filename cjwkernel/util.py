import json
from typing import Any, Dict


def json_encode(value: Dict[str, Any]) -> str:
    """
    Encode as JSON, without Python's stupid defaults.
    """
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
