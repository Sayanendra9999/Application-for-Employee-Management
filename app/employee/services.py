"""Employee Services — Self-service business logic layer.

This module provides all business logic for the employee self-service portal.
It consumes data from HR, Finance, and Admin modules but never modifies their
core configuration. All operations are scoped to the current employee.
"""

import os
import uuid
from datetime import date, datetime
from flask import current_app
from app.extensions import db
from app.models import (Employee, Attendance, Leave, LeaveBalance, LeavePolicy,
                        SalaryRecord, EmployeeDocument, PerformanceReview,
                        Notification, Project, ProjectMember, Task,
                        ProfileUpdateRequest, EmployeeExpense,
                        Shift, CompOff, ShiftSwapRequest)
from app.employee.utils import logger, create_notification, log_employee_action


# ===========================================================================
# PROFILE SERVICES
# ===========================================================================
def get_employee_profile(employee_id):
    """Get complete employee profile with related data."""
    try:
        employee = Employee.query.get(employee_id)
        if not employee:
            return None
        return employee
    except Exception as e:
        logger.error(f'Error fetching profile for emp#{employee_id}: {e}')
        return None


def submit_profile_update_request(employee, field_name, new_value, ip=''):
    """Submit a profile update request for HR approval.
    Returns (success, message)."""
    try:
        # Get current value
        field_map = {
            'phone': lambda: employee.user.phone or '',
            'bank_account': lambda: employee.bank_account or '',
            'pan_number': lambda: employee.pan_number or '',
        }

        if field_name not in field_map:
            return False, f'Field "{field_name}" cannot be updated via self-service'

        old_value = field_map[field_name]()

        if old_value == new_value:
            return False, 'New value is the same as current value'

        # Check for existing pending request for same field
        existing = ProfileUpdateRequest.query.filter_by(
            employee_id=employee.id, field_name=field_name, status='Pending'
        ).first()
        if existing:
            return False, f'A pending request for {field_name} already exists'

        request_obj = ProfileUpdateRequest(
            employee_id=employee.id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            status='Pending'
        )
        db.session.add(request_obj)

        log_employee_action('SUBMIT', 'ProfileUpdateRequest', None,
                          f'Requested {field_name} change', ip)

        # Notify HR users
        from app.models import User, Module
        hr_module = Module.query.filter_by(slug='hr').first()
        if hr_module:
            for hr_user in hr_module.users:
                create_notification(
                    hr_user.id,
                    'Profile Update Request',
                    f'{employee.user.full_name} requested to update {field_name}',
                    category='info',
                    link='/hr/employees'
                )

        logger.info(f'Profile update request submitted: emp#{employee.id} field={field_name}')
        return True, 'Update request submitted for HR approval'
    except Exception as e:
        logger.error(f'Error submitting profile update: {e}')
        return False, 'An error occurred while submitting your request'


def get_profile_update_requests(employee_id):
    """Get all profile update requests for an employee."""
    try:
        return ProfileUpdateRequest.query.filter_by(
            employee_id=employee_id
        ).order_by(ProfileUpdateRequest.created_at.desc()).all()
    except Exception as e:
        logger.error(f'Error fetching profile requests: {e}')
        return []


# ===========================================================================
# ATTENDANCE SERVICES
# ===========================================================================
def perform_self_checkin(employee_id, ip=''):
    """Employee self check-in. Wraps HR services."""
    try:
        from app.hr.services import perform_checkin
        check_time = datetime.now().strftime('%H:%M')
        success, msg = perform_checkin(employee_id, check_time)
        if success:
            log_employee_action('CHECKIN', 'Attendance', employee_id,
                              msg, ip)
        logger.info(f'Self check-in emp#{employee_id}: {msg}')
        return success, msg
    except Exception as e:
        logger.error(f'Error during self check-in: {e}')
        return False, 'An error occurred during check-in'


def perform_self_checkout(employee_id, ip=''):
    """Employee self check-out. Wraps HR services."""
    try:
        from app.hr.services import perform_checkout
        check_time = datetime.now().strftime('%H:%M')
        success, msg = perform_checkout(employee_id, check_time)
        if success:
            log_employee_action('CHECKOUT', 'Attendance', employee_id,
                              msg, ip)
        logger.info(f'Self check-out emp#{employee_id}: {msg}')
        return success, msg
    except Exception as e:
        logger.error(f'Error during self check-out: {e}')
        return False, 'An error occurred during check-out'


def get_my_attendance_history(employee_id, limit=30):
    """Get recent attendance records for the employee."""
    try:
        return Attendance.query.filter_by(
            employee_id=employee_id
        ).order_by(Attendance.date.desc()).limit(limit).all()
    except Exception as e:
        logger.error(f'Error fetching attendance history: {e}')
        return []


def get_today_attendance(employee_id):
    """Get today's attendance record."""
    try:
        return Attendance.query.filter_by(
            employee_id=employee_id, date=date.today()
        ).first()
    except Exception as e:
        logger.error(f'Error fetching today attendance: {e}')
        return None


def get_my_attendance_summary(employee_id, year=None, month=None):
    """Get attendance summary for the employee."""
    try:
        from app.hr.services import get_attendance_summary
        year = year or date.today().year
        month = month or date.today().month
        return get_attendance_summary(employee_id, year, month)
    except Exception as e:
        logger.error(f'Error fetching attendance summary: {e}')
        return {'total_records': 0, 'present': 0, 'late': 0,
                'absent': 0, 'half_day': 0, 'total_hours': 0}


# ===========================================================================
# LEAVE SERVICES
# ===========================================================================
def get_my_leave_balances(employee_id, year=None):
    """Get all leave balances for the employee."""
    try:
        from app.hr.services import get_all_leave_balances
        return get_all_leave_balances(employee_id, year)
    except Exception as e:
        logger.error(f'Error fetching leave balances: {e}')
        return []


def get_my_leaves(employee_id, status=None):
    """Get leave history for the employee."""
    try:
        query = Leave.query.filter_by(employee_id=employee_id)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(Leave.created_at.desc()).all()
    except Exception as e:
        logger.error(f'Error fetching leaves: {e}')
        return []


def submit_leave_request(employee, leave_type, start_date, end_date, reason='', ip=''):
    """Submit a new leave request. Returns (success, message)."""
    try:
        from app.hr.services import validate_leave_request
        valid, msg = validate_leave_request(
            employee.id, leave_type, start_date, end_date
        )
        if not valid:
            return False, msg

        leave = Leave(
            employee_id=employee.id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            status='Pending'
        )
        leave.total_days = leave.calc_days()
        db.session.add(leave)

        log_employee_action('SUBMIT', 'Leave', None,
                          f'{leave_type}: {start_date} to {end_date} ({leave.total_days}d)', ip)

        create_notification(
            employee.user_id,
            'Leave Request Submitted',
            f'Your {leave_type} request for {leave.total_days} day(s) has been submitted.',
            category='info',
            link='/employee/leaves'
        )

        logger.info(f'Leave request submitted: emp#{employee.id} {leave_type} {leave.total_days}d')
        return True, f'Leave request submitted ({leave.total_days} day(s))'
    except Exception as e:
        logger.error(f'Error submitting leave request: {e}')
        return False, 'An error occurred while submitting your leave request'


# ===========================================================================
# PAYSLIP SERVICES (Read-only from Finance)
# ===========================================================================
def get_my_salary_records(employee_id):
    """Get all salary records for the employee."""
    try:
        return SalaryRecord.query.filter_by(
            employee_id=employee_id
        ).order_by(SalaryRecord.year.desc(), SalaryRecord.month.desc()).all()
    except Exception as e:
        logger.error(f'Error fetching salary records: {e}')
        return []


def get_payslip_detail(employee_id, record_id):
    """Get a specific payslip detail. Returns None if not found or unauthorized."""
    try:
        record = SalaryRecord.query.filter_by(
            id=record_id, employee_id=employee_id
        ).first()
        return record
    except Exception as e:
        logger.error(f'Error fetching payslip detail: {e}')
        return None


# ===========================================================================
# EXPENSE / REIMBURSEMENT SERVICES
# ===========================================================================
def submit_expense_claim(employee, category, amount, expense_date,
                         description='', receipt_file=None, ip=''):
    """Submit an expense claim. Returns (success, message)."""
    try:
        receipt_filename = ''
        receipt_original = ''

        if receipt_file and receipt_file.filename:
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads/documents')
            os.makedirs(upload_folder, exist_ok=True)

            ext = receipt_file.filename.rsplit('.', 1)[1].lower() if '.' in receipt_file.filename else 'bin'
            unique_id = uuid.uuid4().hex[:8]
            receipt_filename = f"receipt_{employee.emp_code}_{unique_id}.{ext}"
            receipt_original = receipt_file.filename
            filepath = os.path.join(upload_folder, receipt_filename)
            receipt_file.save(filepath)

        expense = EmployeeExpense(
            employee_id=employee.id,
            category=category,
            amount=amount,
            date=expense_date,
            description=description,
            receipt_filename=receipt_filename,
            receipt_original=receipt_original,
            status='Pending'
        )
        db.session.add(expense)

        log_employee_action('SUBMIT', 'EmployeeExpense', None,
                          f'{category}: ₹{amount}', ip)

        create_notification(
            employee.user_id,
            'Expense Claim Submitted',
            f'Your expense claim of ₹{amount:,.0f} ({category}) has been submitted.',
            category='info',
            link='/employee/expenses'
        )

        logger.info(f'Expense claim submitted: emp#{employee.id} {category} ₹{amount}')
        return True, f'Expense claim of ₹{amount:,.0f} submitted for approval'
    except Exception as e:
        logger.error(f'Error submitting expense claim: {e}')
        return False, 'An error occurred while submitting your expense claim'


def get_my_expense_claims(employee_id, status=None):
    """Get expense claims for the employee."""
    try:
        query = EmployeeExpense.query.filter_by(employee_id=employee_id)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(EmployeeExpense.created_at.desc()).all()
    except Exception as e:
        logger.error(f'Error fetching expense claims: {e}')
        return []


def get_expense_detail(employee_id, expense_id):
    """Get a specific expense claim detail."""
    try:
        return EmployeeExpense.query.filter_by(
            id=expense_id, employee_id=employee_id
        ).first()
    except Exception as e:
        logger.error(f'Error fetching expense detail: {e}')
        return None


# ===========================================================================
# DOCUMENT SERVICES (Read-only from HR)
# ===========================================================================
def get_my_documents(employee_id):
    """Get all documents for the employee."""
    try:
        return EmployeeDocument.query.filter_by(
            employee_id=employee_id
        ).order_by(EmployeeDocument.uploaded_at.desc()).all()
    except Exception as e:
        logger.error(f'Error fetching documents: {e}')
        return []


# ===========================================================================
# PERFORMANCE SERVICES (Read-only from HR)
# ===========================================================================
def get_my_reviews(employee_id):
    """Get performance reviews for the employee."""
    try:
        return PerformanceReview.query.filter_by(
            employee_id=employee_id
        ).order_by(PerformanceReview.created_at.desc()).all()
    except Exception as e:
        logger.error(f'Error fetching reviews: {e}')
        return []


# ===========================================================================
# NOTIFICATION SERVICES
# ===========================================================================
def get_my_notifications(user_id, limit=50):
    """Get notifications for the user."""
    try:
        return Notification.query.filter_by(
            user_id=user_id
        ).order_by(Notification.created_at.desc()).limit(limit).all()
    except Exception as e:
        logger.error(f'Error fetching notifications: {e}')
        return []


def get_unread_count(user_id):
    """Get unread notification count."""
    try:
        return Notification.query.filter_by(
            user_id=user_id, is_read=False
        ).count()
    except Exception as e:
        logger.error(f'Error fetching unread count: {e}')
        return 0


def mark_notification_read(notification_id, user_id):
    """Mark a notification as read. Returns success bool."""
    try:
        notif = Notification.query.filter_by(
            id=notification_id, user_id=user_id
        ).first()
        if notif:
            notif.is_read = True
            return True
        return False
    except Exception as e:
        logger.error(f'Error marking notification read: {e}')
        return False


def mark_all_notifications_read(user_id):
    """Mark all notifications as read."""
    try:
        Notification.query.filter_by(
            user_id=user_id, is_read=False
        ).update({'is_read': True})
        return True
    except Exception as e:
        logger.error(f'Error marking all notifications read: {e}')
        return False


# ===========================================================================
# PROJECT & TASK SERVICES (Read-only from PM)
# ===========================================================================
def get_my_projects(user_id):
    """Get projects where the user is a member."""
    try:
        memberships = ProjectMember.query.filter_by(user_id=user_id).all()
        project_ids = [m.project_id for m in memberships]
        if not project_ids:
            return [], {}
        projects = Project.query.filter(Project.id.in_(project_ids))\
            .order_by(Project.updated_at.desc()).all()
        # Build role map
        role_map = {m.project_id: m.role for m in memberships}
        return projects, role_map
    except Exception as e:
        logger.error(f'Error fetching projects: {e}')
        return [], {}


def get_my_tasks(user_id, status=None):
    """Get tasks assigned to the user."""
    try:
        query = Task.query.filter_by(assigned_to=user_id)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(Task.due_date.asc().nullslast()).all()
    except Exception as e:
        logger.error(f'Error fetching tasks: {e}')
        return []


def update_task_status(user_id, task_id, new_status, ip=''):
    """Update task status (Pending -> In Progress -> Done) for an assigned task."""
    try:
        task = Task.query.filter_by(id=task_id, assigned_to=user_id).first()
        if not task:
            return False, "Task not found or you are not assigned to it."
        
        allowed_transitions = {
            'Pending': ['In Progress', 'Done'],
            'In Progress': ['Pending', 'Done'],
            'Done': ['In Progress', 'Pending'] # Option to revert if needed, or we restrict it? The prompt says "predefined options: Pending -> In Progress -> Done" - we'll allow standard options.
        }
        
        valid_statuses = ['Pending', 'In Progress', 'Done']
        if new_status not in valid_statuses:
            return False, "Invalid status update requested."
            
        old_status = task.status
        if old_status == new_status:
            return False, "Task is already in that status."
            
        task.status = new_status
        task.updated_at = datetime.utcnow()
        
        log_employee_action('UPDATE', 'Task', task.id,
                          f'Updated task status from {old_status} to {new_status}', ip)
                          
        # Notify Project PM
        project = task.project
        create_notification(
            project.created_by,
            'Task Updated',
            f'Task "{task.title}" status changed to {new_status}.',
            category='info',
            link=f'/pm/projects/{project.id}'
        )
        
        task.project.check_and_update_status()
        
        logger.info(f'Task #{task.id} status updated to {new_status} by emp#{user_id}')
        return True, f'Task status updated to {new_status}.'
    except Exception as e:
        logger.error(f'Error updating task status: {e}')
        return False, 'An error occurred while updating the task status.'


# ===========================================================================
# SHIFT & COMP-OFF SERVICES (NEW)
# ===========================================================================
def get_my_shift(employee_id):
    """Get the employee's assigned shift details."""
    try:
        emp = Employee.query.get(employee_id)
        if not emp or not emp.shift_id:
            return None
        return Shift.query.get(emp.shift_id)
    except Exception as e:
        logger.error(f'Error fetching shift: {e}')
        return None


def get_my_shift_rules(employee_id):
    """Get shift rules for the employee (delegates to HR services)."""
    try:
        from app.hr.services import get_shift_rules_for_employee
        return get_shift_rules_for_employee(employee_id)
    except Exception as e:
        logger.error(f'Error fetching shift rules: {e}')
        return {'shift_name': 'General', 'start_time': '09:00', 'end_time': '18:00'}


def get_my_comp_offs(employee_id):
    """Get comp-off records for the employee."""
    try:
        return CompOff.query.filter_by(
            employee_id=employee_id
        ).order_by(CompOff.created_at.desc()).all()
    except Exception as e:
        logger.error(f'Error fetching comp-offs: {e}')
        return []


def get_my_shift_swap_requests(employee_id):
    """Get shift swap requests for the employee."""
    try:
        return ShiftSwapRequest.query.filter_by(
            employee_id=employee_id
        ).order_by(ShiftSwapRequest.created_at.desc()).all()
    except Exception as e:
        logger.error(f'Error fetching shift swap requests: {e}')
        return []


def submit_shift_swap_request(employee, requested_shift_id, reason='', ip=''):
    """Submit a shift swap request. Returns (success, message)."""
    try:
        # Check for existing pending request
        existing = ShiftSwapRequest.query.filter_by(
            employee_id=employee.id, status='Pending'
        ).first()
        if existing:
            return False, 'You already have a pending shift swap request'

        # Validate requested shift exists
        requested_shift = Shift.query.get(requested_shift_id)
        if not requested_shift or not requested_shift.is_active:
            return False, 'Requested shift is not available'

        # Check not requesting same shift
        if employee.shift_id == requested_shift_id:
            return False, 'You are already assigned to this shift'

        swap = ShiftSwapRequest(
            employee_id=employee.id,
            current_shift_id=employee.shift_id,
            requested_shift_id=requested_shift_id,
            reason=reason,
            status='Pending'
        )
        db.session.add(swap)

        log_employee_action('SUBMIT', 'ShiftSwapRequest', None,
                          f'Requested swap to {requested_shift.shift_name}', ip)

        # Notify HR
        from app.models import User, Module
        hr_module = Module.query.filter_by(slug='hr').first()
        if hr_module:
            for hr_user in hr_module.users:
                create_notification(
                    hr_user.id,
                    'Shift Swap Request',
                    f'{employee.user.full_name} requested shift change to {requested_shift.shift_name}',
                    category='info',
                    link='/hr/shift-swaps'
                )

        logger.info(f'Shift swap request submitted: emp#{employee.id} to {requested_shift.shift_name}')
        return True, f'Shift swap request submitted for {requested_shift.shift_name}'
    except Exception as e:
        logger.error(f'Error submitting shift swap: {e}')
        return False, 'An error occurred while submitting your shift swap request'

