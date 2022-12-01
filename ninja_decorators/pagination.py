import inspect
from functools import partial, wraps
from typing import Any, Callable, Tuple, Type

from django.utils.module_loading import import_string
from ninja.conf import settings
from ninja.constants import NOT_SET
from ninja.pagination import PaginationBase, make_response_paginated
from ninja.types import DictStrAny

from ninja_decorators.utils import inject_contribute_args


# TODO: Use built in ninja.pagination.paginate when inject_contribute_args is available - see https://github.com/vitalik/django-ninja/pull/604
def paginate(
    func_or_pgn_class: Any = NOT_SET, **paginator_params: DictStrAny
) -> Callable[[Any], Any]:
    """
    @api.get(...
    @paginage
    def my_view(request):

    or

    @api.get(...
    @paginage(PageNumberPagination)
    def my_view(request):

    """
    isfunction = inspect.isfunction(func_or_pgn_class)
    isnotset = func_or_pgn_class == NOT_SET
    pagination_class: Type[PaginationBase] = import_string(settings.PAGINATION_CLASS)
    if isfunction:
        return _inject_pagination(func_or_pgn_class, pagination_class)
    if not isnotset:
        pagination_class = func_or_pgn_class

    def wrapper(func: Callable[[Any], Any]) -> Any:
        return _inject_pagination(func, pagination_class, **paginator_params)

    return wrapper


# TODO: Delete when above function is removed
def _inject_pagination(
    func: Callable[[Any], Any],
    paginator_class: Type[PaginationBase],
    **paginator_params: Any,
) -> Callable[[Any], Any]:
    paginator: PaginationBase = paginator_class(**paginator_params)

    @wraps(func)
    def view_with_pagination(*args: Tuple[Any], **kwargs: DictStrAny) -> Any:
        pagination_params = kwargs.pop("ninja_pagination")
        if paginator.pass_parameter:
            kwargs[paginator.pass_parameter] = pagination_params
        items = func(*args, **kwargs)
        result = paginator.paginate_queryset(
            items, pagination=pagination_params, **kwargs
        )
        if paginator.Output:
            result[paginator.items_attribute] = list(result[paginator.items_attribute])
        return result

    inject_contribute_args(
        view_with_pagination, "ninja_pagination", paginator.Input, paginator.InputSource
    )
    if paginator.Output:
        view_with_pagination._ninja_contribute_to_operation = partial(  # type: ignore
            make_response_paginated, paginator
        )
    return view_with_pagination
