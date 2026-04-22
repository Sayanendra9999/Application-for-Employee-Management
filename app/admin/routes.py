"""Admin routes — user CRUD, module assignment, HR configuration."""

import secrets
import string
from flask import render_template, redirect, url_for, flash, request, session
from app.admin import bp
from app.decorators import admin_required
from app.extensions import db
from app.models import (User, Module, UserModule, Employee, Project, Task,
                        Milestone, Notification,
                        Department, Designation, LeavePolicy, AttendanceRule, AuditLog)
from app.admin.forms import UserCreateForm, UserEditForm, ModuleAssignForm
from app.admin.config_forms import (DepartmentForm, DesignationForm,
                                     LeavePolicyForm, AttendanceRuleForm)


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
    active_projects = Project.query.filter_by(status='In Progress').count()
    completed_projects = Project.query.filter_by(status='Completed').count()
    total_tasks = Task.query.count()
    pending_tasks = Task.query.filter_by(status='Pending').count()
    total_milestones = Milestone.query.count()
    total_notifications = Notification.query.count()
    total_departments = Department.query.count()
    total_designations = Designation.query.count()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    # Count unassigned employees for onboarding visibility
    from app.hr import services as hr_services
    unassigned_employees = hr_services.get_unassigned_count()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           active_users=active_users,
                           total_modules=total_modules,
                           total_employees=total_employees,
                           total_projects=total_projects,
                           active_projects=active_projects,
                           completed_projects=completed_projects,
                           total_tasks=total_tasks,
                           pending_tasks=pending_tasks,
                           total_milestones=total_milestones,
                           total_notifications=total_notifications,
                           total_departments=total_departments,
                           total_designations=total_designations,
                           recent_users=recent_users,
                           unassigned_employees=unassigned_employees)


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
# LEAVE POLICY MANAGEMENT (NEW)
# ===========================================================================
@bp.route('/leave-policies')
@admin_required
def leave_policies():
    policies = LeavePolicy.query.order_by(LeavePolicy.leave_type).all()
    return render_template('admin/leave_policies.html', policies=policies)


@bp.route('/leave-policies/add', methods=['GET', 'POST'])
@admin_required
def add_leave_policy():
    form = LeavePolicyForm()
    if form.validate_on_submit():
        if LeavePolicy.query.filter_by(leave_type=form.leave_type.data).first():
            flash('Leave type already exists.', 'danger')
            return render_template('admin/leave_policy_form.html', form=form, title='Add Leave Policy')
        policy = LeavePolicy(
            leave_type=form.leave_type.data, total_days=form.total_days.data,
            carry_forward=form.carry_forward.data,
            max_carry_days=form.max_carry_days.data or 0,
            description=form.description.data or '', is_active=form.is_active.data
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
    if form.validate_on_submit():
        policy.leave_type = form.leave_type.data
        policy.total_days = form.total_days.data
        policy.carry_forward = form.carry_forward.data
        policy.max_carry_days = form.max_carry_days.data or 0
        policy.description = form.description.data or ''
        policy.is_active = form.is_active.data
        from flask_login import current_user
        log_audit(current_user.id, 'UPDATE', 'LeavePolicy', policy.id, f'Updated policy {policy.leave_type}')
        db.session.commit()
        flash(f'Leave policy "{policy.leave_type}" updated.', 'success')
        return redirect(url_for('admin.leave_policies'))
    return render_template('admin/leave_policy_form.html', form=form, title='Edit Leave Policy', policy=policy)


# ===========================================================================
# ATTENDANCE RULES (NEW — single config)
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
# AUDIT LOG VIEWER (NEW)
# ===========================================================================
@bp.route('/audit-logs')
@admin_required
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('admin/audit_logs.html', logs=logs)
