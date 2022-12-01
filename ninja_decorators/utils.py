from typing import Any, Callable, Type

from ninja import Schema
from ninja.errors import ConfigError
from ninja.params import Param


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