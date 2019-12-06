from typing import Any, Dict, Iterable, List, Optional, Union, Tuple

ModuleI18nMessage = Tuple[str, Dict[str, Any]]
SimpleModuleError = Union[str, ModuleI18nMessage]
ModuleErrorWithQuickFixes = Union[
    SimpleModuleError, Dict[str, Union[SimpleModuleError, List[Any]]]
]
ModuleErrorsWithQuickFixes = List[ModuleErrorWithQuickFixes]
# The dict must have keys `"message": SimpleModuleError` and `"quickFixes": List[Any]`. We can define it in python 3.8 using `TypedDict`s
ModuleErrorResult = Union[ModuleErrorWithQuickFixes, ModuleErrorsWithQuickFixes]
""" ModuleError is the type we expect from modules to return when there is an error.
When coercing to pandas types, we convert it to the simpler type `List[ProcessResultError]` held in `ProcessResult`.
"""
