"""HR routes — Employee management, Attendance, Leave management.

All operations consume Admin-configured rules via the services layer.
"""

from datetime import date, datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user
from app.hr import bp
from app.decorators import module_required
from app.extensions import db
from app.models import (Employee, User, Leave, Attendance, LeaveBalance,
                        LeavePolicy, Department, Designation)
from app.hr.forms import (EmployeeForm, LeaveActionForm, CheckInOutForm,
                          AttendanceFilterForm)
from app.hr import services


# ===========================================================================
# DASHBOARD
# ===========================================================================
@bp.route('/')
@module_required('hr')
def dashboard():
    total_employees = Employee.query.count()
    pending_leaves = Leave.query.filter_by(status='Pending').count()
    approved_leaves = Leave.query.filter_by(status='Approved').count()

    # Today's attendance
    today = date.today()
    today_records = Attendance.query.filter_by(date=today).all()
    today_present = sum(1 for r in today_records if r.status in ('Present', 'Late'))
    today_late = sum(1 for r in today_records if r.status == 'Late')
    today_absent = total_employees - len(today_records) if total_employees > 0 else 0

    # Department breakdown
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    dept_stats = []
    for dept in departments:
        count = dept.employees.count()
        if count > 0:
            dept_stats.append({'name': dept.name, 'count': count})

    recent_leaves = Leave.query.order_by(Leave.created_at.desc()).limit(5).all()
    rules = services.get_attendance_rules()

    return render_template('hr/dashboard.html',
                           total_employees=total_employees,
                           pending_leaves=pending_leaves,
                           approved_leaves=approved_leaves,
                           today_present=today_present,
                           today_late=today_late,
                           today_absent=today_absent,
                           dept_stats=dept_stats,
                           recent_leaves=recent_leaves,
                           rules=rules)


# ===========================================================================
# EMPLOYEE MANAGEMENT
# ===========================================================================
@bp.route('/employees')
@module_required('hr')
def employees():
    # Optional department filter
    dept_id = request.args.get('department', type=int)
    search = request.args.get('search', '').strip()

    query = Employee.query
    if dept_id:
        query = query.filter_by(department_id=dept_id)
    if search:
        query = query.join(User).filter(
            db.or_(
                User.full_name.ilike(f'%{search}%'),
                Employee.emp_code.ilike(f'%{search}%')
            )
        )

    all_employees = query.order_by(Employee.emp_code).all()
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    return render_template('hr/employees.html', employees=all_employees,
                           departments=departments, selected_dept=dept_id, search=search)


@bp.route('/employees/add', methods=['GET', 'POST'])
@module_required('hr')
def add_employee():
    form = EmployeeForm()
    form.department_id.choices = [(0, '— Select Department —')] + services.get_departments_for_dropdown()
    form.designation_id.choices = [(0, '— Select Designation —')] + services.get_designations_for_dropdown()

    # Get users without an employee profile
    users_without_profile = User.query.filter(
        ~User.id.in_(db.session.query(Employee.user_id))
    ).order_by(User.full_name).all()

    if form.validate_on_submit():
        user_id = request.form.get('user_id')
        if not user_id:
            flash('Please select a user.', 'danger')
            return render_template('hr/employee_form.html', form=form,
                                   users=users_without_profile, title='Add Employee')
        if Employee.query.filter_by(emp_code=form.emp_code.data).first():
            flash('Employee code already exists.', 'danger')
            return render_template('hr/employee_form.html', form=form,
                                   users=users_without_profile, title='Add Employee')

        emp = Employee(
            user_id=int(user_id),
            emp_code=form.emp_code.data,
            department_id=form.department_id.data if form.department_id.data != 0 else None,
            designation_id=form.designation_id.data if form.designation_id.data != 0 else None,
            date_of_joining=form.date_of_joining.data,
            salary=form.salary.data or 0,
            bank_account=form.bank_account.data or '',
            pan_number=form.pan_number.data or ''
        )
        db.session.add(emp)
        db.session.flush()

        # Initialize leave balances from Admin policies
        services.initialize_leave_balances(emp.id)

        services.log_audit(current_user.id, 'CREATE', 'Employee', emp.id,
                          f'Created employee {emp.emp_code}', request.remote_addr or '')
        db.session.commit()
        flash(f'Employee {emp.emp_code} created with leave balances initialized.', 'success')
        return redirect(url_for('hr.employees'))
    return render_template('hr/employee_form.html', form=form,
                           users=users_without_profile, title='Add Employee')


@bp.route('/employees/<int:emp_id>/edit', methods=['GET', 'POST'])
@module_required('hr')
def edit_employee(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    form = EmployeeForm(obj=emp)
    form.department_id.choices = [(0, '— Select Department —')] + services.get_departments_for_dropdown()
    form.designation_id.choices = [(0, '— Select Designation —')] + services.get_designations_for_dropdown()

    if form.validate_on_submit():
        existing = Employee.query.filter(Employee.emp_code == form.emp_code.data,
                                         Employee.id != emp.id).first()
        if existing:
            flash('Employee code already taken.', 'danger')
            return render_template('hr/employee_form.html', form=form,
                                   title='Edit Employee', employee=emp)
        emp.emp_code = form.emp_code.data
        emp.department_id = form.department_id.data if form.department_id.data != 0 else None
        emp.designation_id = form.designation_id.data if form.designation_id.data != 0 else None
        emp.date_of_joining = form.date_of_joining.data
        emp.salary = form.salary.data or 0
        emp.bank_account = form.bank_account.data or ''
        emp.pan_number = form.pan_number.data or ''

        services.log_audit(current_user.id, 'UPDATE', 'Employee', emp.id,
                          f'Updated employee {emp.emp_code}', request.remote_addr or '')
        db.session.commit()
        flash(f'Employee {emp.emp_code} updated.', 'success')
        return redirect(url_for('hr.employees'))
    return render_template('hr/employee_form.html', form=form, title='Edit Employee', employee=emp)


@bp.route('/employees/<int:emp_id>')
@module_required('hr')
def employee_detail(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    leave_balances = services.get_all_leave_balances(emp.id)
    recent_attendance = Attendance.query.filter_by(employee_id=emp.id)\
        .order_by(Attendance.date.desc()).limit(10).all()
    recent_leaves = Leave.query.filter_by(employee_id=emp.id)\
        .order_by(Leave.created_at.desc()).limit(5).all()
    return render_template('hr/employee_detail.html', employee=emp,
                           leave_balances=leave_balances,
                           recent_attendance=recent_attendance,
                           recent_leaves=recent_leaves)


# API: Get designations for a department (dynamic dropdown)
@bp.route('/api/designations/<int:dept_id>')
@module_required('hr')
def api_designations(dept_id):
    desigs = services.get_designations_for_department(dept_id)
    return jsonify(desigs)


# ===========================================================================
# ATTENDANCE MANAGEMENT
# ===========================================================================
@bp.route('/attendance')
@module_required('hr')
def attendance():
    # Filters
    dept_id = request.args.get('department', type=int)
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Attendance.query.join(Employee)
    if dept_id:
        query = query.filter(Employee.department_id == dept_id)
    if status_filter:
        query = query.filter(Attendance.status == status_filter)
    if date_from:
        try:
            query = query.filter(Attendance.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(Attendance.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    records = query.order_by(Attendance.date.desc()).limit(200).all()
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    rules = services.get_attendance_rules()

    return render_template('hr/attendance.html', records=records,
                           departments=departments, rules=rules,
                           selected_dept=dept_id, selected_status=status_filter,
                           date_from=date_from, date_to=date_to)


@bp.route('/attendance/check-in', methods=['GET', 'POST'])
@module_required('hr')
def attendance_checkin():
    form = CheckInOutForm()
    employees = Employee.query.order_by(Employee.emp_code).all()
    form.employee_id.choices = [(0, '— Select Employee —')] + [
        (e.id, f'{e.emp_code} — {e.user.full_name}') for e in employees
    ]

    today_records = {a.employee_id: a for a in Attendance.query.filter_by(date=date.today()).all()}

    if form.validate_on_submit():
        emp_id = form.employee_id.data
        if emp_id == 0:
            flash('Please select an employee.', 'danger')
        else:
            action = request.form.get('action', 'checkin')
            if action == 'checkout':
                success, msg = services.perform_checkout(emp_id, form.time.data)
            else:
                success, msg = services.perform_checkin(emp_id, form.time.data)

            if success:
                services.log_audit(current_user.id, action.upper(), 'Attendance', emp_id,
                                  msg, request.remote_addr or '')
                db.session.commit()
                flash(msg, 'success')
            else:
                flash(msg, 'danger')
        return redirect(url_for('hr.attendance_checkin'))

    return render_template('hr/attendance_checkin.html', form=form,
                           today_records=today_records, employees=employees)


@bp.route('/attendance/report')
@module_required('hr')
def attendance_report():
    """Monthly attendance summary report."""
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)

    employees = Employee.query.order_by(Employee.emp_code).all()
    report = []
    for emp in employees:
        summary = services.get_attendance_summary(emp.id, year, month)
        summary['employee'] = emp
        report.append(summary)

    return render_template('hr/attendance_report.html', report=report,
                           year=year, month=month)


# ===========================================================================
# LEAVE MANAGEMENT
# ===========================================================================
@bp.route('/leaves')
@module_required('hr')
def leaves():
    status_filter = request.args.get('status', '')
    query = Leave.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    all_leaves = query.order_by(Leave.created_at.desc()).all()
    return render_template('hr/leaves.html', leaves=all_leaves,
                           selected_status=status_filter)


@bp.route('/leaves/<int:leave_id>/action', methods=['POST'])
@module_required('hr')
def leave_action(leave_id):
    form = LeaveActionForm()
    if form.validate_on_submit():
        if form.status.data == 'Approved':
            success, msg = services.approve_leave(leave_id, current_user.id)
        else:
            success, msg = services.reject_leave(leave_id, current_user.id,
                                                  form.rejection_reason.data or '')

        if success:
            services.log_audit(current_user.id, form.status.data.upper(), 'Leave', leave_id,
                              msg, request.remote_addr or '')
            db.session.commit()
            flash(msg, 'success')
        else:
            flash(msg, 'danger')
    return redirect(url_for('hr.leaves'))


@bp.route('/leave-balances')
@module_required('hr')
def leave_balances():
    """Overview of all employees' leave balances."""
    year = request.args.get('year', date.today().year, type=int)
    employees = Employee.query.order_by(Employee.emp_code).all()
    policies = LeavePolicy.query.filter_by(is_active=True).order_by(LeavePolicy.leave_type).all()

    balance_data = []
    for emp in employees:
        balances = services.get_all_leave_balances(emp.id, year)
        bal_map = {b.leave_type: b for b in balances}
        balance_data.append({
            'employee': emp,
            'balances': bal_map
        })

    return render_template('hr/leave_balances.html', balance_data=balance_data,
                           policies=policies, year=year)
