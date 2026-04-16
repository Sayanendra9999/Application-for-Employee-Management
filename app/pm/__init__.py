"""Project Management blueprint."""

from flask import Blueprint

bp = Blueprint('pm', __name__, url_prefix='/pm')

from app.pm import routes  # noqa: E402, F401
