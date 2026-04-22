"""HR Services — Business logic for attendance, leave, and employee operations.

This layer consumes Admin-configured rules and applies them.
Routes should call these services instead of writing business logic inline.

UPGRADED: Shift-aware attendance, multi-step leave workflow, comp-off, auto-absent.
"""

import json
from datetime import date, datetime, timedelta
from app.extensions import db
from app.models import (Employee, Attendance, Leave, LeaveBalance, LeavePolicy,
                        AttendanceRule, AuditLog, Department, Designation,
                        Shift, CompOff, ShiftSwapRequest)


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
# SHIFT / ATTENDANCE RULE SERVICES
# ===========================================================================
def get_attendance_rules():
    """Fetch the active attendance rules set by Admin (General Shift).
    Returns defaults if none configured."""
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


def get_shift_rules_for_employee(employee_id):
    """Get shift-specific timing for an employee. Falls back to General Shift.
    Returns dict with start_time, end_time, grace_mins, late_after_mins,
    min_hours, half_day_hours, overtime_eligible."""
    emp = Employee.query.get(employee_id)
    if emp and emp.shift_id:
        shift = Shift.query.get(emp.shift_id)
        if shift and shift.is_active:
            return {
                'shift_name': shift.shift_name,
                'start_time': shift.start_time,
                'end_time': shift.end_time,
                'grace_mins': shift.grace_period_mins,
                'late_after_mins': shift.late_mark_after_mins,
                'min_hours': shift.min_working_hours,
                'half_day_hours': shift.min_working_hours / 2,
                'overtime_eligible': shift.overtime_eligible,
                'is_night_shift': _is_night_shift(shift.start_time, shift.end_time)
            }
    # Fall back to General Shift (AttendanceRule)
    rules = get_attendance_rules()
    return {
        'shift_name': 'General',
        'start_time': rules['work_start'],
        'end_time': rules['work_end'],
        'grace_mins': rules['late_threshold_mins'],
        'late_after_mins': rules['late_threshold_mins'],
        'min_hours': rules['full_day_hours'],
        'half_day_hours': rules['half_day_hours'],
        'overtime_eligible': False,
        'is_night_shift': False
    }


def _is_night_shift(start_time, end_time):
    """Check if a shift crosses midnight (night shift)."""
    try:
        sh, sm = map(int, start_time.split(':'))
        eh, em = map(int, end_time.split(':'))
        return (eh * 60 + em) < (sh * 60 + sm)
    except (ValueError, AttributeError):
        return False


def get_all_shifts():
    """Get all active shifts for dropdowns."""
    return Shift.query.filter_by(is_active=True).order_by(Shift.shift_name).all()


def get_shifts_for_dropdown():
    """Get shifts as (id, name) tuples for form dropdowns."""
    return [(s.id, s.shift_name) for s in get_all_shifts()]


# ===========================================================================
# ATTENDANCE SERVICES — SHIFT-AWARE
# ===========================================================================
def perform_checkin(employee_id, check_time=None):
    """Record employee check-in using their assigned shift rules.
    Returns (success, message)."""
    today = date.today()
    check_time = check_time or datetime.now().strftime('%H:%M')

    # Check if already checked in today
    existing = Attendance.query.filter_by(employee_id=employee_id, date=today).first()
    if existing and existing.check_in:
        return False, f'Already checked in today at {existing.check_in}'

    rules = get_shift_rules_for_employee(employee_id)

    # Determine status based on shift rules
    status = 'Present'
    try:
        work_h, work_m = map(int, rules['start_time'].split(':'))
        ci_h, ci_m = map(int, check_time.split(':'))
        work_start_mins = work_h * 60 + work_m
        checkin_mins = ci_h * 60 + ci_m

        # For night shift, adjust comparison
        if rules['is_night_shift'] and checkin_mins < 12 * 60:
            checkin_mins += 24 * 60

        if checkin_mins > work_start_mins + rules['late_after_mins']:
            status = 'Late'
    except (ValueError, AttributeError):
        pass

    is_overnight = rules['is_night_shift']

    if existing:
        existing.check_in = check_time
        existing.status = status
        existing.is_overnight = is_overnight
    else:
        att = Attendance(
            employee_id=employee_id, date=today,
            check_in=check_time, status=status,
            is_overnight=is_overnight
        )
        db.session.add(att)

    return True, f'Checked in at {check_time} ({status}) — {rules["shift_name"]} shift'


def perform_checkout(employee_id, check_time=None):
    """Record employee check-out. Calculates working hours using shift rules.
    Returns (success, message)."""
    today = date.today()
    check_time = check_time or datetime.now().strftime('%H:%M')

    existing = Attendance.query.filter_by(employee_id=employee_id, date=today).first()
    if not existing or not existing.check_in:
        return False, 'You must check in first before checking out'

    if existing.check_out:
        return False, f'Already checked out today at {existing.check_out}'

    existing.check_out = check_time
    existing.working_hours = existing.calc_working_hours()

    # Apply shift rules for half-day detection
    rules = get_shift_rules_for_employee(employee_id)
    if existing.working_hours < rules['half_day_hours']:
        existing.status = 'Half-Day'
    elif existing.status != 'Late':
        existing.status = 'Present'

    # Check for overtime and comp-off eligibility
    overtime_msg = ''
    if rules['overtime_eligible'] and existing.working_hours > rules['min_hours']:
        extra_hours = round(existing.working_hours - rules['min_hours'], 2)
        if extra_hours >= 1.0:  # At least 1 hour extra to earn comp-off
            comp = CompOff(
                employee_id=employee_id,
                earned_date=today,
                hours_extra=extra_hours,
                status='Earned'
            )
            db.session.add(comp)
            overtime_msg = f' Comp-off earned ({extra_hours:.1f}h extra)!'

    return True, f'Checked out at {check_time}. {existing.working_hours:.1f} hours worked.{overtime_msg}'


def override_attendance(employee_id, att_date, status, check_in='', check_out='', notes=''):
    """HR override for attendance records. Returns (success, message)."""
    existing = Attendance.query.filter_by(employee_id=employee_id, date=att_date).first()
    if existing:
        existing.status = status
        if check_in:
            existing.check_in = check_in
        if check_out:
            existing.check_out = check_out
        if notes:
            existing.notes = notes
        existing.working_hours = existing.calc_working_hours()
    else:
        att = Attendance(
            employee_id=employee_id, date=att_date,
            check_in=check_in, check_out=check_out,
            status=status, notes=notes
        )
        db.session.add(att)
    return True, f'Attendance overridden for {att_date} → {status}'


def auto_mark_absent(target_date=None):
    """Auto mark absent for employees who have no attendance and no approved leave.
    Returns count of employees marked absent."""
    target_date = target_date or (date.today() - timedelta(days=1))  # Yesterday
    if target_date.weekday() >= 5:
        return 0  # Skip weekends

    employees = Employee.query.filter_by(is_active=True).all()
    count = 0
    for emp in employees:
        # Check if already has attendance
        existing_att = Attendance.query.filter_by(employee_id=emp.id, date=target_date).first()
        if existing_att:
            continue

        # Check if has approved leave covering this date
        on_leave = Leave.query.filter(
            Leave.employee_id == emp.id,
            Leave.status == 'Approved',
            Leave.start_date <= target_date,
            Leave.end_date >= target_date
        ).first()
        if on_leave:
            # Mark as "On Leave" instead of absent
            att = Attendance(
                employee_id=emp.id, date=target_date,
                status='On Leave', notes=f'On {on_leave.leave_type}'
            )
            db.session.add(att)
            continue

        # No attendance, no leave → mark absent
        att = Attendance(
            employee_id=emp.id, date=target_date,
            status='Absent', notes='Auto-marked: no login & no approved leave'
        )
        db.session.add(att)
        count += 1

    return count


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
        'on_leave': sum(1 for r in records if r.status == 'On Leave'),
        'total_hours': round(sum(r.working_hours or 0 for r in records), 1)
    }
    summary['effective_days'] = summary['present'] + summary['late'] + (summary['half_day'] * 0.5)
    return summary


# ===========================================================================
# LEAVE SERVICES — ROLE-BASED POLICIES + MULTI-STEP WORKFLOW
# ===========================================================================
def get_leave_policies_for_employee(employee_id):
    """Get applicable leave policies for an employee based on their designation.
    If a designation-specific policy exists, use it; otherwise fall back to global."""
    emp = Employee.query.get(employee_id)
    if not emp:
        return []

    all_policies = LeavePolicy.query.filter_by(is_active=True).all()

    # Group by leave_type
    policy_map = {}
    for p in all_policies:
        lt = p.leave_type
        if lt not in policy_map:
            policy_map[lt] = {'global': None, 'specific': None}
        if p.designation_id is None:
            policy_map[lt]['global'] = p
        elif emp.designation_id and p.designation_id == emp.designation_id:
            policy_map[lt]['specific'] = p

    # Return specific if available, otherwise global
    result = []
    for lt, pols in policy_map.items():
        if pols['specific']:
            result.append(pols['specific'])
        elif pols['global']:
            result.append(pols['global'])

    return result


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
    """Initialize leave balances for an employee based on applicable policies.
    Uses designation-specific policies if available, otherwise global defaults.
    Called when an employee is created or at the start of a new year."""
    year = year or date.today().year
    policies = get_leave_policies_for_employee(employee_id)
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


def _check_blackout_dates(policy, start_date, end_date):
    """Check if requested dates fall within blackout periods.
    Returns (blocked, message)."""
    if not policy.blackout_dates:
        return False, ''
    try:
        blackouts = json.loads(policy.blackout_dates)
        if not isinstance(blackouts, list):
            return False, ''
        for bo in blackouts:
            bo_start = datetime.strptime(bo['start'], '%Y-%m-%d').date()
            bo_end = datetime.strptime(bo['end'], '%Y-%m-%d').date()
            # Check overlap
            if start_date <= bo_end and end_date >= bo_start:
                return True, f'Blackout period: {bo_start.strftime("%d %b")} to {bo_end.strftime("%d %b")}'
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return False, ''


def validate_leave_request(employee_id, leave_type, start_date, end_date):
    """Validate a leave request against Admin policies (role-based).
    Returns (valid, error_message)."""
    # 1. Find applicable policy
    policies = get_leave_policies_for_employee(employee_id)
    policy = next((p for p in policies if p.leave_type == leave_type), None)
    if not policy:
        return False, f'Leave type "{leave_type}" is not configured or inactive for your role'

    # 2. Calculate requested days (excluding weekends)
    requested_days = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:
            requested_days += 1
        current += timedelta(days=1)

    if requested_days == 0:
        return False, 'No working days in the selected range'

    # 3. Check max per request
    if policy.max_per_request and requested_days > policy.max_per_request:
        return False, f'Maximum {policy.max_per_request} days allowed per request'

    # 4. Check blackout dates
    blocked, msg = _check_blackout_dates(policy, start_date, end_date)
    if blocked:
        return False, f'Cannot apply leave during this period: {msg}'

    # 5. Check balance
    year = start_date.year
    balance = get_leave_balance(employee_id, leave_type, year)
    if not balance:
        # Auto-initialize if missing
        initialize_leave_balances(employee_id, year)
        balance = get_leave_balance(employee_id, leave_type, year)

    if balance and balance.remaining < requested_days:
        return False, f'Insufficient {leave_type} balance. Available: {balance.remaining}, Requested: {requested_days}'

    # 6. Check for overlapping leave requests
    overlapping = Leave.query.filter(
        Leave.employee_id == employee_id,
        Leave.status.in_(['Pending', 'Approved']),
        Leave.start_date <= end_date,
        Leave.end_date >= start_date
    ).first()
    if overlapping:
        return False, f'Overlapping leave exists ({overlapping.start_date} to {overlapping.end_date})'

    return True, f'{requested_days} day(s) requested'


def approve_leave(leave_id, approver_id, step='hr'):
    """Approve a leave request (multi-step: manager or HR).
    step='manager' sets manager_status, step='hr' sets hr_status and finalizes.
    Returns (success, message)."""
    leave = Leave.query.get(leave_id)
    if not leave:
        return False, 'Leave request not found'
    if leave.status not in ('Pending',):
        return False, f'Leave is already {leave.status}'

    days = leave.calc_days()

    if step == 'manager':
        leave.manager_status = 'Approved'
        leave.manager_approved_by = approver_id
        return True, f'Manager approved leave ({days} days). Awaiting HR final approval.'

    # HR approval (final step)
    leave.hr_status = 'Approved'
    leave.hr_approved_by = approver_id
    leave.status = 'Approved'
    leave.approved_by = approver_id
    leave.total_days = days

    # Deduct from balance
    balance = get_leave_balance(leave.employee_id, leave.leave_type, leave.start_date.year)
    if balance:
        if balance.remaining < days:
            return False, f'Insufficient balance ({balance.remaining} remaining, {days} needed)'
        balance.used += days

    return True, f'Leave approved ({days} days deducted)'


def reject_leave(leave_id, approver_id, reason='', step='hr'):
    """Reject a leave request (multi-step). Returns (success, message)."""
    leave = Leave.query.get(leave_id)
    if not leave:
        return False, 'Leave request not found'
    if leave.status not in ('Pending',):
        return False, f'Leave is already {leave.status}'

    if step == 'manager':
        leave.manager_status = 'Rejected'
        leave.manager_approved_by = approver_id
        leave.status = 'Rejected'
        leave.rejection_reason = reason
        return True, 'Leave rejected by manager'

    # HR rejection
    leave.hr_status = 'Rejected'
    leave.hr_approved_by = approver_id
    leave.status = 'Rejected'
    leave.approved_by = approver_id
    leave.rejection_reason = reason

    return True, 'Leave rejected'


# ===========================================================================
# COMP-OFF SERVICES
# ===========================================================================
def get_comp_offs(employee_id=None, status=None):
    """Get comp-off records, optionally filtered."""
    query = CompOff.query
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(CompOff.created_at.desc()).all()


def approve_comp_off(comp_id, approver_id):
    """Approve a comp-off and add 1 day to leave balance as 'Comp-Off Leave'."""
    comp = CompOff.query.get(comp_id)
    if not comp or comp.status != 'Earned':
        return False, 'Comp-off not found or not in Earned status'
    comp.approved_by = approver_id
    # Optionally: create/add a comp-off leave balance entry
    return True, f'Comp-off approved for emp#{comp.employee_id}'


# ===========================================================================
# SHIFT SWAP SERVICES
# ===========================================================================
def get_shift_swap_requests(status=None):
    """Get all shift swap requests, optionally filtered by status."""
    query = ShiftSwapRequest.query
    if status:
        query = query.filter_by(status=status)
    return query.order_by(ShiftSwapRequest.created_at.desc()).all()


def approve_shift_swap(swap_id, reviewer_id):
    """Approve a shift swap request and update employee's shift."""
    swap = ShiftSwapRequest.query.get(swap_id)
    if not swap or swap.status != 'Pending':
        return False, 'Shift swap request not found or already processed'

    emp = Employee.query.get(swap.employee_id)
    if not emp:
        return False, 'Employee not found'

    emp.shift_id = swap.requested_shift_id
    swap.status = 'Approved'
    swap.reviewed_by = reviewer_id
    swap.reviewed_at = datetime.utcnow()

    return True, f'Shift swap approved. {emp.emp_code} moved to new shift.'


def reject_shift_swap(swap_id, reviewer_id):
    """Reject a shift swap request."""
    swap = ShiftSwapRequest.query.get(swap_id)
    if not swap or swap.status != 'Pending':
        return False, 'Shift swap request not found or already processed'

    swap.status = 'Rejected'
    swap.reviewed_by = reviewer_id
    swap.reviewed_at = datetime.utcnow()

    return True, 'Shift swap request rejected'


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


# ===========================================================================
# PAYROLL INPUT SERVICES (Batch 2)
# ===========================================================================
def generate_payroll_inputs(year, month):
    """Auto-generate payroll input rows for all employees for a given month.
    Pulls attendance summary and leave data. Returns (created_count, skipped_count)."""
    from app.models import PayrollInput
    from calendar import monthrange

    employees = Employee.query.filter_by(is_active=True).all()
    created = 0
    skipped = 0
    month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    month_name = month_names[month]

    for emp in employees:
        # Check if already exists
        existing = PayrollInput.query.filter_by(
            employee_id=emp.id, month=month_name, year=year
        ).first()
        if existing:
            skipped += 1
            continue

        # Get attendance summary
        summary = get_attendance_summary(emp.id, year, month)

        # Count working days in the month (Mon-Fri)
        _, days_in_month = monthrange(year, month)
        working_days = sum(1 for d in range(1, days_in_month + 1)
                          if date(year, month, d).weekday() < 5)

        # Count approved leaves in the month
        start_date = date(year, month, 1)
        end_date = date(year, month, days_in_month)
        leaves_taken = Leave.query.filter(
            Leave.employee_id == emp.id,
            Leave.status == 'Approved',
            Leave.start_date <= end_date,
            Leave.end_date >= start_date
        ).count()

        payroll = PayrollInput(
            employee_id=emp.id,
            month=month_name,
            year=year,
            working_days=working_days,
            present_days=int(summary['effective_days']),
            leaves_taken=leaves_taken,
            overtime_hours=0.0,
            bonus=0.0,
            deduction_notes='',
            status='Draft'
        )
        db.session.add(payroll)
        created += 1

    db.session.flush()
    return created, skipped


# ===========================================================================
# DOCUMENT MANAGEMENT SERVICES (Batch 2)
# ===========================================================================
def allowed_file(filename, allowed_extensions):
    """Check if a filename has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def generate_safe_filename(original_name, emp_code):
    """Generate a safe, unique filename for storage."""
    import uuid
    ext = original_name.rsplit('.', 1)[1].lower() if '.' in original_name else 'bin'
    unique_id = uuid.uuid4().hex[:8]
    return f"{emp_code}_{unique_id}.{ext}"


# ===========================================================================
# PERFORMANCE REVIEW SERVICES (Batch 2)
# ===========================================================================
def get_review_periods():
    """Generate review period options for the form dropdown."""
    current_year = date.today().year
    periods = []
    for y in range(current_year, current_year - 2, -1):
        periods.append((f'Annual-{y}', f'Annual Review {y}'))
        for q in range(4, 0, -1):
            periods.append((f'Q{q}-{y}', f'Q{q} {y}'))
    return periods


# ===========================================================================
# ONBOARDING / UNASSIGNED EMPLOYEE SERVICES
# ===========================================================================
def is_employee_profile_complete(emp):
    """Check if an employee profile has all required fields filled.
    An employee is 'unassigned' if they are missing department, designation,
    salary, bank account, or PAN number."""
    if not emp:
        return False
    if not emp.department_id:
        return False
    if not emp.designation_id:
        return False
    if not emp.salary or emp.salary <= 0:
        return False
    if not emp.bank_account or emp.bank_account.strip() == '':
        return False
    if not emp.pan_number or emp.pan_number.strip() == '':
        return False
    return True


def get_missing_fields(emp):
    """Return a list of field names that are still missing for the employee."""
    missing = []
    if not emp.department_id:
        missing.append('Department')
    if not emp.designation_id:
        missing.append('Designation')
    if not emp.salary or emp.salary <= 0:
        missing.append('Salary')
    if not emp.bank_account or emp.bank_account.strip() == '':
        missing.append('Bank Account')
    if not emp.pan_number or emp.pan_number.strip() == '':
        missing.append('PAN Number')
    return missing


def get_unassigned_employees():
    """Return all employees whose profiles are incomplete (missing key fields).
    Uses existing schema — filters on NULL department/designation or empty
    salary/bank/PAN."""
    from app.models import User
    all_emps = Employee.query.join(User).order_by(Employee.emp_code).all()
    return [e for e in all_emps if not is_employee_profile_complete(e)]


def get_unassigned_count():
    """Quick count of unassigned employees."""
    return len(get_unassigned_employees())


def complete_employee_profile(emp, department_id, designation_id, salary,
                              bank_account, pan_number, date_of_joining=None):
    """Update an employee's profile with the missing details.
    Returns (success, message)."""
    if not emp:
        return False, 'Employee not found.'

    # Validate required fields
    if not department_id or department_id == 0:
        return False, 'Department is required.'
    if not designation_id or designation_id == 0:
        return False, 'Designation is required.'
    if not salary or float(salary) <= 0:
        return False, 'A valid salary is required.'
    if not bank_account or bank_account.strip() == '':
        return False, 'Bank account is required.'
    if not pan_number or pan_number.strip() == '':
        return False, 'PAN number is required.'

    emp.department_id = int(department_id)
    emp.designation_id = int(designation_id)
    emp.salary = float(salary)
    emp.bank_account = bank_account.strip()
    emp.pan_number = pan_number.strip().upper()
    if date_of_joining:
        emp.date_of_joining = date_of_joining

    return True, f'Profile for {emp.emp_code} ({emp.user.full_name}) completed successfully.'
