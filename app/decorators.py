"""Custom decorators for authentication and authorization."""

from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user, login_required  # noqa: F401 – re-exported


def admin_required(f):
    """Restrict access to admin users only."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def module_required(module_slug):
    """Restrict access to users who have been granted the specified module.

    Admin users bypass this check (they have access to everything).
    Usage:
        @module_required('hr')
        def hr_dashboard():
            ...
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.is_admin:
                return f(*args, **kwargs)
            if not current_user.has_module(module_slug):
                flash('You do not have access to this module.', 'danger')
                return redirect(url_for('main_dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
