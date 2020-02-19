from typing import Any, Dict, List, Literal, Union, Tuple


I18nMessageSource = Literal["module", "cjwmodule", None]
"""Which catalog we should search to find the text of the message.

* "module": the module's zipfile
* "cjwmodule": the cjwmodule library
* None: cjworkbench proper
"""

I18nMessage = Union[
    Tuple[str, Dict[str, Any]], Tuple[str, Dict[str, Any], I18nMessageSource]
]
Message = Union[str, I18nMessage]

RenderError = Union[Message, Dict[str, Union[Message, List[Any]]]]
"""A single render error (with or without quick fixes) returned from a module.

It may be:

* a plain string
* a tuple of message id and message arguments, 
  e.g. `("negative_number", {"param": "that"})` or `("general_error", {})`
* a dict with two keys: `"message": Message` and `"quickFixes": List[Any]`
"""
# We can define the dict more precisely in python 3.8 using a `TypedDict`

RenderErrors = Union[RenderError, List[RenderError]]
"""One or more render errors returned from a module."""
