"""HR routes — Employee management, Attendance, Leave, Performance,
Recruitment, Payroll Input, Document management.

All operations consume Admin-configured rules via the services layer.
"""

import os
from datetime import date, datetime
from flask import (render_template, redirect, url_for, flash, request,
                   jsonify, current_app, send_from_directory)
from flask_login import current_user
from app.hr import bp
from app.decorators import module_required
from app.extensions import db
from app.models import (Employee, User, Leave, Attendance, LeaveBalance,
                        LeavePolicy, Department, Designation,
                        PerformanceReview, PayrollInput, EmployeeDocument,
                        JobPosting, Candidate, Interview,
                        Shift, CompOff, ShiftSwapRequest, Timesheet)
from app.hr.forms import (EmployeeForm, LeaveActionForm, CheckInOutForm,
                          AttendanceFilterForm, AttendanceOverrideForm,
                          PerformanceReviewForm,
                          JobPostingForm, CandidateForm, InterviewForm,
                          InterviewFeedbackForm, PayrollInputForm,
                          PayrollGenerateForm, DocumentUploadForm)
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
    unassigned_count = services.get_unassigned_count()
    pending_swaps = ShiftSwapRequest.query.filter_by(status='Pending').count()
    pending_comp_offs = CompOff.query.filter_by(status='Earned').count()
    total_shifts = Shift.query.filter_by(is_active=True).count()

    # Timesheet stats for HR
    total_timesheets = Timesheet.query.count()
    pending_timesheets = Timesheet.query.filter_by(status='Pending').count()
    approved_ts_hours = db.session.query(db.func.coalesce(db.func.sum(Timesheet.hours_worked), 0)).filter_by(status='Approved').scalar()

    return render_template('hr/dashboard.html',
                           total_employees=total_employees,
                           pending_leaves=pending_leaves,
                           approved_leaves=approved_leaves,
                           today_present=today_present,
                           today_late=today_late,
                           today_absent=today_absent,
                           dept_stats=dept_stats,
                           recent_leaves=recent_leaves,
                           rules=rules,
                           unassigned_count=unassigned_count,
                           pending_swaps=pending_swaps,
                           pending_comp_offs=pending_comp_offs,
                           total_shifts=total_shifts,
                           total_timesheets=total_timesheets,
                           pending_timesheets=pending_timesheets,
                           approved_ts_hours=round(approved_ts_hours, 1))


# ===========================================================================
# EMPLOYEE MANAGEMENT
# ===========================================================================
@bp.route('/employees')
@module_required('hr')
def employees():
    # Optional department filter
    dept_id = request.args.get('department', type=int)
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()

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

    # Apply status filter in-memory (no schema change)
    if status_filter == 'unassigned':
        all_employees = [e for e in all_employees if not services.is_employee_profile_complete(e)]
    elif status_filter == 'assigned':
        all_employees = [e for e in all_employees if services.is_employee_profile_complete(e)]

    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    unassigned_count = services.get_unassigned_count()
    return render_template('hr/employees.html', employees=all_employees,
                           departments=departments, selected_dept=dept_id,
                           search=search, status_filter=status_filter,
                           unassigned_count=unassigned_count,
                           is_profile_complete=services.is_employee_profile_complete)


@bp.route('/employees/<int:emp_id>/edit', methods=['GET', 'POST'])
@module_required('hr')
def edit_employee(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    form = EmployeeForm(obj=emp)
    form.department_id.choices = [(0, '— Select Department —')] + services.get_departments_for_dropdown()
    form.designation_id.choices = [(0, '— Select Designation —')] + services.get_designations_for_dropdown()
    form.shift_id.choices = [(0, '— General Shift —')] + services.get_shifts_for_dropdown()

    if request.method == 'GET':
        form.shift_id.data = emp.shift_id or 0

    if form.validate_on_submit():
        # emp_code is system-assigned by Admin and immutable — not updated here
        emp.department_id = form.department_id.data if form.department_id.data != 0 else None
        emp.designation_id = form.designation_id.data if form.designation_id.data != 0 else None
        emp.shift_id = form.shift_id.data if form.shift_id.data != 0 else None
        emp.date_of_joining = form.date_of_joining.data
        emp.salary = form.salary.data or 0
        emp.bank_account = form.bank_account.data or ''
        emp.pan_number = form.pan_number.data or ''

        # Reinitialize leave balances if designation changed (role-based policies)
        services.initialize_leave_balances(emp.id)

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
# UNASSIGNED EMPLOYEES / ONBOARDING
# ===========================================================================
@bp.route('/employees/unassigned')
@module_required('hr')
def unassigned_employees():
    """List employees with incomplete profiles awaiting HR onboarding."""
    unassigned = services.get_unassigned_employees()
    # Attach missing field info to each employee for template use
    emp_info = []
    for emp in unassigned:
        emp_info.append({
            'employee': emp,
            'missing': services.get_missing_fields(emp)
        })
    return render_template('hr/unassigned_employees.html',
                           emp_info=emp_info,
                           unassigned_count=len(unassigned))


@bp.route('/employees/<int:emp_id>/complete-profile', methods=['GET', 'POST'])
@module_required('hr')
def complete_profile(emp_id):
    """HR fills in missing details for an unassigned employee."""
    emp = Employee.query.get_or_404(emp_id)
    form = EmployeeForm(obj=emp)
    form.department_id.choices = [(0, '— Select Department —')] + services.get_departments_for_dropdown()
    form.designation_id.choices = [(0, '— Select Designation —')] + services.get_designations_for_dropdown()
    form.shift_id.choices = [(0, '— General Shift —')] + services.get_shifts_for_dropdown()

    missing = services.get_missing_fields(emp)

    if form.validate_on_submit():
        success, msg = services.complete_employee_profile(
            emp,
            department_id=form.department_id.data,
            designation_id=form.designation_id.data,
            salary=form.salary.data,
            bank_account=form.bank_account.data,
            pan_number=form.pan_number.data,
            date_of_joining=form.date_of_joining.data
        )
        if success:
            # emp_code is system-assigned by Admin — not modified here

            # Initialize leave balances if not already done
            services.initialize_leave_balances(emp.id)

            services.log_audit(current_user.id, 'COMPLETE_PROFILE', 'Employee', emp.id,
                              f'Completed profile for {emp.emp_code}', request.remote_addr or '')
            db.session.commit()
            flash(msg, 'success')
            return redirect(url_for('hr.employee_detail', emp_id=emp.id))
        else:
            flash(msg, 'danger')

    return render_template('hr/complete_profile.html', form=form,
                           employee=emp, missing=missing,
                           title='Complete Employee Profile')


@bp.route('/api/employee/<int:emp_id>/profile-status')
@module_required('hr')
def api_profile_status(emp_id):
    """API: Check if an employee's profile is complete."""
    emp = Employee.query.get(emp_id)
    if not emp:
        return jsonify({'error': 'Employee not found'}), 404
    complete = services.is_employee_profile_complete(emp)
    missing = services.get_missing_fields(emp) if not complete else []
    return jsonify({
        'employee_id': emp.id,
        'emp_code': emp.emp_code,
        'is_complete': complete,
        'missing_fields': missing
    })


# ===========================================================================
# ATTENDANCE MANAGEMENT
# ===========================================================================
@bp.route('/api/attendance')
@module_required('hr')
def api_attendance():
    """API for real-time attendance search by employee ID/name."""
    emp_query = request.args.get('employee_id', '').strip()
    
    query = Employee.query.join(User)
    if emp_query:
        query = query.filter(
            db.or_(
                Employee.emp_code.ilike(f'%{emp_query}%'),
                User.full_name.ilike(f'%{emp_query}%')
            )
        )
    
    employees = query.order_by(Employee.emp_code).all()
    today_records = {a.employee_id: a for a in Attendance.query.filter_by(date=date.today()).all()}
    
    results = []
    for emp in employees:
        rec = today_records.get(emp.id)
        results.append({
            'emp_code': emp.emp_code,
            'full_name': emp.user.full_name,
            'check_in': rec.check_in.strftime('%H:%M:%S') if rec and rec.check_in else '—',
            'check_out': rec.check_out.strftime('%H:%M:%S') if rec and rec.check_out else '—',
            'working_hours': f'{rec.working_hours:.1f}h' if rec and rec.working_hours else '—',
            'status': rec.status if rec else 'Not Recorded'
        })
        
    return jsonify(results)


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


# ===========================================================================
# PERFORMANCE MANAGEMENT (Batch 2)
# ===========================================================================
@bp.route('/performance')
@module_required('hr')
def performance():
    period_filter = request.args.get('period', '')
    dept_filter = request.args.get('department', type=int)

    query = PerformanceReview.query
    if period_filter:
        query = query.filter_by(review_period=period_filter)
    if dept_filter:
        query = query.join(Employee).filter(Employee.department_id == dept_filter)

    reviews = query.order_by(PerformanceReview.created_at.desc()).all()
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    periods = services.get_review_periods()
    return render_template('hr/performance.html', reviews=reviews,
                           departments=departments, periods=periods,
                           selected_period=period_filter, selected_dept=dept_filter)


@bp.route('/performance/add', methods=['GET', 'POST'])
@module_required('hr')
def add_performance():
    form = PerformanceReviewForm()
    employees = Employee.query.order_by(Employee.emp_code).all()
    form.employee_id.choices = [(0, '— Select Employee —')] + [
        (e.id, f'{e.emp_code} — {e.user.full_name}') for e in employees
    ]
    form.review_period.choices = services.get_review_periods()

    if form.validate_on_submit():
        if form.employee_id.data == 0:
            flash('Please select an employee.', 'danger')
            return render_template('hr/performance_form.html', form=form, title='Add Review')
        review = PerformanceReview(
            employee_id=form.employee_id.data,
            reviewer_id=current_user.id,
            review_period=form.review_period.data,
            rating=form.rating.data,
            strengths=form.strengths.data or '',
            improvements=form.improvements.data or '',
            comments=form.comments.data or '',
            status='Submitted'
        )
        db.session.add(review)
        services.log_audit(current_user.id, 'CREATE', 'PerformanceReview', None,
                          f'Submitted review for emp#{review.employee_id}', request.remote_addr or '')
        db.session.commit()
        flash('Performance review submitted.', 'success')
        return redirect(url_for('hr.performance'))
    return render_template('hr/performance_form.html', form=form, title='Add Performance Review')


@bp.route('/performance/<int:review_id>')
@module_required('hr')
def performance_detail(review_id):
    review = PerformanceReview.query.get_or_404(review_id)
    return render_template('hr/performance_detail.html', review=review)


@bp.route('/performance/<int:review_id>/edit', methods=['GET', 'POST'])
@module_required('hr')
def edit_performance(review_id):
    review = PerformanceReview.query.get_or_404(review_id)
    form = PerformanceReviewForm(obj=review)
    employees = Employee.query.order_by(Employee.emp_code).all()
    form.employee_id.choices = [(e.id, f'{e.emp_code} — {e.user.full_name}') for e in employees]
    form.review_period.choices = services.get_review_periods()

    if form.validate_on_submit():
        review.employee_id = form.employee_id.data
        review.review_period = form.review_period.data
        review.rating = form.rating.data
        review.strengths = form.strengths.data or ''
        review.improvements = form.improvements.data or ''
        review.comments = form.comments.data or ''
        review.status = 'Submitted'
        services.log_audit(current_user.id, 'UPDATE', 'PerformanceReview', review.id,
                          f'Updated review for emp#{review.employee_id}', request.remote_addr or '')
        db.session.commit()
        flash('Performance review updated.', 'success')
        return redirect(url_for('hr.performance'))
    return render_template('hr/performance_form.html', form=form,
                           title='Edit Performance Review', review=review)


# ===========================================================================
# RECRUITMENT (Batch 2)
# ===========================================================================
@bp.route('/recruitment')
@module_required('hr')
def recruitment():
    status_filter = request.args.get('status', '')
    query = JobPosting.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    jobs = query.order_by(JobPosting.created_at.desc()).all()

    # Pipeline stats
    total_candidates = Candidate.query.count()
    pipeline = {}
    for status in ['Applied', 'Screening', 'Interview', 'Offer', 'Hired', 'Rejected']:
        pipeline[status] = Candidate.query.filter_by(status=status).count()

    return render_template('hr/recruitment.html', jobs=jobs, pipeline=pipeline,
                           total_candidates=total_candidates, selected_status=status_filter)


@bp.route('/recruitment/jobs/add', methods=['GET', 'POST'])
@module_required('hr')
def add_job():
    form = JobPostingForm()
    form.department_id.choices = [(0, '— Select —')] + services.get_departments_for_dropdown()
    form.designation_id.choices = [(0, '— Optional —')] + services.get_designations_for_dropdown()

    if form.validate_on_submit():
        job = JobPosting(
            title=form.title.data,
            department_id=form.department_id.data if form.department_id.data != 0 else None,
            designation_id=form.designation_id.data if form.designation_id.data != 0 else None,
            description=form.description.data or '',
            requirements=form.requirements.data or '',
            vacancies=form.vacancies.data,
            status=form.status.data,
            created_by=current_user.id
        )
        db.session.add(job)
        services.log_audit(current_user.id, 'CREATE', 'JobPosting', None,
                          f'Created job posting: {job.title}', request.remote_addr or '')
        db.session.commit()
        flash(f'Job posting "{job.title}" created.', 'success')
        return redirect(url_for('hr.recruitment'))
    return render_template('hr/job_form.html', form=form, title='Create Job Posting')


@bp.route('/recruitment/jobs/<int:job_id>')
@module_required('hr')
def job_detail(job_id):
    job = JobPosting.query.get_or_404(job_id)
    candidates = Candidate.query.filter_by(job_id=job.id).order_by(Candidate.applied_at.desc()).all()
    return render_template('hr/job_detail.html', job=job, candidates=candidates)


@bp.route('/recruitment/jobs/<int:job_id>/candidates/add', methods=['GET', 'POST'])
@module_required('hr')
def add_candidate(job_id):
    job = JobPosting.query.get_or_404(job_id)
    form = CandidateForm()

    if form.validate_on_submit():
        candidate = Candidate(
            job_id=job.id,
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data or '',
            status=form.status.data,
            notes=form.notes.data or ''
        )
        db.session.add(candidate)
        services.log_audit(current_user.id, 'CREATE', 'Candidate', None,
                          f'Added candidate {candidate.name} for {job.title}', request.remote_addr or '')
        db.session.commit()
        flash(f'Candidate "{candidate.name}" added.', 'success')
        return redirect(url_for('hr.job_detail', job_id=job.id))
    return render_template('hr/candidate_form.html', form=form, job=job, title='Add Candidate')


@bp.route('/recruitment/candidates/<int:candidate_id>/edit', methods=['GET', 'POST'])
@module_required('hr')
def edit_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    form = CandidateForm(obj=candidate)

    if form.validate_on_submit():
        old_status = candidate.status
        candidate.name = form.name.data
        candidate.email = form.email.data
        candidate.phone = form.phone.data or ''
        candidate.status = form.status.data
        candidate.notes = form.notes.data or ''
        services.log_audit(current_user.id, 'UPDATE', 'Candidate', candidate.id,
                          f'Status: {old_status} → {candidate.status}', request.remote_addr or '')
        db.session.commit()
        flash(f'Candidate "{candidate.name}" updated.', 'success')
        return redirect(url_for('hr.job_detail', job_id=candidate.job_id))
    return render_template('hr/candidate_form.html', form=form, job=candidate.job,
                           title='Edit Candidate', candidate=candidate)


@bp.route('/recruitment/candidates/<int:candidate_id>/interview', methods=['GET', 'POST'])
@module_required('hr')
def schedule_interview(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    form = InterviewForm()
    users = User.query.filter_by(is_active_user=True).order_by(User.full_name).all()
    form.interviewer_id.choices = [(0, '— Select —')] + [(u.id, u.full_name) for u in users]

    if form.validate_on_submit():
        # Combine date and time into a datetime
        scheduled_dt = datetime.combine(form.scheduled_date.data,
                                        datetime.strptime(form.scheduled_time.data, '%H:%M').time())
        interview = Interview(
            candidate_id=candidate.id,
            interviewer_id=form.interviewer_id.data,
            scheduled_at=scheduled_dt,
            duration_mins=form.duration_mins.data,
            interview_type=form.interview_type.data,
            status='Scheduled'
        )
        db.session.add(interview)

        # Auto-update candidate status to Interview
        if candidate.status in ('Applied', 'Screening'):
            candidate.status = 'Interview'

        services.log_audit(current_user.id, 'CREATE', 'Interview', None,
                          f'Scheduled {interview.interview_type} for {candidate.name}',
                          request.remote_addr or '')
        db.session.commit()
        flash(f'Interview scheduled for {candidate.name}.', 'success')
        return redirect(url_for('hr.job_detail', job_id=candidate.job_id))
    return render_template('hr/interview_form.html', form=form, candidate=candidate,
                           title='Schedule Interview')


@bp.route('/recruitment/interviews/<int:interview_id>/feedback', methods=['GET', 'POST'])
@module_required('hr')
def interview_feedback(interview_id):
    interview = Interview.query.get_or_404(interview_id)
    form = InterviewFeedbackForm()

    if form.validate_on_submit():
        interview.rating = form.rating.data
        interview.feedback = form.feedback.data
        interview.status = 'Completed'
        services.log_audit(current_user.id, 'UPDATE', 'Interview', interview.id,
                          f'Feedback rating: {interview.rating}/5', request.remote_addr or '')
        db.session.commit()
        flash('Interview feedback submitted.', 'success')
        return redirect(url_for('hr.job_detail', job_id=interview.candidate.job_id))
    return render_template('hr/interview_feedback.html', form=form, interview=interview,
                           title='Interview Feedback')


# ===========================================================================
# PAYROLL INPUT (Batch 2)
# ===========================================================================
@bp.route('/payroll')
@module_required('hr')
def payroll():
    year = request.args.get('year', date.today().year, type=int)
    month_name = request.args.get('month', '')

    query = PayrollInput.query.filter_by(year=year)
    if month_name:
        query = query.filter_by(month=month_name)

    inputs = query.join(Employee).order_by(Employee.emp_code).all()
    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    return render_template('hr/payroll_input.html', inputs=inputs, year=year,
                           months=months, selected_month=month_name)


@bp.route('/payroll/generate', methods=['GET', 'POST'])
@module_required('hr')
def payroll_generate():
    form = PayrollGenerateForm()
    month_choices = [(i, m) for i, m in enumerate(
        ['', 'January', 'February', 'March', 'April', 'May', 'June',
         'July', 'August', 'September', 'October', 'November', 'December']
    ) if i > 0]
    form.month.choices = month_choices
    form.year.data = form.year.data or date.today().year

    if form.validate_on_submit():
        created, skipped = services.generate_payroll_inputs(form.year.data, form.month.data)
        services.log_audit(current_user.id, 'CREATE', 'PayrollInput', None,
                          f'Generated payroll: {created} created, {skipped} skipped',
                          request.remote_addr or '')
        db.session.commit()
        flash(f'Payroll inputs generated: {created} created, {skipped} already existed.', 'success')
        month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        return redirect(url_for('hr.payroll', year=form.year.data,
                                month=month_names[form.month.data]))
    return render_template('hr/payroll_generate.html', form=form, title='Generate Payroll Inputs')


@bp.route('/payroll/<int:payroll_id>/edit', methods=['GET', 'POST'])
@module_required('hr')
def payroll_edit(payroll_id):
    pi = PayrollInput.query.get_or_404(payroll_id)
    if pi.status == 'Submitted':
        flash('Cannot edit submitted payroll input.', 'danger')
        return redirect(url_for('hr.payroll'))

    form = PayrollInputForm(obj=pi)
    if form.validate_on_submit():
        pi.overtime_hours = form.overtime_hours.data or 0
        pi.bonus = form.bonus.data or 0
        pi.deduction_notes = form.deduction_notes.data or ''
        services.log_audit(current_user.id, 'UPDATE', 'PayrollInput', pi.id,
                          f'Updated payroll for emp#{pi.employee_id}', request.remote_addr or '')
        db.session.commit()
        flash('Payroll input updated.', 'success')
        return redirect(url_for('hr.payroll', year=pi.year, month=pi.month))
    return render_template('hr/payroll_form.html', form=form, payroll=pi,
                           title=f'Edit Payroll — {pi.employee.user.full_name}')


@bp.route('/payroll/submit', methods=['POST'])
@module_required('hr')
def payroll_submit():
    """Bulk submit all Draft payroll inputs for a month."""
    year = request.form.get('year', type=int)
    month = request.form.get('month', '')
    if not year or not month:
        flash('Invalid month/year.', 'danger')
        return redirect(url_for('hr.payroll'))

    drafts = PayrollInput.query.filter_by(year=year, month=month, status='Draft').all()
    count = 0
    for pi in drafts:
        pi.status = 'Submitted'
        pi.submitted_by = current_user.id
        count += 1

    if count > 0:
        services.log_audit(current_user.id, 'SUBMIT', 'PayrollInput', None,
                          f'Submitted {count} payroll inputs for {month} {year}',
                          request.remote_addr or '')
        db.session.commit()
        flash(f'{count} payroll inputs submitted to Finance.', 'success')
    else:
        flash('No draft payroll inputs to submit.', 'warning')
    return redirect(url_for('hr.payroll', year=year, month=month))


# ===========================================================================
# DOCUMENT MANAGEMENT (Batch 2)
# ===========================================================================
@bp.route('/documents')
@module_required('hr')
def documents():
    emp_filter = request.args.get('employee', type=int)
    query = EmployeeDocument.query
    if emp_filter:
        query = query.filter_by(employee_id=emp_filter)
    docs = query.order_by(EmployeeDocument.uploaded_at.desc()).all()
    employees = Employee.query.order_by(Employee.emp_code).all()
    return render_template('hr/documents.html', documents=docs, employees=employees,
                           selected_emp=emp_filter)


@bp.route('/documents/upload', methods=['GET', 'POST'])
@module_required('hr')
def document_upload():
    form = DocumentUploadForm()
    employees = Employee.query.order_by(Employee.emp_code).all()
    form.employee_id.choices = [(0, '— Select Employee —')] + [
        (e.id, f'{e.emp_code} — {e.user.full_name}') for e in employees
    ]

    if form.validate_on_submit():
        if form.employee_id.data == 0:
            flash('Please select an employee.', 'danger')
            return render_template('hr/document_upload.html', form=form, title='Upload Document')

        file = form.document.data
        emp = Employee.query.get(form.employee_id.data)
        if not emp:
            flash('Employee not found.', 'danger')
            return redirect(url_for('hr.documents'))

        # Ensure upload directory exists
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads/documents')
        os.makedirs(upload_folder, exist_ok=True)

        # Generate safe filename
        safe_name = services.generate_safe_filename(file.filename, emp.emp_code)
        filepath = os.path.join(upload_folder, safe_name)
        file.save(filepath)

        doc = EmployeeDocument(
            employee_id=emp.id,
            doc_type=form.doc_type.data,
            filename=safe_name,
            original_name=file.filename,
            uploaded_by=current_user.id
        )
        db.session.add(doc)
        services.log_audit(current_user.id, 'CREATE', 'EmployeeDocument', None,
                          f'Uploaded {form.doc_type.data} for {emp.emp_code}',
                          request.remote_addr or '')
        db.session.commit()
        flash(f'Document "{file.filename}" uploaded for {emp.emp_code}.', 'success')
        return redirect(url_for('hr.documents', employee=emp.id))
    return render_template('hr/document_upload.html', form=form, title='Upload Document')


@bp.route('/documents/<int:doc_id>/download')
@module_required('hr')
def document_download(doc_id):
    doc = EmployeeDocument.query.get_or_404(doc_id)
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads/documents')
    return send_from_directory(upload_folder, doc.filename,
                               as_attachment=True,
                               download_name=doc.original_name)


@bp.route('/documents/<int:doc_id>/delete', methods=['POST'])
@module_required('hr')
def document_delete(doc_id):
    doc = EmployeeDocument.query.get_or_404(doc_id)
    emp_id = doc.employee_id

    # Delete the file from disk
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads/documents')
    filepath = os.path.join(upload_folder, doc.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    services.log_audit(current_user.id, 'DELETE', 'EmployeeDocument', doc.id,
                      f'Deleted {doc.doc_type} ({doc.original_name})',
                      request.remote_addr or '')
    db.session.delete(doc)
    db.session.commit()
    flash('Document deleted.', 'warning')
    return redirect(url_for('hr.documents', employee=emp_id))


# ===========================================================================
# SHIFT SWAP REQUESTS (NEW)
# ===========================================================================
@bp.route('/shift-swaps')
@module_required('hr')
def shift_swaps():
    status_filter = request.args.get('status', '')
    query = ShiftSwapRequest.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    swaps = query.order_by(ShiftSwapRequest.created_at.desc()).all()
    return render_template('hr/shift_swap_requests.html', swaps=swaps,
                           selected_status=status_filter)


@bp.route('/shift-swaps/<int:swap_id>/approve', methods=['POST'])
@module_required('hr')
def approve_shift_swap(swap_id):
    success, msg = services.approve_shift_swap(swap_id, current_user.id)
    if success:
        services.log_audit(current_user.id, 'APPROVE', 'ShiftSwapRequest', swap_id,
                          msg, request.remote_addr or '')
        db.session.commit()
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('hr.shift_swaps'))


@bp.route('/shift-swaps/<int:swap_id>/reject', methods=['POST'])
@module_required('hr')
def reject_shift_swap(swap_id):
    success, msg = services.reject_shift_swap(swap_id, current_user.id)
    if success:
        services.log_audit(current_user.id, 'REJECT', 'ShiftSwapRequest', swap_id,
                          msg, request.remote_addr or '')
        db.session.commit()
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('hr.shift_swaps'))


# ===========================================================================
# COMP-OFF MANAGEMENT (NEW)
# ===========================================================================
@bp.route('/comp-offs')
@module_required('hr')
def comp_offs():
    status_filter = request.args.get('status', '')
    comps = services.get_comp_offs(status=status_filter or None)
    return render_template('hr/comp_offs.html', comp_offs=comps,
                           selected_status=status_filter)


@bp.route('/comp-offs/<int:comp_id>/approve', methods=['POST'])
@module_required('hr')
def approve_comp_off(comp_id):
    success, msg = services.approve_comp_off(comp_id, current_user.id)
    if success:
        services.log_audit(current_user.id, 'APPROVE', 'CompOff', comp_id,
                          msg, request.remote_addr or '')
        db.session.commit()
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('hr.comp_offs'))


# ===========================================================================
# ATTENDANCE OVERRIDE & AUTO-ABSENT (NEW)
# ===========================================================================
@bp.route('/attendance/override', methods=['GET', 'POST'])
@module_required('hr')
def attendance_override():
    form = AttendanceOverrideForm()
    employees = Employee.query.order_by(Employee.emp_code).all()
    form.employee_id.choices = [(0, '— Select Employee —')] + [
        (e.id, f'{e.emp_code} — {e.user.full_name}') for e in employees
    ]
    if form.validate_on_submit():
        if form.employee_id.data == 0:
            flash('Please select an employee.', 'danger')
        else:
            success, msg = services.override_attendance(
                form.employee_id.data, form.date.data,
                form.status.data, form.check_in.data or '',
                form.check_out.data or '', form.notes.data or ''
            )
            if success:
                services.log_audit(current_user.id, 'OVERRIDE', 'Attendance',
                                  form.employee_id.data, msg, request.remote_addr or '')
                db.session.commit()
                flash(msg, 'success')
            else:
                flash(msg, 'danger')
        return redirect(url_for('hr.attendance_override'))
    return render_template('hr/attendance_override.html', form=form)


@bp.route('/attendance/auto-absent', methods=['POST'])
@module_required('hr')
def run_auto_absent():
    """Manually trigger auto-absent marking for yesterday."""
    count = services.auto_mark_absent()
    if count > 0:
        services.log_audit(current_user.id, 'AUTO_ABSENT', 'Attendance', None,
                          f'Marked {count} employees absent', request.remote_addr or '')
        db.session.commit()
        flash(f'{count} employee(s) marked absent.', 'warning')
    else:
        flash('No employees to mark absent.', 'info')
    return redirect(url_for('hr.attendance'))


# ===========================================================================
# TIMESHEET MANAGEMENT (HR)
# ===========================================================================
@bp.route('/timesheets')
@module_required('hr')
def timesheets():
    """Organization-wide timesheet view with filters."""
    status_filter = request.args.get('status', '')
    dept_filter = request.args.get('department', type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Timesheet.query.join(Employee)
    if status_filter:
        query = query.filter(Timesheet.status == status_filter)
    if dept_filter:
        query = query.filter(Employee.department_id == dept_filter)
    if date_from:
        try:
            query = query.filter(Timesheet.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(Timesheet.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    records = query.order_by(Timesheet.date.desc()).limit(300).all()
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()

    # Summary stats
    total_hours = sum(r.hours_worked for r in records)
    approved_hours = sum(r.hours_worked for r in records if r.status == 'Approved')

    return render_template('hr/timesheets.html', records=records,
                           departments=departments,
                           selected_status=status_filter,
                           selected_dept=dept_filter,
                           date_from=date_from, date_to=date_to,
                           total_hours=round(total_hours, 2),
                           approved_hours=round(approved_hours, 2))


@bp.route('/timesheets/attendance-comparison')
@module_required('hr')
def timesheet_attendance_comparison():
    """Side-by-side: Attendance hours vs. Timesheet hours per employee."""
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)

    employees = Employee.query.order_by(Employee.emp_code).all()
    comparison = []

    for emp in employees:
        # Attendance hours this month
        att_summary = services.get_attendance_summary(emp.id, year, month)
        att_hours = att_summary.get('total_hours', 0)

        # Timesheet hours this month (approved)
        ts_entries = Timesheet.query.filter(
            Timesheet.employee_id == emp.id,
            Timesheet.status == 'Approved',
            db.extract('year', Timesheet.date) == year,
            db.extract('month', Timesheet.date) == month
        ).all()
        ts_hours = round(sum(e.hours_worked for e in ts_entries), 2)

        # Overtime flag: timesheet hours > attendance hours
        overtime_flag = ts_hours > att_hours if att_hours > 0 else False

        comparison.append({
            'employee': emp,
            'attendance_hours': round(att_hours, 2),
            'timesheet_hours': ts_hours,
            'difference': round(ts_hours - att_hours, 2),
            'overtime_flag': overtime_flag
        })

    return render_template('hr/timesheet_comparison.html',
                           comparison=comparison,
                           year=year, month=month)