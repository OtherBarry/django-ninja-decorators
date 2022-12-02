from abc import ABC, abstractmethod
from collections.abc import Iterable
from functools import wraps
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, Union

from django.db.models import QuerySet
from django.utils.module_loading import import_string
from ninja import Schema
from ninja.params import Param, Query
from pydantic import Field, create_model, validator

from ninja_decorators.conf import settings
from ninja_decorators.utils import inject_contribute_args


class BaseSorter(ABC):
    DEFAULT_PARAMETER_NAME = "sort"
    DEFAULT_PARAMETER_TYPE = Query
    KEYWORD_ARGUMENT_NAME = "ninja_sorting"
    SCHEMA_NAME = "Input"
    SCHEMA_PROPERTY = "sort"
    UNIQUE_ITEMS = True

    def __init__(
        self,
        parameter_name: Optional[str] = None,
        parameter_type: Optional[Param] = None,
    ) -> None:
        self.parameter_name = (
            parameter_name
            if parameter_name is not None
            else self.DEFAULT_PARAMETER_NAME
        )
        self.parameter_type = (
            parameter_type
            if parameter_type is not None
            else self.DEFAULT_PARAMETER_TYPE
        )

    def generate_model(self, keys: Dict[str, str], default: List[str]) -> Type[Schema]:
        definitions = {
            self.SCHEMA_PROPERTY: (
                List[Literal[tuple(keys.keys())]],
                Field(
                    default, alias=self.parameter_name, unique_items=self.UNIQUE_ITEMS
                ),
            )
        }

        def _validator(cls, v):
            return self.validate_input(v, keys)

        validators = {
            f"{self.SCHEMA_PROPERTY}_validator": validator(
                self.SCHEMA_PROPERTY, allow_reuse=True
            )(_validator)
        }
        return create_model(*definitions, __validators__=validators)

    def validate_keys(self, keys: Dict[str, str]) -> Dict[str, str]:
        return keys

    def validate_input(self, sort_list: List[str], keys: Dict[str, str]) -> List[str]:
        return sort_list

    @abstractmethod
    def sort_queryset(self, queryset: QuerySet, sort_list: List[str]) -> QuerySet:
        pass


class ORMSorter(BaseSorter):
    DEFAULT_PARAMETER_NAME = "sort_by"

    def __init__(self, *args, reversible: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.reversible = reversible

    def validate_keys(self, keys: Dict[str, str]) -> Dict[str, str]:
        if self.reversible:
            keys.update({f"-{k}": f"-{v}" for k, v in keys.items()})
        return keys

    def sort_queryset(self, queryset: QuerySet, sort_list: List[str]) -> QuerySet:
        return queryset.order_by(*sort_list)


def sortable(
    keys: Union[Iterable[str], Dict[str, str]],
    default: Optional[Union[List[str], str]] = None,
    sorter_class: Optional[Type[BaseSorter]] = None,
    **kwargs: Any,
) -> Callable[[Callable[[Any], QuerySet[Any]]], Callable[[Any], QuerySet[Any]]]:
    if not isinstance(keys, dict):
        keys = {field: field for field in keys}
    if sorter_class is None:
        sorter_class: Type[BaseSorter] = import_string(settings.SORTER_CLASS)
    sorter = sorter_class(**kwargs)
    keys = sorter.validate_keys(keys)
    if default is None:
        default = []
    elif isinstance(default, str):
        default = [default]
    default = sorter.validate_input(default, keys)
    InputSchema = sorter.generate_model(keys, default)

    def wrapper(func: Callable[[Any], QuerySet[Any]]) -> Callable[[Any], QuerySet[Any]]:
        @wraps(func)
        def view_with_sorting(*args: Tuple[Any], **kwargs: Any) -> Any:
            data: InputSchema = kwargs.pop(sorter.KEYWORD_ARGUMENT_NAME)
            sort_list = [keys[field] for field in getattr(data, sorter.SCHEMA_PROPERTY)]
            queryset = func(*args, **kwargs)
            return sorter.sort_queryset(queryset, sort_list)

        inject_contribute_args(
            view_with_sorting,
            sorter.KEYWORD_ARGUMENT_NAME,
            InputSchema,
            sorter.parameter_type(default),
        )
        return view_with_sorting

    return wrapper
