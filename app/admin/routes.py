"""Admin routes — user CRUD, module assignment, HR configuration, Shift management."""

import secrets
import string
from flask import render_template, redirect, url_for, flash, request, session
from app.admin import bp
from app.decorators import admin_required
from app.extensions import db
from app.models import (User, Module, UserModule, Employee, Project, Task,
                        Milestone, Notification,
                        Department, Designation, LeavePolicy, AttendanceRule, AuditLog,
                        Shift, Timesheet)
from app.admin.forms import UserCreateForm, UserEditForm, ModuleAssignForm
from app.admin.config_forms import (DepartmentForm, DesignationForm,
                                     LeavePolicyForm, AttendanceRuleForm, ShiftForm)


def generate_readable_password():
    """Generate a readable temporary password like 'Welcome@7842'."""
    digits = ''.join(secrets.choice(string.digits) for _ in range(4))
    return f'Welcome@{digits}'


def log_audit(user_id, action, entity_type, entity_id=None, details=''):
    """Write an audit log entry."""
    from flask import request as req
    log = AuditLog(
        user_id=user_id, action=action, entity_type=entity_type,
        entity_id=entity_id, details=details,
        ip_address=req.remote_addr or ''
    )
    db.session.add(log)


# ===========================================================================
# DASHBOARD
# ===========================================================================
@bp.route('/')
@admin_required
def dashboard():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active_user=True).count()
    total_modules = Module.query.count()
    total_employees = Employee.query.count()
    total_projects = Project.query.count()
    total_notifications = Notification.query.count()
    total_departments = Department.query.count()
    total_designations = Designation.query.count()
    total_shifts = Shift.query.filter_by(is_active=True).count()
    total_leave_policies = LeavePolicy.query.filter_by(is_active=True).count()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    # Count unassigned employees for onboarding visibility
    from app.hr import services as hr_services
    unassigned_employees = hr_services.get_unassigned_count()

    # Timesheet stats
    total_timesheets = Timesheet.query.count()
    pending_timesheets = Timesheet.query.filter_by(status='Pending').count()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           active_users=active_users,
                           total_modules=total_modules,
                           total_employees=total_employees,
                           total_projects=total_projects,
                           total_notifications=total_notifications,
                           total_departments=total_departments,
                           total_designations=total_designations,
                           total_shifts=total_shifts,
                           total_leave_policies=total_leave_policies,
                           recent_users=recent_users,
                           unassigned_employees=unassigned_employees,
                           total_timesheets=total_timesheets,
                           pending_timesheets=pending_timesheets)


# ===========================================================================
# USER MANAGEMENT (unchanged)
# ===========================================================================
@bp.route('/users')
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    new_user_info = session.pop('new_user_info', None)
    from app.hr import services as hr_services
    return render_template('admin/users.html', users=all_users,
                           new_user_info=new_user_info,
                           is_profile_complete=hr_services.is_employee_profile_complete)


@bp.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    form = UserCreateForm()
    all_modules = Module.query.order_by(Module.name).all()
    form.modules.choices = [(m.id, m.name) for m in all_modules]

    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists.', 'danger')
            return render_template('admin/user_form.html', form=form, title='Add User', all_modules=all_modules)
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists.', 'danger')
            return render_template('admin/user_form.html', form=form, title='Add User', all_modules=all_modules)

        selected_ids = set(form.modules.data or [])
        admin_module = Module.query.filter_by(slug='admin').first()
        is_admin_selected = (admin_module and admin_module.id in selected_ids)

        temp_password = generate_readable_password()
        user = User(
            username=form.username.data, email=form.email.data,
            full_name=form.full_name.data, phone=form.phone.data,
            is_admin=is_admin_selected, must_change_password=True
        )
        user.set_password(temp_password)
        db.session.add(user)
        db.session.flush()

        selected_ids = set(form.modules.data or [])
        emp_module = Module.query.filter_by(slug='employee').first()
        if emp_module:
            selected_ids.add(emp_module.id)
        for mod_id in selected_ids:
            db.session.add(UserModule(user_id=user.id, module_id=mod_id))

        # Auto-create an employee profile so the user can access Employee module without 404
        emp = Employee(
            user_id=user.id,
            emp_code=f"EMP{user.id:04d}"
        )
        db.session.add(emp)
        db.session.flush()
        
        from app.hr import services
        services.initialize_leave_balances(emp.id)

        from flask_login import current_user
        log_audit(current_user.id, 'CREATE', 'User', user.id, f'Created user {user.username}')
        db.session.commit()

        session['new_user_info'] = {
            'username': user.username, 'full_name': user.full_name,
            'password': temp_password
        }
        flash(f'User "{user.username}" created successfully.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', form=form, title='Add User', all_modules=all_modules)


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)
    all_modules = Module.query.order_by(Module.name).all()
    form.modules.choices = [(m.id, m.name) for m in all_modules]

    if request.method == 'GET':
        form.is_active.data = user.is_active_user
        form.modules.data = [m.id for m in user.modules]

    if form.validate_on_submit():
        existing = User.query.filter(User.username == form.username.data, User.id != user.id).first()
        if existing:
            flash('Username already taken.', 'danger')
            return render_template('admin/user_form.html', form=form, title='Edit User', user=user, all_modules=all_modules)
        existing = User.query.filter(User.email == form.email.data, User.id != user.id).first()
        if existing:
            flash('Email already taken.', 'danger')
            return render_template('admin/user_form.html', form=form, title='Edit User', user=user, all_modules=all_modules)

        user.username = form.username.data
        user.email = form.email.data
        user.full_name = form.full_name.data
        user.phone = form.phone.data
        user.is_active_user = form.is_active.data
        if form.password.data:
            user.set_password(form.password.data)

        UserModule.query.filter_by(user_id=user.id).delete()
        selected_ids = set(form.modules.data or [])
        admin_module = Module.query.filter_by(slug='admin').first()
        user.is_admin = (admin_module and admin_module.id in selected_ids)

        emp_module = Module.query.filter_by(slug='employee').first()
        if emp_module:
            selected_ids.add(emp_module.id)
        for mod_id in selected_ids:
            db.session.add(UserModule(user_id=user.id, module_id=mod_id))

        from flask_login import current_user
        log_audit(current_user.id, 'UPDATE', 'User', user.id, f'Updated user {user.username}')
        db.session.commit()
        flash(f'User "{user.username}" updated.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', form=form, title='Edit User', user=user, all_modules=all_modules)


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Cannot delete an admin user.', 'danger')
        return redirect(url_for('admin.users'))
    user.is_active_user = False
    from flask_login import current_user
    log_audit(current_user.id, 'DEACTIVATE', 'User', user.id, f'Deactivated user {user.username}')
    db.session.commit()
    flash(f'User "{user.username}" deactivated.', 'warning')
    return redirect(url_for('admin.users'))


@bp.route('/users/<int:user_id>/modules', methods=['GET', 'POST'])
@admin_required
def assign_modules(user_id):
    user = User.query.get_or_404(user_id)
    form = ModuleAssignForm()
    all_modules = Module.query.order_by(Module.name).all()
    form.modules.choices = [(m.id, m.name) for m in all_modules]
    if request.method == 'GET':
        form.modules.data = [m.id for m in user.modules]
    if form.validate_on_submit():
        UserModule.query.filter_by(user_id=user.id).delete()
        for mod_id in form.modules.data:
            db.session.add(UserModule(user_id=user.id, module_id=mod_id))
        db.session.commit()
        flash(f'Permissions updated for "{user.username}".', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/assign_modules.html', form=form, user=user, modules=all_modules)


@bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    temp_password = generate_readable_password()
    user.set_password(temp_password)
    user.must_change_password = True
    db.session.commit()
    session['new_user_info'] = {
        'username': user.username, 'full_name': user.full_name, 'password': temp_password
    }
    flash(f'Password reset for "{user.username}". See the credentials below.', 'success')
    return redirect(url_for('admin.users'))


# ===========================================================================
# DEPARTMENT MANAGEMENT (NEW)
# ===========================================================================
@bp.route('/departments')
@admin_required
def departments():
    all_depts = Department.query.order_by(Department.name).all()
    return render_template('admin/departments.html', departments=all_depts)


@bp.route('/departments/add', methods=['GET', 'POST'])
@admin_required
def add_department():
    form = DepartmentForm()
    if form.validate_on_submit():
        if Department.query.filter_by(code=form.code.data).first():
            flash('Department code already exists.', 'danger')
            return render_template('admin/department_form.html', form=form, title='Add Department')
        dept = Department(
            name=form.name.data, code=form.code.data.upper(),
            description=form.description.data or '', is_active=form.is_active.data
        )
        db.session.add(dept)
        from flask_login import current_user
        log_audit(current_user.id, 'CREATE', 'Department', None, f'Created dept {dept.code}')
        db.session.commit()
        flash(f'Department "{dept.name}" created.', 'success')
        return redirect(url_for('admin.departments'))
    return render_template('admin/department_form.html', form=form, title='Add Department')


@bp.route('/departments/<int:dept_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    form = DepartmentForm(obj=dept)
    if form.validate_on_submit():
        existing = Department.query.filter(Department.code == form.code.data, Department.id != dept.id).first()
        if existing:
            flash('Department code already taken.', 'danger')
            return render_template('admin/department_form.html', form=form, title='Edit Department', dept=dept)
        dept.name = form.name.data
        dept.code = form.code.data.upper()
        dept.description = form.description.data or ''
        dept.is_active = form.is_active.data
        from flask_login import current_user
        log_audit(current_user.id, 'UPDATE', 'Department', dept.id, f'Updated dept {dept.code}')
        db.session.commit()
        flash(f'Department "{dept.name}" updated.', 'success')
        return redirect(url_for('admin.departments'))
    return render_template('admin/department_form.html', form=form, title='Edit Department', dept=dept)


# ===========================================================================
# DESIGNATION MANAGEMENT (NEW)
# ===========================================================================
@bp.route('/designations')
@admin_required
def designations():
    all_desig = Designation.query.order_by(Designation.department_id, Designation.level).all()
    return render_template('admin/designations.html', designations=all_desig)


@bp.route('/designations/add', methods=['GET', 'POST'])
@admin_required
def add_designation():
    form = DesignationForm()
    form.department_id.choices = [(d.id, d.name) for d in Department.query.filter_by(is_active=True).order_by(Department.name)]
    if form.validate_on_submit():
        desig = Designation(
            title=form.title.data, department_id=form.department_id.data,
            level=form.level.data, is_active=form.is_active.data
        )
        db.session.add(desig)
        from flask_login import current_user
        log_audit(current_user.id, 'CREATE', 'Designation', None, f'Created designation {desig.title}')
        db.session.commit()
        flash(f'Designation "{desig.title}" created.', 'success')
        return redirect(url_for('admin.designations'))
    return render_template('admin/designation_form.html', form=form, title='Add Designation')


@bp.route('/designations/<int:desig_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_designation(desig_id):
    desig = Designation.query.get_or_404(desig_id)
    form = DesignationForm(obj=desig)
    form.department_id.choices = [(d.id, d.name) for d in Department.query.filter_by(is_active=True).order_by(Department.name)]
    if form.validate_on_submit():
        desig.title = form.title.data
        desig.department_id = form.department_id.data
        desig.level = form.level.data
        desig.is_active = form.is_active.data
        from flask_login import current_user
        log_audit(current_user.id, 'UPDATE', 'Designation', desig.id, f'Updated designation {desig.title}')
        db.session.commit()
        flash(f'Designation "{desig.title}" updated.', 'success')
        return redirect(url_for('admin.designations'))
    return render_template('admin/designation_form.html', form=form, title='Edit Designation', desig=desig)


# ===========================================================================
# LEAVE POLICY MANAGEMENT (UPGRADED — designation-linked)
# ===========================================================================
@bp.route('/leave-policies')
@admin_required
def leave_policies():
    policies = LeavePolicy.query.order_by(LeavePolicy.leave_type, LeavePolicy.designation_id).all()
    return render_template('admin/leave_policies.html', policies=policies)


@bp.route('/leave-policies/add', methods=['GET', 'POST'])
@admin_required
def add_leave_policy():
    form = LeavePolicyForm()
    form.designation_id.choices = [(0, '— Global (All Roles) —')] + [
        (d.id, f'{d.title} ({d.department.name})') for d in
        Designation.query.filter_by(is_active=True).order_by(Designation.title)
    ]
    if form.validate_on_submit():
        desig_id = form.designation_id.data if form.designation_id.data != 0 else None
        # Check uniqueness: same leave_type + designation combo
        existing = LeavePolicy.query.filter_by(
            leave_type=form.leave_type.data, designation_id=desig_id
        ).first()
        if existing:
            flash(f'Leave policy "{form.leave_type.data}" already exists for this designation.', 'danger')
            return render_template('admin/leave_policy_form.html', form=form, title='Add Leave Policy')
        policy = LeavePolicy(
            leave_type=form.leave_type.data,
            designation_id=desig_id,
            total_days=form.total_days.data,
            carry_forward=form.carry_forward.data,
            max_carry_days=form.max_carry_days.data or 0,
            monthly_accrual=form.monthly_accrual.data,
            encashment_allowed=form.encashment_allowed.data,
            max_per_request=form.max_per_request.data if form.max_per_request.data else None,
            blackout_dates=form.blackout_dates.data or '',
            description=form.description.data or '',
            is_active=form.is_active.data
        )
        db.session.add(policy)
        from flask_login import current_user
        log_audit(current_user.id, 'CREATE', 'LeavePolicy', None, f'Created policy {policy.leave_type}')
        db.session.commit()
        flash(f'Leave policy "{policy.leave_type}" created.', 'success')
        return redirect(url_for('admin.leave_policies'))
    return render_template('admin/leave_policy_form.html', form=form, title='Add Leave Policy')


@bp.route('/leave-policies/<int:policy_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_leave_policy(policy_id):
    policy = LeavePolicy.query.get_or_404(policy_id)
    form = LeavePolicyForm(obj=policy)
    form.designation_id.choices = [(0, '— Global (All Roles) —')] + [
        (d.id, f'{d.title} ({d.department.name})') for d in
        Designation.query.filter_by(is_active=True).order_by(Designation.title)
    ]
    if request.method == 'GET':
        form.designation_id.data = policy.designation_id or 0
    if form.validate_on_submit():
        desig_id = form.designation_id.data if form.designation_id.data != 0 else None
        policy.leave_type = form.leave_type.data
        policy.designation_id = desig_id
        policy.total_days = form.total_days.data
        policy.carry_forward = form.carry_forward.data
        policy.max_carry_days = form.max_carry_days.data or 0
        policy.monthly_accrual = form.monthly_accrual.data
        policy.encashment_allowed = form.encashment_allowed.data
        policy.max_per_request = form.max_per_request.data if form.max_per_request.data else None
        policy.blackout_dates = form.blackout_dates.data or ''
        policy.description = form.description.data or ''
        policy.is_active = form.is_active.data
        from flask_login import current_user
        log_audit(current_user.id, 'UPDATE', 'LeavePolicy', policy.id, f'Updated policy {policy.leave_type}')
        db.session.commit()
        flash(f'Leave policy "{policy.leave_type}" updated.', 'success')
        return redirect(url_for('admin.leave_policies'))
    return render_template('admin/leave_policy_form.html', form=form, title='Edit Leave Policy', policy=policy)


# ===========================================================================
# ATTENDANCE RULES (single config — acts as General Shift)
# ===========================================================================
@bp.route('/attendance-rules', methods=['GET', 'POST'])
@admin_required
def attendance_rules():
    rule = AttendanceRule.query.first()
    if not rule:
        rule = AttendanceRule()
        db.session.add(rule)
        db.session.commit()
    form = AttendanceRuleForm(obj=rule)
    if form.validate_on_submit():
        rule.work_start = form.work_start.data
        rule.work_end = form.work_end.data
        rule.late_threshold_mins = form.late_threshold_mins.data
        rule.half_day_hours = form.half_day_hours.data
        rule.full_day_hours = form.full_day_hours.data
        from flask_login import current_user
        log_audit(current_user.id, 'UPDATE', 'AttendanceRule', rule.id, 'Updated attendance rules')
        db.session.commit()
        flash('Attendance rules updated.', 'success')
        return redirect(url_for('admin.attendance_rules'))
    return render_template('admin/attendance_rules.html', form=form, rule=rule)


# ===========================================================================
# SHIFT MANAGEMENT (NEW)
# ===========================================================================
@bp.route('/shifts')
@admin_required
def shifts():
    all_shifts = Shift.query.order_by(Shift.shift_name).all()
    return render_template('admin/shifts.html', shifts=all_shifts)


@bp.route('/shifts/add', methods=['GET', 'POST'])
@admin_required
def add_shift():
    form = ShiftForm()
    if form.validate_on_submit():
        if Shift.query.filter_by(shift_name=form.shift_name.data).first():
            flash('Shift name already exists.', 'danger')
            return render_template('admin/shift_form.html', form=form, title='Add Shift')
        shift = Shift(
            shift_name=form.shift_name.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            grace_period_mins=form.grace_period_mins.data,
            min_working_hours=form.min_working_hours.data,
            late_mark_after_mins=form.late_mark_after_mins.data,
            overtime_eligible=form.overtime_eligible.data,
            is_active=form.is_active.data
        )
        db.session.add(shift)
        from flask_login import current_user
        log_audit(current_user.id, 'CREATE', 'Shift', None, f'Created shift {shift.shift_name}')
        db.session.commit()
        flash(f'Shift "{shift.shift_name}" created.', 'success')
        return redirect(url_for('admin.shifts'))
    return render_template('admin/shift_form.html', form=form, title='Add Shift')


@bp.route('/shifts/<int:shift_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_shift(shift_id):
    shift = Shift.query.get_or_404(shift_id)
    form = ShiftForm(obj=shift)
    if form.validate_on_submit():
        existing = Shift.query.filter(Shift.shift_name == form.shift_name.data, Shift.id != shift.id).first()
        if existing:
            flash('Shift name already taken.', 'danger')
            return render_template('admin/shift_form.html', form=form, title='Edit Shift', shift=shift)
        shift.shift_name = form.shift_name.data
        shift.start_time = form.start_time.data
        shift.end_time = form.end_time.data
        shift.grace_period_mins = form.grace_period_mins.data
        shift.min_working_hours = form.min_working_hours.data
        shift.late_mark_after_mins = form.late_mark_after_mins.data
        shift.overtime_eligible = form.overtime_eligible.data
        shift.is_active = form.is_active.data
        from flask_login import current_user
        log_audit(current_user.id, 'UPDATE', 'Shift', shift.id, f'Updated shift {shift.shift_name}')
        db.session.commit()
        flash(f'Shift "{shift.shift_name}" updated.', 'success')
        return redirect(url_for('admin.shifts'))
    return render_template('admin/shift_form.html', form=form, title='Edit Shift', shift=shift)


# ===========================================================================
# AUDIT LOG VIEWER (NEW)
# ===========================================================================
@bp.route('/audit-logs')
@admin_required
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('admin/audit_logs.html', logs=logs)


# ===========================================================================
# PM OVERVIEW (Admin as PM Lead)
# ===========================================================================
@bp.route('/pm-overview')
@admin_required
def pm_overview():
    """Admin PM overview — all projects grouped by assigned PM."""
    from datetime import date as date_cls
    all_projects = Project.query.order_by(Project.assigned_pm, Project.created_at.desc()).all()

    # Group projects by PM
    pm_groups = {}  # pm_user -> [projects]
    unassigned = []
    for p in all_projects:
        if p.assigned_pm:
            pm_user = User.query.get(p.assigned_pm)
            if pm_user not in pm_groups:
                pm_groups[pm_user] = []
            pm_groups[pm_user].append(p)
        else:
            unassigned.append(p)

    # Build stats per PM
    pm_stats = []
    for pm_user, projects in pm_groups.items():
        total_tasks = sum(p.tasks.count() for p in projects)
        pending = sum(p.tasks.filter_by(status='Pending').count() for p in projects)
        in_progress = sum(p.tasks.filter_by(status='In Progress').count() for p in projects)
        done = sum(p.tasks.filter_by(status='Done').count() for p in projects)
        overdue = sum(p.tasks.filter(Task.due_date < db.func.current_date(), Task.status != 'Done').count() for p in projects)
        team_count = len(set(
            m.user_id for p in projects for m in p.members
        ))
        pm_stats.append({
            'pm': pm_user,
            'projects': projects,
            'total_tasks': total_tasks,
            'pending': pending,
            'in_progress': in_progress,
            'done': done,
            'overdue': overdue,
            'team_count': team_count,
        })

    # Summary stats
    total = len(all_projects)
    active = sum(1 for p in all_projects if p.status == 'In Progress')
    completed = sum(1 for p in all_projects if p.status == 'Completed')
    delayed = sum(1 for p in all_projects if p.is_delayed)

    return render_template('admin/pm_overview.html',
                           pm_stats=pm_stats,
                           unassigned_projects=unassigned,
                           total_projects=total,
                           active_projects=active,
                           completed_projects=completed,
                           delayed_projects=delayed)


# ===========================================================================
# TIMESHEET MANAGEMENT (Admin Override)
# ===========================================================================
@bp.route('/timesheets')
@admin_required
def timesheets():
    """Global timesheet report — all entries, all projects."""
    status_filter = request.args.get('status', '')
    project_filter = request.args.get('project', type=int)
    employee_filter = request.args.get('employee', type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Timesheet.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if project_filter:
        query = query.filter_by(project_id=project_filter)
    if employee_filter:
        query = query.filter_by(employee_id=employee_filter)
    if date_from:
        try:
            from datetime import datetime
            query = query.filter(Timesheet.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to:
        try:
            from datetime import datetime
            query = query.filter(Timesheet.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    records = query.order_by(Timesheet.date.desc()).limit(500).all()
    projects = Project.query.order_by(Project.name).all()
    employees = Employee.query.order_by(Employee.emp_code).all()

    total_hours = round(sum(r.hours_worked for r in records), 2)
    approved_hours = round(sum(r.hours_worked for r in records if r.status == 'Approved'), 2)

    return render_template('admin/timesheets.html', records=records,
                           projects=projects, employees=employees,
                           selected_status=status_filter,
                           selected_project=project_filter,
                           selected_employee=employee_filter,
                           date_from=date_from, date_to=date_to,
                           total_hours=total_hours,
                           approved_hours=approved_hours)


@bp.route('/timesheets/<int:ts_id>/force-approve', methods=['POST'])
@admin_required
def force_approve_timesheet(ts_id):
    """Admin overrides: force-approve a timesheet."""
    from datetime import datetime
    ts = Timesheet.query.get_or_404(ts_id)

    if ts.status == 'Approved':
        flash('Timesheet is already approved.', 'warning')
        return redirect(url_for('admin.timesheets'))

    old_status = ts.status
    ts.status = 'Approved'
    ts.approved_by = session.get('user_id') or 1
    ts.approved_at = datetime.utcnow()

    # Auto-sync task hours
    if ts.task_id:
        task = Task.query.get(ts.task_id)
        if task:
            task.actual_hours = (task.actual_hours or 0) + ts.hours_worked

    from flask_login import current_user
    log_audit(current_user.id, 'FORCE_APPROVE', 'Timesheet', ts.id,
              f'Admin force-approved (was {old_status}): {ts.hours_worked}h emp#{ts.employee_id}')

    # Notify employee and PM
    notif = Notification(user_id=ts.employee.user_id,
                        title='Timesheet Force-Approved',
                        message=f'Admin force-approved your timesheet for {ts.date.strftime("%d %b %Y")} ({ts.hours_worked}h).',
                        category='success', link='/employee/timesheets')
    db.session.add(notif)
    if ts.project.assigned_pm:
        pm_notif = Notification(user_id=ts.project.assigned_pm,
                               title='Admin Override: Timesheet Approved',
                               message=f'Admin force-approved timesheet #{ts.id} for {ts.employee_name}.',
                               category='info', link='/pm/timesheet-approvals')
        db.session.add(pm_notif)

    db.session.commit()
    flash(f'Timesheet #{ts.id} force-approved by Admin.', 'success')
    return redirect(url_for('admin.timesheets'))


@bp.route('/timesheets/<int:ts_id>/force-reject', methods=['POST'])
@admin_required
def force_reject_timesheet(ts_id):
    """Admin overrides: force-reject a timesheet."""
    ts = Timesheet.query.get_or_404(ts_id)
    reason = request.form.get('rejection_reason', 'Admin override').strip()

    old_status = ts.status

    # If it was previously Approved, reverse the hour sync
    if old_status == 'Approved' and ts.task_id:
        task = Task.query.get(ts.task_id)
        if task:
            task.actual_hours = max(0, (task.actual_hours or 0) - ts.hours_worked)

    ts.status = 'Rejected'
    ts.rejection_reason = reason

    from flask_login import current_user
    log_audit(current_user.id, 'FORCE_REJECT', 'Timesheet', ts.id,
              f'Admin force-rejected (was {old_status}): {reason}')

    notif = Notification(user_id=ts.employee.user_id,
                        title='Timesheet Force-Rejected',
                        message=f'Admin rejected your timesheet for {ts.date.strftime("%d %b %Y")}: {reason}',
                        category='danger', link='/employee/timesheets')
    db.session.add(notif)

    db.session.commit()
    flash(f'Timesheet #{ts.id} force-rejected.', 'warning')
    return redirect(url_for('admin.timesheets'))


@bp.route('/timesheets/export')
@admin_required
def export_timesheets():
    """Export timesheets as CSV or Excel."""
    import csv
    import io
    from flask import Response

    fmt = request.args.get('format', 'csv')  # csv or xlsx
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Timesheet.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if date_from:
        try:
            from datetime import datetime
            query = query.filter(Timesheet.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to:
        try:
            from datetime import datetime
            query = query.filter(Timesheet.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    records = query.order_by(Timesheet.date.desc()).all()

    headers = ['ID', 'Employee Code', 'Employee Name', 'Date', 'Project',
               'Task', 'Hours', 'Description', 'Status', 'Approved By', 'Approved At']

    rows = []
    for r in records:
        rows.append([
            r.id,
            r.employee.emp_code,
            r.employee_name,
            r.date.strftime('%Y-%m-%d'),
            r.project_name,
            r.task_title,
            r.hours_worked,
            r.description,
            r.status,
            r.approver.full_name if r.approver else '',
            r.approved_at.strftime('%Y-%m-%d %H:%M') if r.approved_at else ''
        ])

    if fmt == 'xlsx':
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Timesheets'
            ws.append(headers)
            for row in rows:
                ws.append(row)
            # Style header
            for cell in ws[1]:
                cell.font = openpyxl.styles.Font(bold=True)
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            return Response(
                output.getvalue(),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': 'attachment; filename=timesheets_export.xlsx'}
            )
        except ImportError:
            flash('Excel export requires openpyxl. Falling back to CSV.', 'warning')
            # Fall through to CSV

    # CSV export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=timesheets_export.csv'}
    )
