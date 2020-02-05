from typing import Any, Dict, Iterable, List, Optional, Union, Tuple, NewType


I18nMessageSource = NewType("I18nMessageSource", str)
""" Indicates which catalog we should search to find the text of the message.
    - `"module"` means it's coming from a module;
      when localizing, we should look into the current context to find which module it is
    - `"cjwmodule"` means it's coming from `cjwmodule`
"""
# We should use a `typing.Literal` in python 3.8

I18nMessage = Union[
    Tuple[str, Dict[str, Any]], Tuple[str, Dict[str, Any], I18nMessageSource]
]
Message = Union[str, I18nMessage]

RenderError = Union[Message, Dict[str, Union[Message, List[Any]]]]
""" A single render error (with or without quick fixes) returned from a module
It can be
  - a plain string
  - a tuple of message id and message arguments, 
    e.g. `("negative_number", {"param": "that"})` or `("general_error", {})`
  - a dict with two keys: `"message": Message` and `"quickFixes": List[Any]`

"""
# We can define the dict more precisely in python 3.8 using a `TypedDict`

RenderErrors = Union[RenderError, List[RenderError]]
""" One or more render errors returned from a module
It can be:
  - anything that `RenderError` can be
  - a list of `RenderError`
"""
