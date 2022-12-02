from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type

from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.utils.module_loading import import_string
from ninja.errors import HttpError

from ninja_decorators.conf import settings
from ninja_decorators.utils import get_argument

User = get_user_model()


class BasePermission(ABC):
    def __init__(self, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def has_permissions(self, request: HttpRequest, permissions: Tuple[str]) -> bool:
        pass

    def handle_missing_permissions(
        self, request: HttpRequest, permissions: Tuple[str]
    ) -> Any:
        raise HttpError(
            status_code=403,
            message=f"User does not have sufficient permissions. Required permissions are {', '.join(permissions)}.",
        )

    def update_docstring(
        self, docstring: Optional[str], permissions: Tuple[str]
    ) -> Optional[str]:
        return docstring


class DjangoAuthPermissions(BasePermission):
    class AuthenticatedHttpRequest(HttpRequest):
        user: User

    def has_permissions(
        self, request: AuthenticatedHttpRequest, permissions: Tuple[str]
    ) -> bool:
        return request.user.has_perms(permissions)


def requires_permission(
    *permissions: str,
    permission_class: Optional[Type[BasePermission]] = None,
    **kwargs: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    if permission_class is None:
        permission_class: Type[BasePermission] = import_string(
            settings.PERMISSIONS_CLASS
        )
    permissions_handler = permission_class(**kwargs)

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        if len(permissions) == 0:
            return f  # Short circuit if no permissions are required.

        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            request: HttpRequest = get_argument("request", f, args, kwargs)
            if not permissions_handler.has_permissions(request, permissions):
                return permissions_handler.handle_missing_permissions(
                    request, permissions
                )
            return f(*args, **kwargs)

        permissions_handler.update_docstring(decorated_function.__doc__, permissions)
        return decorated_function

    return decorator
