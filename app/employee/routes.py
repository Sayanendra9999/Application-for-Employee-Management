"""Employee routes — Production-level self-service portal.

All routes use @module_required('employee') for RBAC.
Employee can only view/submit — no approval permissions.
"""

from flask import (render_template, redirect, url_for, flash, request,
                   current_app, send_from_directory, jsonify)
from flask_login import current_user
from app.employee import bp
from app.decorators import module_required
from app.extensions import db
from app.models import LeavePolicy, Shift
from app.employee import services
from app.employee.utils import get_current_employee_or_abort, logger
from app.employee.forms import (ProfileForm, ProfileUpdateRequestForm,
                                LeaveRequestForm, ExpenseClaimForm,
                                TimesheetForm)


# ===========================================================================
# DASHBOARD
# ===========================================================================
@bp.route('/')
@module_required('employee')
def dashboard():
    """Rich employee dashboard with stats, attendance, notifications."""
    employee = current_user.employee
    today_att = None
    leave_balances = []
    pending_leaves = 0
    att_summary = {}
    profile_complete = False
    shift_rules = None
    comp_off_count = 0

    if employee:
        from app.hr import services as hr_services
        profile_complete = hr_services.is_employee_profile_complete(employee)
        today_att = services.get_today_attendance(employee.id)
        leave_balances = services.get_my_leave_balances(employee.id)
        pending_leaves = len(services.get_my_leaves(employee.id, status='Pending'))
        att_summary = services.get_my_attendance_summary(employee.id)
        shift_rules = services.get_my_shift_rules(employee.id)
        comp_off_count = len([c for c in services.get_my_comp_offs(employee.id) if c.status == 'Earned'])

    tasks = services.get_my_tasks(current_user.id)
    tasks_pending = sum(1 for t in tasks if t.status != 'Done')
    tasks_done = sum(1 for t in tasks if t.status == 'Done')
    notifications = services.get_my_notifications(current_user.id, limit=5)
    unread_count = services.get_unread_count(current_user.id)

    # Timesheet summary for dashboard
    ts_summary = services.get_timesheet_summary(employee.id) if employee else {
        'total_entries': 0, 'total_hours': 0, 'approved_hours': 0,
        'pending_hours': 0, 'rejected_count': 0
    }

    return render_template('employee/dashboard.html',
                           employee=employee,
                           profile_complete=profile_complete,
                           today_att=today_att,
                           leave_balances=leave_balances,
                           pending_leaves=pending_leaves,
                           att_summary=att_summary,
                           shift_rules=shift_rules,
                           comp_off_count=comp_off_count,
                           tasks=tasks[:5],
                           tasks_pending=tasks_pending,
                           tasks_done=tasks_done,
                           notifications=notifications,
                           unread_count=unread_count,
                           ts_summary=ts_summary)


# ===========================================================================
# PROFILE
# ===========================================================================
@bp.route('/profile', methods=['GET', 'POST'])
@module_required('employee')
def profile():
    """View and update basic profile info."""
    employee = current_user.employee
    form = ProfileForm(obj=current_user)

    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.phone = form.phone.data or ''
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        logger.info(f'Profile updated by {current_user.username}')
        return redirect(url_for('employee.profile'))

    update_requests = []
    if employee:
        update_requests = services.get_profile_update_requests(employee.id)

    return render_template('employee/profile.html',
                           form=form, employee=employee,
                           update_requests=update_requests)


@bp.route('/profile/update-request', methods=['GET', 'POST'])
@module_required('employee')
def profile_update_request():
    """Submit a profile update request for HR approval."""
    employee = get_current_employee_or_abort()
    form = ProfileUpdateRequestForm()

    if form.validate_on_submit():
        success, msg = services.submit_profile_update_request(
            employee, form.field_name.data, form.new_value.data,
            ip=request.remote_addr or ''
        )
        if success:
            db.session.commit()
            flash(msg, 'success')
        else:
            flash(msg, 'danger')
        return redirect(url_for('employee.profile'))

    return render_template('employee/profile_update_request.html',
                           form=form, employee=employee)


# ===========================================================================
# ATTENDANCE
# ===========================================================================
@bp.route('/attendance')
@module_required('employee')
def attendance():
    """View attendance history."""
    employee = get_current_employee_or_abort()
    today_att = services.get_today_attendance(employee.id)
    records = services.get_my_attendance_history(employee.id, limit=60)
    summary = services.get_my_attendance_summary(employee.id)

    return render_template('employee/attendance.html',
                           employee=employee,
                           today_att=today_att,
                           records=records,
                           summary=summary)


@bp.route('/attendance/checkin', methods=['POST'])
@module_required('employee')
def attendance_checkin():
    """Self check-in."""
    employee = get_current_employee_or_abort()
    success, msg = services.perform_self_checkin(
        employee.id, ip=request.remote_addr or ''
    )
    if success:
        db.session.commit()
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('employee.attendance'))


@bp.route('/attendance/checkout', methods=['POST'])
@module_required('employee')
def attendance_checkout():
    """Self check-out."""
    employee = get_current_employee_or_abort()
    success, msg = services.perform_self_checkout(
        employee.id, ip=request.remote_addr or ''
    )
    if success:
        db.session.commit()
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('employee.attendance'))


# ===========================================================================
# LEAVE MANAGEMENT
# ===========================================================================
@bp.route('/leaves')
@module_required('employee')
def my_leaves():
    """View leave history with status filter."""
    employee = get_current_employee_or_abort()
    status_filter = request.args.get('status', '')
    leaves = services.get_my_leaves(employee.id, status=status_filter or None)
    leave_balances = services.get_my_leave_balances(employee.id)

    return render_template('employee/my_leaves.html',
                           leaves=leaves,
                           leave_balances=leave_balances,
                           selected_status=status_filter)


@bp.route('/leaves/balance')
@module_required('employee')
def leave_balance():
    """View leave balance details."""
    employee = get_current_employee_or_abort()
    balances = services.get_my_leave_balances(employee.id)
    from app.hr.services import get_leave_policies_for_employee
    policies = get_leave_policies_for_employee(employee.id)

    return render_template('employee/leave_balance.html',
                           balances=balances, policies=policies,
                           employee=employee)


@bp.route('/leaves/request', methods=['GET', 'POST'])
@module_required('employee')
def request_leave():
    """Apply for leave."""
    employee = get_current_employee_or_abort()
    form = LeaveRequestForm()
    # Get only policies applicable to this employee's designation (role-based)
    from app.hr.services import get_leave_policies_for_employee
    applicable_policies = get_leave_policies_for_employee(employee.id)
    form.leave_type.choices = list(set([(p.leave_type, p.leave_type) for p in applicable_policies]))
    leave_balances = services.get_my_leave_balances(employee.id)

    if form.validate_on_submit():
        if form.end_date.data < form.start_date.data:
            flash('End date cannot be before start date.', 'danger')
            return render_template('employee/leave_request.html',
                                   form=form, leave_balances=leave_balances)

        success, msg = services.submit_leave_request(
            employee, form.leave_type.data,
            form.start_date.data, form.end_date.data,
            reason=form.reason.data or '',
            ip=request.remote_addr or ''
        )
        if success:
            db.session.commit()
            flash(msg, 'success')
            return redirect(url_for('employee.my_leaves'))
        else:
            flash(msg, 'danger')

    return render_template('employee/leave_request.html',
                           form=form, leave_balances=leave_balances)


# ===========================================================================
# PAYSLIPS (Read-only from Finance)
# ===========================================================================
@bp.route('/payslips')
@module_required('employee')
def payslips():
    """View salary records / payslips."""
    employee = get_current_employee_or_abort()
    records = services.get_my_salary_records(employee.id)
    return render_template('employee/payslips.html',
                           records=records, employee=employee)


@bp.route('/payslips/<int:record_id>')
@module_required('employee')
def payslip_detail(record_id):
    """View payslip detail."""
    employee = get_current_employee_or_abort()
    record = services.get_payslip_detail(employee.id, record_id)
    if not record:
        flash('Payslip not found.', 'danger')
        return redirect(url_for('employee.payslips'))
    return render_template('employee/payslip_detail.html',
                           record=record, employee=employee)


# ===========================================================================
# EXPENSES & REIMBURSEMENT
# ===========================================================================
@bp.route('/expenses')
@module_required('employee')
def expenses():
    """View expense claims."""
    employee = get_current_employee_or_abort()
    status_filter = request.args.get('status', '')
    claims = services.get_my_expense_claims(employee.id,
                                            status=status_filter or None)
    return render_template('employee/expenses.html',
                           claims=claims, selected_status=status_filter)


@bp.route('/expenses/submit', methods=['GET', 'POST'])
@module_required('employee')
def submit_expense():
    """Submit expense claim with receipt upload."""
    employee = get_current_employee_or_abort()
    form = ExpenseClaimForm()

    if form.validate_on_submit():
        success, msg = services.submit_expense_claim(
            employee,
            category=form.category.data,
            amount=form.amount.data,
            expense_date=form.date.data,
            description=form.description.data,
            receipt_file=form.receipt.data,
            ip=request.remote_addr or ''
        )
        if success:
            db.session.commit()
            flash(msg, 'success')
            return redirect(url_for('employee.expenses'))
        else:
            flash(msg, 'danger')

    return render_template('employee/expense_form.html', form=form)


@bp.route('/expenses/<int:expense_id>')
@module_required('employee')
def expense_detail(expense_id):
    """View expense claim detail."""
    employee = get_current_employee_or_abort()
    claim = services.get_expense_detail(employee.id, expense_id)
    if not claim:
        flash('Expense claim not found.', 'danger')
        return redirect(url_for('employee.expenses'))
    return render_template('employee/expense_detail.html', claim=claim)


# ===========================================================================
# DOCUMENT CENTER (Read-only from HR)
# ===========================================================================
@bp.route('/documents')
@module_required('employee')
def documents():
    """View/download employee documents."""
    employee = get_current_employee_or_abort()
    docs = services.get_my_documents(employee.id)
    return render_template('employee/documents.html',
                           documents=docs, employee=employee)


@bp.route('/documents/<int:doc_id>/download')
@module_required('employee')
def document_download(doc_id):
    """Download a specific document."""
    employee = get_current_employee_or_abort()
    from app.models import EmployeeDocument
    doc = EmployeeDocument.query.filter_by(
        id=doc_id, employee_id=employee.id
    ).first_or_404()
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads/documents')
    return send_from_directory(upload_folder, doc.filename,
                               as_attachment=True,
                               download_name=doc.original_name)


# ===========================================================================
# PERFORMANCE & FEEDBACK (Read-only from HR)
# ===========================================================================
@bp.route('/performance')
@module_required('employee')
def performance():
    """View performance reviews."""
    employee = get_current_employee_or_abort()
    reviews = services.get_my_reviews(employee.id)
    return render_template('employee/performance.html',
                           reviews=reviews, employee=employee)


@bp.route('/performance/<int:review_id>')
@module_required('employee')
def performance_detail(review_id):
    """View performance review detail."""
    employee = get_current_employee_or_abort()
    from app.models import PerformanceReview
    review = PerformanceReview.query.filter_by(
        id=review_id, employee_id=employee.id
    ).first_or_404()
    return render_template('employee/performance_detail.html', review=review)


# ===========================================================================
# NOTIFICATIONS
# ===========================================================================
@bp.route('/notifications')
@module_required('employee')
def notifications():
    """View all notifications."""
    notifs = services.get_my_notifications(current_user.id, limit=100)
    unread_count = services.get_unread_count(current_user.id)
    return render_template('employee/notifications.html',
                           notifications=notifs, unread_count=unread_count)


@bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@module_required('employee')
def mark_read(notif_id):
    """Mark a notification as read."""
    services.mark_notification_read(notif_id, current_user.id)
    db.session.commit()
    return redirect(url_for('employee.notifications'))


@bp.route('/notifications/mark-all-read', methods=['POST'])
@module_required('employee')
def mark_all_read():
    """Mark all notifications as read."""
    services.mark_all_notifications_read(current_user.id)
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('employee.notifications'))


# ===========================================================================
# PROJECTS & TASKS (Read-only from PM)
# ===========================================================================
@bp.route('/projects')
@module_required('employee')
def projects():
    """View assigned projects."""
    project_list, role_map = services.get_my_projects(current_user.id)
    return render_template('employee/projects.html',
                           projects=project_list, role_map=role_map)


@bp.route('/tasks')
@module_required('employee')
def my_tasks():
    """View assigned tasks."""
    status_filter = request.args.get('status', '')
    tasks = services.get_my_tasks(current_user.id,
                                  status=status_filter or None)
    return render_template('employee/my_tasks.html',
                           tasks=tasks, selected_status=status_filter)


@bp.route('/api/tasks/<int:task_id>/status', methods=['POST'])
@module_required('employee')
def update_task_status(task_id):
    """Update task status via API (Pending -> In Progress -> Done)."""
    data = request.get_json()
    new_status = data.get('status')
    
    success, msg = services.update_task_status(
        user_id=current_user.id,
        task_id=task_id,
        new_status=new_status,
        ip=request.remote_addr or ''
    )
    if success:
        db.session.commit()
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'message': msg}), 400


@bp.route('/tasks/<int:task_id>/log-hours', methods=['POST'])
@module_required('employee')
def log_task_hours(task_id):
    """DEPRECATED — Hours are now tracked via the Timesheet system."""
    flash('Direct hour logging has been replaced by the Timesheet system. '
          'Please use My Timesheets to submit hours.', 'info')
    return redirect(url_for('employee.my_timesheets'))


# ===========================================================================
# SHIFT SWAP REQUEST (NEW)
# ===========================================================================
@bp.route('/shift-swap', methods=['GET', 'POST'])
@module_required('employee')
def shift_swap():
    """Submit a shift swap request."""
    employee = get_current_employee_or_abort()
    shifts = Shift.query.filter_by(is_active=True).order_by(Shift.shift_name).all()
    my_shift = services.get_my_shift(employee.id)
    swap_requests = services.get_my_shift_swap_requests(employee.id)

    if request.method == 'POST':
        requested_shift_id = request.form.get('shift_id', type=int)
        reason = request.form.get('reason', '')
        if not requested_shift_id:
            flash('Please select a shift.', 'danger')
        else:
            success, msg = services.submit_shift_swap_request(
                employee, requested_shift_id, reason=reason,
                ip=request.remote_addr or ''
            )
            if success:
                db.session.commit()
                flash(msg, 'success')
            else:
                flash(msg, 'danger')
        return redirect(url_for('employee.shift_swap'))

    return render_template('employee/shift_swap.html',
                           employee=employee,
                           shifts=shifts,
                           my_shift=my_shift,
                           swap_requests=swap_requests)


# ===========================================================================
# COMP-OFF VIEW (NEW)
# ===========================================================================
@bp.route('/comp-offs')
@module_required('employee')
def my_comp_offs():
    """View comp-off records."""
    employee = get_current_employee_or_abort()
    comp_offs = services.get_my_comp_offs(employee.id)
    return render_template('employee/comp_offs.html',
                           comp_offs=comp_offs, employee=employee)


# ===========================================================================
# TIMESHEETS
# ===========================================================================
@bp.route('/timesheets')
@module_required('employee')
def my_timesheets():
    """View timesheet history with status filter."""
    employee = get_current_employee_or_abort()
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    from datetime import datetime as dt
    d_from = None
    d_to = None
    if date_from:
        try:
            d_from = dt.strptime(date_from, '%Y-%m-%d').date()
        except ValueError:
            pass
    if date_to:
        try:
            d_to = dt.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            pass

    timesheets = services.get_my_timesheets(
        employee.id,
        status=status_filter or None,
        date_from=d_from,
        date_to=d_to
    )
    summary = services.get_timesheet_summary(employee.id)

    return render_template('employee/my_timesheets.html',
                           timesheets=timesheets,
                           summary=summary,
                           selected_status=status_filter,
                           date_from=date_from,
                           date_to=date_to)


@bp.route('/timesheets/submit', methods=['GET', 'POST'])
@module_required('employee')
def submit_timesheet():
    """Submit a new timesheet entry."""
    employee = get_current_employee_or_abort()
    form = TimesheetForm()

    # Populate project dropdown with assigned projects
    projects = services.get_assigned_projects_for_employee(current_user.id)
    form.project_id.choices = [(0, '— Select Project —')] + [
        (p.id, p.name) for p in projects
    ]
    # Task choices will be populated via AJAX on frontend; start with empty
    form.task_id.choices = [(0, '— No Task (General) —')]

    # On POST, populate task choices so WTForms validation succeeds
    if request.method == 'POST':
        try:
            proj_id = int(request.form.get('project_id', 0))
            if proj_id > 0:
                tasks = services.get_tasks_for_project_user(current_user.id, proj_id)
                form.task_id.choices += [(t.id, t.title) for t in tasks]
        except ValueError:
            pass

    if form.validate_on_submit():
        if form.project_id.data == 0:
            flash('Please select a project.', 'danger')
            return render_template('employee/timesheet_form.html',
                                   form=form, employee=employee)

        success, msg = services.submit_timesheet(
            employee,
            project_id=form.project_id.data,
            task_id=form.task_id.data,
            ts_date=form.date.data,
            hours=form.hours_worked.data,
            description=form.description.data,
            ip=request.remote_addr or ''
        )
        if success:
            db.session.commit()
            flash(msg, 'success')
            return redirect(url_for('employee.my_timesheets'))
        else:
            flash(msg, 'danger')

    return render_template('employee/timesheet_form.html',
                           form=form, employee=employee)


@bp.route('/api/tasks-for-project/<int:project_id>')
@module_required('employee')
def api_tasks_for_project(project_id):
    """AJAX endpoint: Get tasks assigned to the current user in a project."""
    tasks = services.get_tasks_for_project_user(current_user.id, project_id)
    data = [{'id': t.id, 'title': t.title, 'status': t.status} for t in tasks]
    return jsonify({'tasks': data})

