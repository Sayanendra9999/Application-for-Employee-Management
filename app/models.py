"""SQLAlchemy models for the Enterprise Portal."""

from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db


# ---------------------------------------------------------------------------
# Association table: User ↔ Module (many-to-many)
# ---------------------------------------------------------------------------
class UserModule(db.Model):
    __tablename__ = 'user_modules'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'module_id', name='uq_user_module'),)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), default='')
    is_admin = db.Column(db.Boolean, default=False)
    is_active_user = db.Column(db.Boolean, default=True)
    must_change_password = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    modules = db.relationship('Module', secondary='user_modules', backref=db.backref('users', lazy='dynamic'))
    employee = db.relationship('Employee', backref='user', uselist=False, lazy='joined')
    tasks_assigned = db.relationship('Task', backref='assignee', foreign_keys='Task.assigned_to')
    expenses = db.relationship('Expense', backref='submitter', foreign_keys='Expense.submitted_by')
    projects_created = db.relationship('Project', backref='creator', foreign_keys='Project.created_by')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_module(self, slug):
        """Check if user has access to a module by slug."""
        return any(m.slug == slug for m in self.modules)

    @property
    def is_active(self):
        return self.is_active_user

    def __repr__(self):
        return f'<User {self.username}>'


# ---------------------------------------------------------------------------
# Module (represents an app module: admin, hr, pm, finance, employee)
# ---------------------------------------------------------------------------
class Module(db.Model):
    __tablename__ = 'modules'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), default='')
    icon = db.Column(db.String(50), default='fas fa-cube')

    def __repr__(self):
        return f'<Module {self.slug}>'


# ===========================================================================
# ADMIN CONFIG TABLES — Admin defines, HR consumes
# ===========================================================================

# ---------------------------------------------------------------------------
# Department (Admin-managed)
# ---------------------------------------------------------------------------
class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.String(250), default='')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    designations = db.relationship('Designation', backref='department', lazy='dynamic')
    employees = db.relationship('Employee', backref='department', lazy='dynamic')

    def __repr__(self):
        return f'<Department {self.code}>'


# ---------------------------------------------------------------------------
# Designation (Admin-managed, linked to Department)
# ---------------------------------------------------------------------------
class Designation(db.Model):
    __tablename__ = 'designations'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False)
    level = db.Column(db.Integer, default=1)          # 1=Junior, 2=Mid, 3=Senior, 4=Lead, 5=Head
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employees = db.relationship('Employee', backref='designation', lazy='dynamic')

    __table_args__ = (db.UniqueConstraint('title', 'department_id', name='uq_title_dept'),)

    def __repr__(self):
        return f'<Designation {self.title}>'


# ---------------------------------------------------------------------------
# LeavePolicy (Admin-managed — defines leave types and quotas)
# ---------------------------------------------------------------------------
class LeavePolicy(db.Model):
    __tablename__ = 'leave_policies'

    id = db.Column(db.Integer, primary_key=True)
    leave_type = db.Column(db.String(50), unique=True, nullable=False)    # Casual, Sick, Earned, etc.
    total_days = db.Column(db.Integer, nullable=False, default=12)
    carry_forward = db.Column(db.Boolean, default=False)
    max_carry_days = db.Column(db.Integer, default=0)
    description = db.Column(db.String(250), default='')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<LeavePolicy {self.leave_type} ({self.total_days}d)>'


# ---------------------------------------------------------------------------
# AttendanceRule (Admin-managed — single config row)
# ---------------------------------------------------------------------------
class AttendanceRule(db.Model):
    __tablename__ = 'attendance_rules'

    id = db.Column(db.Integer, primary_key=True)
    work_start = db.Column(db.String(5), default='09:00')    # HH:MM
    work_end = db.Column(db.String(5), default='18:00')
    late_threshold_mins = db.Column(db.Integer, default=15)   # Minutes after work_start to mark "Late"
    half_day_hours = db.Column(db.Float, default=4.0)         # Min hours for half-day
    full_day_hours = db.Column(db.Float, default=8.0)         # Min hours for full-day
    is_active = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<AttendanceRule {self.work_start}-{self.work_end}>'


# ---------------------------------------------------------------------------
# AuditLog (tracks changes across the system)
# ---------------------------------------------------------------------------
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)         # CREATE, UPDATE, DELETE, APPROVE, REJECT
    entity_type = db.Column(db.String(50), nullable=False)    # Employee, Leave, Attendance, etc.
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, default='')
    ip_address = db.Column(db.String(45), default='')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='audit_logs')

    def __repr__(self):
        return f'<AuditLog {self.action} {self.entity_type}#{self.entity_id}>'


# ===========================================================================
# HR MODULE MODELS
# ===========================================================================

# ---------------------------------------------------------------------------
# Employee (extends User with HR-specific fields) — UPGRADED
# ---------------------------------------------------------------------------
class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    emp_code = db.Column(db.String(20), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    designation_id = db.Column(db.Integer, db.ForeignKey('designations.id'), nullable=True)
    date_of_joining = db.Column(db.Date, default=date.today)
    salary = db.Column(db.Float, default=0.0)
    bank_account = db.Column(db.String(30), default='')
    pan_number = db.Column(db.String(15), default='')
    is_active = db.Column(db.Boolean, default=True)

    # relationships
    leaves = db.relationship('Leave', backref='employee', lazy='dynamic')
    attendance_records = db.relationship('Attendance', backref='employee', lazy='dynamic')
    salary_records = db.relationship('SalaryRecord', backref='employee', lazy='dynamic')
    leave_balances = db.relationship('LeaveBalance', backref='employee', lazy='dynamic')
    documents = db.relationship('EmployeeDocument', backref='employee', lazy='dynamic')
    payroll_inputs = db.relationship('PayrollInput', backref='employee', lazy='dynamic')

    @property
    def department_name(self):
        return self.department.name if self.department else 'Unassigned'

    @property
    def designation_title(self):
        return self.designation.title if self.designation else 'Unassigned'

    def __repr__(self):
        return f'<Employee {self.emp_code}>'


# ---------------------------------------------------------------------------
# Leave
# ---------------------------------------------------------------------------
class Leave(db.Model):
    __tablename__ = 'leaves'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    leave_type = db.Column(db.String(30), nullable=False)          # Casual, Sick, Earned
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='Pending')           # Pending, Approved, Rejected
    reason = db.Column(db.Text, default='')
    rejection_reason = db.Column(db.Text, default='')
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    approver = db.relationship('User', foreign_keys=[approved_by])

    def calc_days(self):
        """Calculate number of leave days (excluding weekends)."""
        if not self.start_date or not self.end_date:
            return 0
        count = 0
        current = self.start_date
        from datetime import timedelta
        while current <= self.end_date:
            if current.weekday() < 5:  # Mon-Fri
                count += 1
            current += timedelta(days=1)
        return count

    def __repr__(self):
        return f'<Leave {self.id} – {self.status}>'


# ---------------------------------------------------------------------------
# LeaveBalance (per employee per leave type)
# ---------------------------------------------------------------------------
class LeaveBalance(db.Model):
    __tablename__ = 'leave_balances'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)
    total_allocated = db.Column(db.Integer, default=0)
    used = db.Column(db.Integer, default=0)
    year = db.Column(db.Integer, nullable=False)

    __table_args__ = (db.UniqueConstraint('employee_id', 'leave_type', 'year', name='uq_emp_leave_year'),)

    @property
    def remaining(self):
        return max(0, self.total_allocated - self.used)

    def __repr__(self):
        return f'<LeaveBalance {self.leave_type}: {self.remaining} left>'


# ---------------------------------------------------------------------------
# Attendance — UPGRADED
# ---------------------------------------------------------------------------
class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.String(10), default='')     # stored as HH:MM string for SQLite compat
    check_out = db.Column(db.String(10), default='')
    working_hours = db.Column(db.Float, default=0.0)     # Calculated hours
    status = db.Column(db.String(20), default='Present')  # Present, Absent, Half-Day, Late
    notes = db.Column(db.String(250), default='')

    __table_args__ = (db.UniqueConstraint('employee_id', 'date', name='uq_emp_date'),)

    def calc_working_hours(self):
        """Calculate hours between check_in and check_out."""
        if not self.check_in or not self.check_out:
            return 0.0
        try:
            h1, m1 = map(int, self.check_in.split(':'))
            h2, m2 = map(int, self.check_out.split(':'))
            total_mins = (h2 * 60 + m2) - (h1 * 60 + m1)
            return round(max(0, total_mins / 60), 2)
        except (ValueError, AttributeError):
            return 0.0

    def __repr__(self):
        return f'<Attendance {self.employee_id} {self.date}>'


# ===========================================================================
# PROJECT MANAGEMENT MODELS — UPGRADED
# ===========================================================================

# ---------------------------------------------------------------------------
# Project — UPGRADED with lifecycle, deadline, unique name, progress
# ---------------------------------------------------------------------------
class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)   # prevent duplicates
    description = db.Column(db.Text, default='')
    start_date = db.Column(db.Date, default=date.today)
    end_date = db.Column(db.Date, nullable=True)
    deadline = db.Column(db.Date, nullable=True)                     # NEW — hard deadline
    status = db.Column(db.String(30), default='Not Started')         # Not Started, In Progress, Completed, On Hold
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = db.relationship('ProjectMember', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    milestones = db.relationship('Milestone', backref='project', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def progress(self):
        """Calculate project progress (%) based on completed tasks."""
        total = self.tasks.count()
        if total == 0:
            return 0
        done = self.tasks.filter_by(status='Done').count()
        return round((done / total) * 100)

    @property
    def is_delayed(self):
        """Check if project is past deadline but not completed."""
        if self.deadline and self.status != 'Completed':
            return date.today() > self.deadline
        return False

    def __repr__(self):
        return f'<Project {self.name}>'


# ---------------------------------------------------------------------------
# ProjectMember — UPGRADED with expanded project roles
# ---------------------------------------------------------------------------
class ProjectMember(db.Model):
    __tablename__ = 'project_members'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.String(50), default='Developer')  # Developer, Tester, Designer, Lead, Observer
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='project_memberships')
    __table_args__ = (db.UniqueConstraint('project_id', 'user_id', name='uq_project_user'),)

    def __repr__(self):
        return f'<ProjectMember P{self.project_id} U{self.user_id}>'


# ---------------------------------------------------------------------------
# Task — UPGRADED with updated_at tracking
# ---------------------------------------------------------------------------
class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    priority = db.Column(db.String(20), default='Medium')    # Low, Medium, High, Critical
    status = db.Column(db.String(20), default='Pending')     # Pending, In Progress, Done
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Task {self.title}>'


# ---------------------------------------------------------------------------
# Milestone — NEW
# ---------------------------------------------------------------------------
class Milestone(db.Model):
    __tablename__ = 'milestones'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    deadline = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(30), default='Pending')     # Pending, In Progress, Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('project_id', 'title', name='uq_project_milestone'),)

    @property
    def is_overdue(self):
        if self.deadline and self.status != 'Completed':
            return date.today() > self.deadline
        return False

    def __repr__(self):
        return f'<Milestone {self.title}>'


# ---------------------------------------------------------------------------
# Notification — NEW (system notifications for PM events)
# ---------------------------------------------------------------------------
class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, default='')
    category = db.Column(db.String(30), default='info')       # info, success, warning, danger
    is_read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(500), default='')               # optional URL to relevant page
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='notifications')

    def __repr__(self):
        return f'<Notification {self.title} for user#{self.user_id}>'


# ===========================================================================
# FINANCE MODELS (unchanged)
# ===========================================================================

# ---------------------------------------------------------------------------
# Expense
# ---------------------------------------------------------------------------
class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(60), nullable=False)      # Travel, Software, Office, Marketing
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=date.today)
    description = db.Column(db.Text, default='')
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending')     # Pending, Approved, Rejected

    def __repr__(self):
        return f'<Expense {self.category} ₹{self.amount}>'


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------
class Invoice(db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(30), unique=True, nullable=False)
    client_name = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    issue_date = db.Column(db.Date, default=date.today)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='Unpaid')      # Unpaid, Paid, Overdue, Cancelled
    description = db.Column(db.Text, default='')

    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'


# ---------------------------------------------------------------------------
# SalaryRecord
# ---------------------------------------------------------------------------
class SalaryRecord(db.Model):
    __tablename__ = 'salary_records'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    month = db.Column(db.String(20), nullable=False)         # e.g. "January"
    year = db.Column(db.Integer, nullable=False)
    basic = db.Column(db.Float, default=0.0)
    hra = db.Column(db.Float, default=0.0)
    deductions = db.Column(db.Float, default=0.0)
    net_salary = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Pending')     # Pending, Processed, Paid

    __table_args__ = (db.UniqueConstraint('employee_id', 'month', 'year', name='uq_emp_month_year'),)

    def __repr__(self):
        return f'<SalaryRecord {self.employee_id} {self.month}/{self.year}>'


# ===========================================================================
# BATCH 2 STUBS (models ready, routes in Batch 2)
# ===========================================================================

# ---------------------------------------------------------------------------
# PayrollInput (HR → Finance bridge)
# ---------------------------------------------------------------------------
class PayrollInput(db.Model):
    __tablename__ = 'payroll_inputs'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    month = db.Column(db.String(20), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    working_days = db.Column(db.Integer, default=0)
    present_days = db.Column(db.Integer, default=0)
    leaves_taken = db.Column(db.Integer, default=0)
    overtime_hours = db.Column(db.Float, default=0.0)
    bonus = db.Column(db.Float, default=0.0)
    deduction_notes = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='Draft')       # Draft, Submitted
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submitter = db.relationship('User', foreign_keys=[submitted_by])

    __table_args__ = (db.UniqueConstraint('employee_id', 'month', 'year', name='uq_payroll_emp_month_year'),)

    def __repr__(self):
        return f'<PayrollInput {self.employee_id} {self.month}/{self.year}>'


# ---------------------------------------------------------------------------
# EmployeeDocument
# ---------------------------------------------------------------------------
class EmployeeDocument(db.Model):
    __tablename__ = 'employee_documents'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    doc_type = db.Column(db.String(50), nullable=False)      # ID Proof, Offer Letter, Resume, etc.
    filename = db.Column(db.String(250), nullable=False)
    original_name = db.Column(db.String(250), default='')
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploader = db.relationship('User', foreign_keys=[uploaded_by])

    def __repr__(self):
        return f'<EmployeeDocument {self.doc_type} for emp#{self.employee_id}>'


# ---------------------------------------------------------------------------
# JobPosting (Recruitment — Batch 2)
# ---------------------------------------------------------------------------
class JobPosting(db.Model):
    __tablename__ = 'job_postings'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    designation_id = db.Column(db.Integer, db.ForeignKey('designations.id'), nullable=True)
    description = db.Column(db.Text, default='')
    requirements = db.Column(db.Text, default='')
    vacancies = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='Open')        # Open, Closed, On Hold
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by])
    department = db.relationship('Department', foreign_keys=[department_id])
    designation = db.relationship('Designation', foreign_keys=[designation_id])
    candidates = db.relationship('Candidate', backref='job', lazy='dynamic')

    def __repr__(self):
        return f'<JobPosting {self.title}>'


# ---------------------------------------------------------------------------
# Candidate (Recruitment — Batch 2)
# ---------------------------------------------------------------------------
class Candidate(db.Model):
    __tablename__ = 'candidates'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_postings.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), default='')
    resume_file = db.Column(db.String(250), default='')
    status = db.Column(db.String(30), default='Applied')     # Applied, Screening, Interview, Offer, Hired, Rejected
    notes = db.Column(db.Text, default='')
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

    interviews = db.relationship('Interview', backref='candidate', lazy='dynamic')

    def __repr__(self):
        return f'<Candidate {self.name}>'


# ---------------------------------------------------------------------------
# Interview (Recruitment — Batch 2)
# ---------------------------------------------------------------------------
class Interview(db.Model):
    __tablename__ = 'interviews'

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    interviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    duration_mins = db.Column(db.Integer, default=60)
    interview_type = db.Column(db.String(30), default='Technical')  # Technical, HR, Managerial
    rating = db.Column(db.Integer, nullable=True)                   # 1-5
    feedback = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='Scheduled')          # Scheduled, Completed, Cancelled

    interviewer = db.relationship('User', foreign_keys=[interviewer_id])

    def __repr__(self):
        return f'<Interview #{self.id} for candidate#{self.candidate_id}>'


# ---------------------------------------------------------------------------
# PerformanceReview (Batch 2)
# ---------------------------------------------------------------------------
class PerformanceReview(db.Model):
    __tablename__ = 'performance_reviews'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    review_period = db.Column(db.String(30), nullable=False)        # Q1-2026, Annual-2025, etc.
    rating = db.Column(db.Integer, default=3)                       # 1-5
    strengths = db.Column(db.Text, default='')
    improvements = db.Column(db.Text, default='')
    comments = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='Draft')              # Draft, Submitted, Acknowledged
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship('Employee', backref='performance_reviews')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id])

    def __repr__(self):
        return f'<PerformanceReview {self.review_period} emp#{self.employee_id}>'


# ===========================================================================
# EMPLOYEE SELF-SERVICE MODELS
# ===========================================================================

# ---------------------------------------------------------------------------
# ProfileUpdateRequest — Employee submits profile changes for HR approval
# ---------------------------------------------------------------------------
class ProfileUpdateRequest(db.Model):
    __tablename__ = 'profile_update_requests'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    field_name = db.Column(db.String(50), nullable=False)       # phone, bank_account, pan_number, emergency_contact
    old_value = db.Column(db.String(250), default='')
    new_value = db.Column(db.String(250), nullable=False)
    status = db.Column(db.String(20), default='Pending')        # Pending, Approved, Rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    employee = db.relationship('Employee', backref=db.backref('profile_update_requests', lazy='dynamic'))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

    def __repr__(self):
        return f'<ProfileUpdateRequest {self.field_name} emp#{self.employee_id} {self.status}>'


# ---------------------------------------------------------------------------
# EmployeeExpense — Employee submits expense/reimbursement claims
# ---------------------------------------------------------------------------
class EmployeeExpense(db.Model):
    __tablename__ = 'employee_expenses'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    category = db.Column(db.String(60), nullable=False)         # Travel, Medical, Software, Food, Other
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=date.today)
    description = db.Column(db.Text, default='')
    receipt_filename = db.Column(db.String(250), default='')
    receipt_original = db.Column(db.String(250), default='')
    status = db.Column(db.String(20), default='Pending')        # Pending, Approved, Rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship('Employee', backref=db.backref('expense_claims', lazy='dynamic'))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

    def __repr__(self):
        return f'<EmployeeExpense {self.category} ₹{self.amount} emp#{self.employee_id}>'
