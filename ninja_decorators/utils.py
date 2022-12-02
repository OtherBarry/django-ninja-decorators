import inspect
from typing import Any, Callable, Dict, Tuple, Type

from django.http import HttpRequest
from ninja import Schema
from ninja.errors import ConfigError
from ninja.params import Param


def get_request_argument_index(func: Callable) -> int:
    """Returns the index of the request argument in the function signature"""
    signature = inspect.signature(func)
    for index, (name, param) in enumerate(signature.parameters.items()):
        if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD and name == "request":
            return index
    raise ValueError(f"{func} is missing a request argument")


def get_request_argument_value(
    index: int, args: Tuple[Any], kwargs: Dict[str, Any]
) -> HttpRequest:
    """Returns the request argument value from the function arguments"""
    if "request" in kwargs:
        return kwargs["request"]
    if index < len(args):
        return args[index]
    raise ValueError("Request argument not found")


def get_request_argument(
    func: Callable, args: Tuple[Any], kwargs: Dict[str, Any]
) -> HttpRequest:
    """Returns the request argument from the function arguments"""
    index = get_request_argument_index(func)
    return get_request_argument_value(index, args, kwargs)


# TODO: Use built in ninja.signature.utils.inject_contribute_args when it's available  - see https://github.com/vitalik/django-ninja/pull/604
def inject_contribute_args(
    func: Callable[[Any], Any], p_name: str, p_type: Type[Schema], p_source: Param
) -> Callable[[Any], Any]:
    """Injects _ninja_contribute_args to the function"""

    contribution_args = (p_name, p_type, p_source)
    if hasattr(func, "_ninja_contribute_args"):
        if isinstance(func._ninja_contribute_args, list):  # type: ignore[attr-defined]
            func._ninja_contribute_args.append(contribution_args)  # type: ignore[attr-defined]
        else:
            raise ConfigError(f"{func} has an invalid _ninja_contribute_args value")
    else:
        func._ninja_contribute_args = [contribution_args]  # type: ignore[attr-defined]
    return func
