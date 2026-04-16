"""HR Services — Business logic for attendance, leave, and employee operations.

This layer consumes Admin-configured rules and applies them.
Routes should call these services instead of writing business logic inline.
"""

from datetime import date, datetime, timedelta
from app.extensions import db
from app.models import (Employee, Attendance, Leave, LeaveBalance, LeavePolicy,
                        AttendanceRule, AuditLog, Department, Designation)


# ===========================================================================
# AUDIT
# ===========================================================================
def log_audit(user_id, action, entity_type, entity_id=None, details='', ip=''):
    """Write an audit log entry."""
    log = AuditLog(
        user_id=user_id, action=action, entity_type=entity_type,
        entity_id=entity_id, details=details, ip_address=ip
    )
    db.session.add(log)


# ===========================================================================
# ATTENDANCE SERVICES
# ===========================================================================
def get_attendance_rules():
    """Fetch the active attendance rules set by Admin. Returns defaults if none configured."""
    rule = AttendanceRule.query.filter_by(is_active=True).first()
    if not rule:
        return {
            'work_start': '09:00', 'work_end': '18:00',
            'late_threshold_mins': 15, 'half_day_hours': 4.0, 'full_day_hours': 8.0
        }
    return {
        'work_start': rule.work_start, 'work_end': rule.work_end,
        'late_threshold_mins': rule.late_threshold_mins,
        'half_day_hours': rule.half_day_hours, 'full_day_hours': rule.full_day_hours
    }


def perform_checkin(employee_id, check_time=None):
    """Record employee check-in. Returns (success, message)."""
    today = date.today()
    check_time = check_time or datetime.now().strftime('%H:%M')

    # Check if already checked in today
    existing = Attendance.query.filter_by(employee_id=employee_id, date=today).first()
    if existing and existing.check_in:
        return False, f'Already checked in today at {existing.check_in}'

    rules = get_attendance_rules()

    # Determine status based on Admin rules
    status = 'Present'
    try:
        work_h, work_m = map(int, rules['work_start'].split(':'))
        ci_h, ci_m = map(int, check_time.split(':'))
        work_start_mins = work_h * 60 + work_m
        checkin_mins = ci_h * 60 + ci_m
        if checkin_mins > work_start_mins + rules['late_threshold_mins']:
            status = 'Late'
    except (ValueError, AttributeError):
        pass

    if existing:
        existing.check_in = check_time
        existing.status = status
    else:
        att = Attendance(
            employee_id=employee_id, date=today,
            check_in=check_time, status=status
        )
        db.session.add(att)

    return True, f'Checked in at {check_time} ({status})'


def perform_checkout(employee_id, check_time=None):
    """Record employee check-out. Calculates working hours. Returns (success, message)."""
    today = date.today()
    check_time = check_time or datetime.now().strftime('%H:%M')

    existing = Attendance.query.filter_by(employee_id=employee_id, date=today).first()
    if not existing or not existing.check_in:
        return False, 'You must check in first before checking out'

    if existing.check_out:
        return False, f'Already checked out today at {existing.check_out}'

    existing.check_out = check_time
    existing.working_hours = existing.calc_working_hours()

    # Apply Admin rules for half-day detection
    rules = get_attendance_rules()
    if existing.working_hours < rules['half_day_hours']:
        existing.status = 'Half-Day'
    elif existing.status != 'Late':
        existing.status = 'Present'

    return True, f'Checked out at {check_time}. {existing.working_hours:.1f} hours worked.'


def get_monthly_attendance(employee_id, year, month):
    """Get attendance records for a specific month."""
    from calendar import monthrange
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    return Attendance.query.filter(
        Attendance.employee_id == employee_id,
        Attendance.date >= start,
        Attendance.date <= end
    ).order_by(Attendance.date).all()


def get_attendance_summary(employee_id, year, month):
    """Compute attendance summary for payroll input."""
    records = get_monthly_attendance(employee_id, year, month)
    summary = {
        'total_records': len(records),
        'present': sum(1 for r in records if r.status == 'Present'),
        'late': sum(1 for r in records if r.status == 'Late'),
        'absent': sum(1 for r in records if r.status == 'Absent'),
        'half_day': sum(1 for r in records if r.status == 'Half-Day'),
        'total_hours': round(sum(r.working_hours or 0 for r in records), 1)
    }
    summary['effective_days'] = summary['present'] + summary['late'] + (summary['half_day'] * 0.5)
    return summary


# ===========================================================================
# LEAVE SERVICES
# ===========================================================================
def get_leave_balance(employee_id, leave_type, year=None):
    """Get leave balance for an employee. Returns LeaveBalance object or None."""
    year = year or date.today().year
    return LeaveBalance.query.filter_by(
        employee_id=employee_id, leave_type=leave_type, year=year
    ).first()


def get_all_leave_balances(employee_id, year=None):
    """Get all leave balances for an employee for a year."""
    year = year or date.today().year
    return LeaveBalance.query.filter_by(
        employee_id=employee_id, year=year
    ).all()


def initialize_leave_balances(employee_id, year=None):
    """Initialize leave balances for an employee based on Admin-defined policies.
    Called when an employee is created or at the start of a new year."""
    year = year or date.today().year
    policies = LeavePolicy.query.filter_by(is_active=True).all()
    for policy in policies:
        existing = LeaveBalance.query.filter_by(
            employee_id=employee_id, leave_type=policy.leave_type, year=year
        ).first()
        if not existing:
            balance = LeaveBalance(
                employee_id=employee_id, leave_type=policy.leave_type,
                total_allocated=policy.total_days, used=0, year=year
            )
            db.session.add(balance)
    db.session.flush()


def validate_leave_request(employee_id, leave_type, start_date, end_date):
    """Validate a leave request against Admin policies.
    Returns (valid, error_message)."""
    # 1. Check policy exists and is active
    policy = LeavePolicy.query.filter_by(leave_type=leave_type, is_active=True).first()
    if not policy:
        return False, f'Leave type "{leave_type}" is not configured or inactive'

    # 2. Calculate requested days (excluding weekends)
    requested_days = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:
            requested_days += 1
        current += timedelta(days=1)

    if requested_days == 0:
        return False, 'No working days in the selected range'

    # 3. Check balance
    year = start_date.year
    balance = get_leave_balance(employee_id, leave_type, year)
    if not balance:
        # Auto-initialize if missing
        initialize_leave_balances(employee_id, year)
        balance = get_leave_balance(employee_id, leave_type, year)

    if balance and balance.remaining < requested_days:
        return False, f'Insufficient {leave_type} balance. Available: {balance.remaining}, Requested: {requested_days}'

    # 4. Check for overlapping leave requests
    overlapping = Leave.query.filter(
        Leave.employee_id == employee_id,
        Leave.status.in_(['Pending', 'Approved']),
        Leave.start_date <= end_date,
        Leave.end_date >= start_date
    ).first()
    if overlapping:
        return False, f'Overlapping leave exists ({overlapping.start_date} to {overlapping.end_date})'

    return True, f'{requested_days} day(s) requested'


def approve_leave(leave_id, approver_id):
    """Approve a leave request and deduct balance. Returns (success, message)."""
    leave = Leave.query.get(leave_id)
    if not leave:
        return False, 'Leave request not found'
    if leave.status != 'Pending':
        return False, f'Leave is already {leave.status}'

    # Calculate days
    days = leave.calc_days()

    # Deduct from balance
    balance = get_leave_balance(leave.employee_id, leave.leave_type, leave.start_date.year)
    if balance:
        if balance.remaining < days:
            return False, f'Insufficient balance ({balance.remaining} remaining, {days} needed)'
        balance.used += days

    leave.status = 'Approved'
    leave.approved_by = approver_id
    leave.total_days = days

    return True, f'Leave approved ({days} days deducted)'


def reject_leave(leave_id, approver_id, reason=''):
    """Reject a leave request. Returns (success, message)."""
    leave = Leave.query.get(leave_id)
    if not leave:
        return False, 'Leave request not found'
    if leave.status != 'Pending':
        return False, f'Leave is already {leave.status}'

    leave.status = 'Rejected'
    leave.approved_by = approver_id
    leave.rejection_reason = reason

    return True, 'Leave rejected'


# ===========================================================================
# EMPLOYEE SERVICES
# ===========================================================================
def get_departments_for_dropdown():
    """Get active departments for form dropdowns."""
    return [(d.id, d.name) for d in Department.query.filter_by(is_active=True).order_by(Department.name)]


def get_designations_for_dropdown(department_id=None):
    """Get active designations for form dropdowns, optionally filtered by department."""
    query = Designation.query.filter_by(is_active=True)
    if department_id:
        query = query.filter_by(department_id=department_id)
    return [(d.id, f'{d.title}') for d in query.order_by(Designation.title)]


def get_designations_for_department(department_id):
    """API helper: return designation list for a department (for dynamic dropdown)."""
    desigs = Designation.query.filter_by(
        department_id=department_id, is_active=True
    ).order_by(Designation.title).all()
    return [{'id': d.id, 'title': d.title, 'level': d.level} for d in desigs]
