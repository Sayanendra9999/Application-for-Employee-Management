"""Employee module utilities — logging, notifications, audit helpers."""

import logging
from flask import abort
from flask_login import current_user
from app.extensions import db
from app.models import Notification, AuditLog


# ── Module Logger ────────────────────────────────────────────────────────
logger = logging.getLogger('employee')
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '[%(asctime)s] EMPLOYEE %(levelname)s — %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(handler)


def get_current_employee_or_abort():
    """Get the current user's employee profile or abort with 404."""
    employee = current_user.employee
    if not employee:
        logger.warning(f'User {current_user.username} has no employee profile')
        abort(404, description='Employee profile not found. Contact HR.')
    return employee


def create_notification(user_id, title, message, category='info', link=''):
    """Create a notification record for a user."""
    try:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            link=link
        )
        db.session.add(notif)
        logger.info(f'Notification created for user#{user_id}: {title}')
    except Exception as e:
        logger.error(f'Failed to create notification: {e}')


def log_employee_action(action, entity_type, entity_id=None, details='', ip=''):
    """Write an audit log entry for an employee action."""
    try:
        log = AuditLog(
            user_id=current_user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip
        )
        db.session.add(log)
        logger.info(f'Audit: {action} {entity_type}#{entity_id} by {current_user.username}')
    except Exception as e:
        logger.error(f'Failed to log audit: {e}')
