from functools import wraps
from typing import Any, Callable, Dict, Tuple, Type

from django.db.models import QuerySet
from ninja import Schema
from ninja.params import Param, Query
from pydantic import create_model

from ninja_decorators.utils import inject_contribute_args

# TODO: Implement filtering logic using a class, like ninja pagination


def filterable(
    # TODO: Determine which type hint to use for type hints
    filters: Dict[str, Tuple[str, Any]],
    param_type: Type[Param] = Query,
    schema_suffix: str = "filter",
) -> Callable[[Callable[[Any], QuerySet[Any]]], Callable[[Any], QuerySet[Any]]]:
    field_name = "ninja_filtering"

    definitions = {field: (type_, None) for field, (lookup, type_) in filters.items()}

    def wrapper(func: Callable[[Any], QuerySet[Any]]) -> Callable[[Any], QuerySet[Any]]:

        schema: Type[Schema] = create_model(
            f"{func.__name__}_{schema_suffix}",
            __config__=None,
            __base__=Schema,
            __module__=Schema.__module__,
            __validators__={},
            **definitions,
        )  # type: ignore

        @wraps(func)
        def view_with_filtering(*args: Tuple[Any], **kwargs: Any) -> Any:
            data = kwargs.pop(field_name)
            queryset_filters = {
                filters[field][0]: value
                for field, value in data.dict(
                    exclude_unset=True, exclude_none=True
                ).items()
            }
            return func(*args, **kwargs).filter(**queryset_filters)

        inject_contribute_args(view_with_filtering, field_name, schema, param_type(...))
        return view_with_filtering

    return wrapper
