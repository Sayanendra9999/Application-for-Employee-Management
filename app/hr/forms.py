"""HR forms — Employee, Attendance, Leave management."""

from flask_wtf import FlaskForm
from wtforms import (StringField, FloatField, DateField, SelectField,
                     TextAreaField, SubmitField, IntegerField)
from wtforms.validators import DataRequired, Optional, Length


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
