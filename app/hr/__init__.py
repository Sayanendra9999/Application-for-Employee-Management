"""HR blueprint — employee records, leaves, attendance."""

from flask import Blueprint

bp = Blueprint('hr', __name__, url_prefix='/hr')

from app.hr import routes  # noqa: E402, F401
