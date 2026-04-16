"""Admin configuration forms — Departments, Designations, Leave Policies, Attendance Rules."""

from flask_wtf import FlaskForm
from wtforms import (StringField, IntegerField, BooleanField, FloatField,
                     SelectField, TextAreaField, SubmitField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class DepartmentForm(FlaskForm):
    name = StringField('Department Name', validators=[DataRequired(), Length(2, 100)])
    code = StringField('Department Code', validators=[DataRequired(), Length(2, 20)])
    description = TextAreaField('Description', validators=[Optional(), Length(0, 250)])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Department')


class DesignationForm(FlaskForm):
    title = StringField('Designation Title', validators=[DataRequired(), Length(2, 100)])
    department_id = SelectField('Department', coerce=int, validators=[DataRequired()])
    level = SelectField('Level', coerce=int, choices=[
        (1, 'Junior'), (2, 'Mid-Level'), (3, 'Senior'),
        (4, 'Lead'), (5, 'Head/Manager')
    ], default=1)
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Designation')


class LeavePolicyForm(FlaskForm):
    leave_type = StringField('Leave Type', validators=[DataRequired(), Length(2, 50)])
    total_days = IntegerField('Total Days per Year', validators=[DataRequired(), NumberRange(1, 365)])
    carry_forward = BooleanField('Allow Carry Forward', default=False)
    max_carry_days = IntegerField('Max Carry Forward Days', validators=[Optional()], default=0)
    description = TextAreaField('Description', validators=[Optional(), Length(0, 250)])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Policy')


class AttendanceRuleForm(FlaskForm):
    work_start = StringField('Work Start Time (HH:MM)', validators=[DataRequired(), Length(5, 5)],
                             default='09:00')
    work_end = StringField('Work End Time (HH:MM)', validators=[DataRequired(), Length(5, 5)],
                           default='18:00')
    late_threshold_mins = IntegerField('Late Threshold (minutes)',
                                       validators=[DataRequired(), NumberRange(1, 120)], default=15)
    half_day_hours = FloatField('Half Day Hours', validators=[DataRequired()], default=4.0)
    full_day_hours = FloatField('Full Day Hours', validators=[DataRequired()], default=8.0)
    submit = SubmitField('Save Rules')
