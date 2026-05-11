"""Employee forms — expanded for self-service portal."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, DateField, SelectField, TextAreaField,
                     FloatField, SubmitField, BooleanField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class ProfileUpdateBatchForm(FlaskForm):
    """Batch request update for all profile fields (needs HR approval)."""
    full_name = StringField('Full Name', validators=[Optional(), Length(2, 150)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    bank_account = StringField('Bank Account Number', validators=[Optional(), Length(max=30)])
    pan_number = StringField('PAN Number', validators=[Optional(), Length(max=15)])
    aadhar_number = StringField('Aadhar Number', validators=[Optional(), Length(max=20)])
    location = StringField('Location', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Submit Update Request')


class LeaveRequestForm(FlaskForm):
    """Leave request form."""
    leave_type = SelectField('Leave Type', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    reason = TextAreaField('Reason', validators=[Optional(), Length(max=500)])
    is_urgent = BooleanField('Mark as Urgent (skip manager, direct HR review)')
    submit = SubmitField('Submit Request')


class ExpenseClaimForm(FlaskForm):
    """Expense/reimbursement claim form."""
    category = SelectField('Category', choices=[
        ('Travel', 'Travel'),
        ('Medical', 'Medical'),
        ('Software', 'Software / Tools'),
        ('Food', 'Food / Meals'),
        ('Office Supplies', 'Office Supplies'),
        ('Training', 'Training / Courses'),
        ('Other', 'Other'),
    ], validators=[DataRequired()])
    amount = FloatField('Amount (₹)', validators=[
        DataRequired(), NumberRange(min=1, max=500000, message='Amount must be ₹1 — ₹5,00,000')
    ])
    date = DateField('Expense Date', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired(), Length(5, 500)])
    receipt = FileField('Upload Receipt', validators=[
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF, JPG, PNG files allowed')
    ])
    submit = SubmitField('Submit Claim')


class TimesheetForm(FlaskForm):
    """Timesheet submission form — log hours against a project/task."""
    project_id = SelectField('Project', coerce=int, validators=[DataRequired()])
    task_id = SelectField('Task (Optional)', coerce=int, validators=[Optional()])
    date = DateField('Date', validators=[DataRequired()])
    hours_worked = FloatField('Hours Worked', validators=[
        DataRequired(), NumberRange(min=0.25, max=24, message='Hours must be between 0.25 and 24')
    ])
    description = TextAreaField('Work Description', validators=[DataRequired(), Length(5, 1000)])
    submit = SubmitField('Submit Timesheet')
