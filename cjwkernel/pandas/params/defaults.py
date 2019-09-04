# Functions that will appear in a loaded module, unless user code defines the
# functions differently.

from typing import Any, Dict


def migrate_params(params: Dict[str, Any]) -> Dict[str, Any]:
    return params
