"""Employee routes — personal dashboard, profile, tasks, leaves."""

from flask import render_template, redirect, url_for, flash
from flask_login import current_user
from app.employee import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Employee, Leave, Task, SalaryRecord, LeavePolicy
from app.employee.forms import LeaveRequestForm, ProfileForm


@bp.route('/')
@module_required('employee')
def dashboard():
    employee = current_user.employee
    my_tasks = Task.query.filter_by(assigned_to=current_user.id).all()
    tasks_pending = sum(1 for t in my_tasks if t.status != 'Done')
    tasks_done = sum(1 for t in my_tasks if t.status == 'Done')

    pending_leaves = 0
    leave_balances = []
    if employee:
        pending_leaves = Leave.query.filter_by(
            employee_id=employee.id, status='Pending').count()
        from app.hr.services import get_all_leave_balances
        leave_balances = get_all_leave_balances(employee.id)

    return render_template('employee/dashboard.html',
                           employee=employee,
                           my_tasks=my_tasks,
                           tasks_pending=tasks_pending,
                           tasks_done=tasks_done,
                           pending_leaves=pending_leaves,
                           leave_balances=leave_balances)


@bp.route('/profile', methods=['GET', 'POST'])
@module_required('employee')
def profile():
    form = ProfileForm(obj=current_user)
    employee = current_user.employee
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.phone = form.phone.data or ''
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('employee.profile'))
    return render_template('employee/profile.html', form=form, employee=employee)


@bp.route('/tasks')
@module_required('employee')
def my_tasks():
    tasks = Task.query.filter_by(assigned_to=current_user.id)\
        .order_by(Task.due_date.asc()).all()
    return render_template('employee/my_tasks.html', tasks=tasks)


@bp.route('/leaves')
@module_required('employee')
def my_leaves():
    employee = current_user.employee
    leaves = []
    leave_balances = []
    if employee:
        leaves = Leave.query.filter_by(employee_id=employee.id)\
            .order_by(Leave.created_at.desc()).all()
        from app.hr.services import get_all_leave_balances
        leave_balances = get_all_leave_balances(employee.id)
    return render_template('employee/my_leaves.html', leaves=leaves,
                           leave_balances=leave_balances)


@bp.route('/leaves/request', methods=['GET', 'POST'])
@module_required('employee')
def request_leave():
    employee = current_user.employee
    if not employee:
        flash('Your employee profile has not been set up. Contact HR.', 'warning')
        return redirect(url_for('employee.dashboard'))

    form = LeaveRequestForm()
    # Load leave types from Admin-configured policies
    policies = LeavePolicy.query.filter_by(is_active=True).order_by(LeavePolicy.leave_type).all()
    form.leave_type.choices = [(p.leave_type, p.leave_type) for p in policies]

    if form.validate_on_submit():
        if form.end_date.data < form.start_date.data:
            flash('End date cannot be before start date.', 'danger')
            return render_template('employee/leave_request.html', form=form)

        # Validate against Admin policies
        from app.hr.services import validate_leave_request
        valid, msg = validate_leave_request(
            employee.id, form.leave_type.data,
            form.start_date.data, form.end_date.data
        )
        if not valid:
            flash(msg, 'danger')
            return render_template('employee/leave_request.html', form=form)

        leave = Leave(
            employee_id=employee.id,
            leave_type=form.leave_type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            reason=form.reason.data or '',
            status='Pending'
        )
        leave.total_days = leave.calc_days()
        db.session.add(leave)
        db.session.commit()
        flash(f'Leave request submitted ({leave.total_days} day(s)).', 'success')
        return redirect(url_for('employee.my_leaves'))
    return render_template('employee/leave_request.html', form=form)

