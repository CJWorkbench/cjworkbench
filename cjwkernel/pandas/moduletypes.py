from typing import Any, Dict, Iterable, List, Optional, Union, Tuple

I18nMessage = Tuple[str, Dict[str, Any]]
Message = Union[str, I18nMessage]
RenderError = Union[Message, Dict[str, Union[Message, List[Any]]]]
# The dict must have keys `"message": Message` and `"quickFixes": List[Any]`. We can define it in python 3.8 using `TypedDict`s
RenderErrors = Union[RenderError, List[RenderError]]
""" RenderErrors is the type we expect from modules to return when there is an error.
When coercing to pandas types, we convert it to the simpler (pandas) type `List[ProcessResultError]` held in (pandas) `ProcessResult`.
"""
