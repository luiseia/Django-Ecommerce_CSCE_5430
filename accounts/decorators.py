"""
Decorators for role-based access control.

Usage in views::

    @login_required
    @merchant_required
    def merchant_dashboard(request):
        ...
"""

from functools import wraps

from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """Generic decorator — pass one or more ``User.Role`` values."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def shopper_required(view_func):
    return role_required("SHOPPER")(view_func)


def merchant_required(view_func):
    return role_required("MERCHANT")(view_func)


def administrator_required(view_func):
    return role_required("ADMIN")(view_func)
