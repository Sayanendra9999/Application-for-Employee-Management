"""HR forms — Employee, Attendance, Leave, Performance, Recruitment, Payroll, Documents."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, FloatField, DateField, SelectField,
                     TextAreaField, SubmitField, IntegerField, DateTimeLocalField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange, Email


# ===========================================================================
# BATCH 1 FORMS (unchanged)
# ===========================================================================
class EmployeeForm(FlaskForm):
    emp_code = StringField('Employee Code', validators=[DataRequired(), Length(2, 20)])
    department_id = SelectField('Department', coerce=int, validators=[DataRequired()])
    designation_id = SelectField('Designation', coerce=int, validators=[DataRequired()])
    date_of_joining = DateField('Date of Joining', validators=[Optional()])
    salary = FloatField('Monthly Salary (₹)', validators=[Optional()])
    bank_account = StringField('Bank Account', validators=[Optional(), Length(0, 30)])
    pan_number = StringField('PAN Number', validators=[Optional(), Length(0, 15)])
    submit = SubmitField('Save')


class LeaveActionForm(FlaskForm):
    """Used by HR to approve/reject a leave request."""
    status = SelectField('Action', choices=[('Approved', 'Approve'), ('Rejected', 'Reject')],
                         validators=[DataRequired()])
    rejection_reason = TextAreaField('Reason (for rejection)', validators=[Optional(), Length(0, 500)])
    submit = SubmitField('Submit')


class CheckInOutForm(FlaskForm):
    """Used for manual check-in / check-out."""
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    time = StringField('Time (HH:MM)', validators=[DataRequired(), Length(5, 5)])
    submit = SubmitField('Submit')


class AttendanceFilterForm(FlaskForm):
    """Filter attendance records."""
    department_id = SelectField('Department', coerce=int, validators=[Optional()])
    status = SelectField('Status', choices=[
        ('', 'All'), ('Present', 'Present'), ('Late', 'Late'),
        ('Absent', 'Absent'), ('Half-Day', 'Half-Day')
    ], validators=[Optional()])
    date_from = DateField('From', validators=[Optional()])
    date_to = DateField('To', validators=[Optional()])
    submit = SubmitField('Filter')


class LeaveBalanceForm(FlaskForm):
    """Manually adjust leave balance."""
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    leave_type = SelectField('Leave Type', validators=[DataRequired()])
    adjustment = IntegerField('Adjustment (+/-)', validators=[DataRequired()])
    reason = StringField('Reason', validators=[Optional(), Length(0, 200)])
    submit = SubmitField('Apply Adjustment')


# ===========================================================================
# BATCH 2 — PERFORMANCE
# ===========================================================================
class PerformanceReviewForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    review_period = SelectField('Review Period', validators=[DataRequired()])
    rating = SelectField('Rating', coerce=int, choices=[
        (1, '1 — Poor'), (2, '2 — Below Average'), (3, '3 — Average'),
        (4, '4 — Good'), (5, '5 — Excellent')
    ], default=3, validators=[DataRequired()])
    strengths = TextAreaField('Strengths', validators=[Optional(), Length(0, 2000)])
    improvements = TextAreaField('Areas for Improvement', validators=[Optional(), Length(0, 2000)])
    comments = TextAreaField('Additional Comments', validators=[Optional(), Length(0, 2000)])
    submit = SubmitField('Save Review')


# ===========================================================================
# BATCH 2 — RECRUITMENT
# ===========================================================================
class JobPostingForm(FlaskForm):
    title = StringField('Job Title', validators=[DataRequired(), Length(3, 150)])
    department_id = SelectField('Department', coerce=int, validators=[DataRequired()])
    designation_id = SelectField('Designation', coerce=int, validators=[Optional()])
    description = TextAreaField('Job Description', validators=[Optional(), Length(0, 3000)])
    requirements = TextAreaField('Requirements', validators=[Optional(), Length(0, 3000)])
    vacancies = IntegerField('Number of Vacancies', validators=[DataRequired(), NumberRange(1, 50)], default=1)
    status = SelectField('Status', choices=[
        ('Open', 'Open'), ('On Hold', 'On Hold'), ('Closed', 'Closed')
    ], default='Open')
    submit = SubmitField('Save Job Posting')


class CandidateForm(FlaskForm):
    name = StringField('Candidate Name', validators=[DataRequired(), Length(2, 150)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(0, 120)])
    phone = StringField('Phone', validators=[Optional(), Length(0, 20)])
    status = SelectField('Status', choices=[
        ('Applied', 'Applied'), ('Screening', 'Screening'),
        ('Interview', 'Interview'), ('Offer', 'Offer'),
        ('Hired', 'Hired'), ('Rejected', 'Rejected')
    ], default='Applied')
    notes = TextAreaField('Notes', validators=[Optional(), Length(0, 2000)])
    submit = SubmitField('Save Candidate')


class InterviewForm(FlaskForm):
    interviewer_id = SelectField('Interviewer', coerce=int, validators=[DataRequired()])
    scheduled_date = DateField('Date', validators=[DataRequired()])
    scheduled_time = StringField('Time (HH:MM)', validators=[DataRequired(), Length(5, 5)])
    duration_mins = IntegerField('Duration (minutes)', validators=[DataRequired()], default=60)
    interview_type = SelectField('Type', choices=[
        ('Technical', 'Technical'), ('HR', 'HR'),
        ('Managerial', 'Managerial'), ('Culture Fit', 'Culture Fit')
    ], default='Technical')
    submit = SubmitField('Schedule Interview')


class InterviewFeedbackForm(FlaskForm):
    rating = SelectField('Rating', coerce=int, choices=[
        (1, '1 — Poor'), (2, '2 — Below Average'), (3, '3 — Average'),
        (4, '4 — Good'), (5, '5 — Excellent')
    ], validators=[DataRequired()])
    feedback = TextAreaField('Feedback', validators=[DataRequired(), Length(5, 2000)])
    submit = SubmitField('Submit Feedback')


# ===========================================================================
# BATCH 2 — PAYROLL INPUT
# ===========================================================================
class PayrollInputForm(FlaskForm):
    overtime_hours = FloatField('Overtime Hours', validators=[Optional()], default=0)
    bonus = FloatField('Bonus (₹)', validators=[Optional()], default=0)
    deduction_notes = TextAreaField('Deduction Notes', validators=[Optional(), Length(0, 500)])
    submit = SubmitField('Save')


class PayrollGenerateForm(FlaskForm):
    month = SelectField('Month', coerce=int, validators=[DataRequired()])
    year = IntegerField('Year', validators=[DataRequired(), NumberRange(2020, 2030)])
    submit = SubmitField('Generate Payroll Inputs')


# ===========================================================================
# BATCH 2 — DOCUMENT MANAGEMENT
# ===========================================================================
class DocumentUploadForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    doc_type = SelectField('Document Type', choices=[
        ('ID Proof', 'ID Proof'), ('PAN Card', 'PAN Card'),
        ('Aadhar Card', 'Aadhar Card'), ('Offer Letter', 'Offer Letter'),
        ('Appointment Letter', 'Appointment Letter'),
        ('Resume', 'Resume'), ('Certificate', 'Certificate'),
        ('Relieving Letter', 'Relieving Letter'), ('Other', 'Other')
    ], validators=[DataRequired()])
    document = FileField('Upload File', validators=[
        DataRequired(),
        FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'txt', 'xlsx', 'xls'],
                     'Only PDF, DOC, Image, TXT, and Excel files are allowed.')
    ])
    submit = SubmitField('Upload Document')
