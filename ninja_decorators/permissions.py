from functools import wraps
from inspect import getfullargspec
from typing import Any, Callable

from django.contrib.auth import get_user_model
from django.http import HttpRequest
from ninja.errors import HttpError

User = get_user_model()


# TODO: Implement permissions logic using a class, like ninja pagination


class AuthenticatedHttpRequest(HttpRequest):
    user: User


def requires_permission(
    *permissions: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        if len(permissions) == 0:
            return f  # Short circuit if no permissions are required.

        try:
            request_index = getfullargspec(f).args.index("request")
        except ValueError:
            request_index = 0  # TODO: Find more reliable solution.

        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            try:
                request: AuthenticatedHttpRequest = args[request_index]
            except IndexError:
                request = kwargs["request"]
            if not request.user.has_perms(permissions):
                raise HttpError(
                    status_code=403,
                    message=f"User does not have sufficient permissions. Required permissions are {', '.join(permissions)}.",
                )
            return f(*args, **kwargs)

        if decorated_function.__doc__ is not None:
            decorated_function.__doc__ += (
                f"\nRequires permissions `{', '.join(permissions)}`."
            )

        return decorated_function

    return decorator
