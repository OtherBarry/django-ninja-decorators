from collections.abc import Iterable
from functools import wraps
from typing import Any, Callable, Literal, Optional, Union

from django.db.models import QuerySet
from ninja import Schema
from ninja.params import Param, Query
from pydantic import Field, validator

from ninja_decorators.utils import inject_contribute_args

# TODO: Implement sorting logic using a class, like ninja pagination


def sortable(
    order_by: Union[Iterable[str], dict[str, str]],
    param_name: str = "sort",
    param_type: type[Param] = Query,
    default: Optional[Union[list[str], str]] = None,
) -> Callable[[Callable[[Any], QuerySet[Any]]], Callable[[Any], QuerySet[Any]]]:
    if not isinstance(order_by, dict):
        order_by = {field: field for field in order_by}
    order_by.update(
        {f"-{field}": f"-{sort_field}" for field, sort_field in order_by.items()}
    )
    if default is None:
        default = []
    elif isinstance(default, str):
        default = [default]

    class Input(
        Schema
    ):  # TODO: Make dynamic with pydantic.create_model to avoid name conflicts
        sort: list[Literal[tuple(order_by.keys())]] = Field(  # type: ignore[misc]
            default, alias=param_name, unique_items=True
        )

        @validator("sort", allow_reuse=True)
        def validate_sort(cls, v: list[str]) -> list[str]:
            for field in v:
                if field.startswith("-") and field[1:] in v:
                    raise ValueError(
                        f"Cannot sort field '{field[1:]}' ascending and descending at the same time"
                    )
            return v

    field_name = "ninja_sorting"

    def wrapper(func: Callable[[Any], QuerySet[Any]]) -> Callable[[Any], QuerySet[Any]]:
        @wraps(func)
        def view_with_sorting(*args: tuple[Any], **kwargs: Any) -> Any:
            data: Input = kwargs.pop(field_name)
            sort_fields = [order_by[field] for field in data.sort]  # type: ignore[index]
            return func(*args, **kwargs).order_by(*sort_fields)

        inject_contribute_args(
            view_with_sorting, field_name, Input, param_type(default)
        )
        return view_with_sorting

    return wrapper
