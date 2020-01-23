from typing import Any, Dict, Iterable, List, Optional, Union, Tuple

I18nMessageSource = Dict[str, str]
""" Indicates which catalog we should search to find the text of the message.
    - A dict with key `"module"` means it's coming from a module;
      for example `{"module": "mymodule"}` means, "search the mymodule module's catalog"
    - A dict with key `"library"` indicates it's coming from some of our supported libraries;
      for example `{"library": "cjwmodule"}` means, "search the cjwmodule library's catalog"
"""
# We can define the dict more precisely in python 3.8 using a `TypedDict`


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
