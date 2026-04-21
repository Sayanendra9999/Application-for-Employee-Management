"""Employee forms — expanded for self-service portal."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, DateField, SelectField, TextAreaField,
                     FloatField, SubmitField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class ProfileForm(FlaskForm):
    """Basic profile update (direct fields)."""
    full_name = StringField('Full Name', validators=[DataRequired(), Length(2, 150)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Update Profile')


class ProfileUpdateRequestForm(FlaskForm):
    """Request update for sensitive fields (needs HR approval)."""
    field_name = SelectField('Field to Update', choices=[
        ('bank_account', 'Bank Account Number'),
        ('pan_number', 'PAN Number'),
    ], validators=[DataRequired()])
    new_value = StringField('New Value', validators=[DataRequired(), Length(2, 250)])
    submit = SubmitField('Submit Request')


class LeaveRequestForm(FlaskForm):
    """Leave request form."""
    leave_type = SelectField('Leave Type', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    reason = TextAreaField('Reason', validators=[Optional(), Length(max=500)])
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
