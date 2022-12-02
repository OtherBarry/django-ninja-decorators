from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple, Type

from django.db.models import QuerySet
from django.utils.module_loading import import_string
from ninja import Schema
from ninja.params import Param, Query
from pydantic import create_model

from ninja_decorators.conf import settings
from ninja_decorators.utils import inject_contribute_args

TypeType = Any  # TODO: Determine which type hint to use for type hints

# TODO: Allow default values to be set in the filters dict


class BaseFilter(ABC):
    SCHEMA_SUFFIX = "filters"
    DEFAULT_PARAMETER_TYPE = Query
    KEYWORD_ARGUMENT_NAME = "ninja_filtering"

    def __init__(
        self, *args: Any, parameter_type: Optional[Param] = None, **kwargs: Any
    ) -> None:
        self.parameter_type = (
            parameter_type
            if parameter_type is not None
            else self.DEFAULT_PARAMETER_TYPE
        )

    @abstractmethod
    def filter_queryset(
        self, queryset: QuerySet, filter_values: Dict[str, Any]
    ) -> QuerySet:
        pass

    def generate_model(
        self, filters: Dict[str, Tuple[str, TypeType]], function_name: str
    ) -> Type[Schema]:
        definitions = {key: (type_, None) for key, (_, type_) in filters.items()}
        return create_model(
            f"{function_name}_{self.SCHEMA_SUFFIX}",
            __config__=None,
            __base__=Schema,
            __module__=Schema.__module__,
            __validators__={},
            **definitions,
        )

    def parse_model(
        self, data: Schema, filters: Dict[str, Tuple[str, TypeType]]
    ) -> Dict[str, Any]:
        raw_data = data.dict(exclude_unset=True)
        return {filters[k][0]: v for k, v in raw_data.items()}


class ORMFilter(BaseFilter):
    def filter_queryset(self, queryset: QuerySet, filters: Dict[str, Any]) -> QuerySet:
        return queryset.filter(**filters)


def filterable(
    filters: Dict[str, Tuple[str, Any]],
    filter_class: Optional[Type[BaseFilter]] = None,
    **kwargs: Any,
) -> Callable[[Callable[[Any], QuerySet[Any]]], Callable[[Any], QuerySet[Any]]]:

    if filter_class is None:
        filter_class = import_string(settings.FILTER_CLASS)
    filter_ = filter_class(**kwargs)

    def wrapper(func: Callable[[Any], QuerySet[Any]]) -> Callable[[Any], QuerySet[Any]]:
        schema = filter_.generate_model(filters, func.__name__)

        @wraps(func)
        def view_with_filtering(*args: Any, **kwargs: Any) -> Any:
            data = kwargs.pop(filter_.KEYWORD_ARGUMENT_NAME)
            queryset = func(*args, **kwargs)
            filter_data = filter_.parse_model(data, filters)
            return filter_.filter_queryset(queryset, filter_data)

        inject_contribute_args(
            view_with_filtering,
            filter_.KEYWORD_ARGUMENT_NAME,
            schema,
            filter_.parameter_type(...),
        )
        return view_with_filtering

    return wrapper
