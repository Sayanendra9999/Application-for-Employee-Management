"""Employee forms."""

from flask_wtf import FlaskForm
from wtforms import (StringField, DateField, SelectField, TextAreaField,
                     SubmitField)
from wtforms.validators import DataRequired, Optional


class LeaveRequestForm(FlaskForm):
    leave_type = SelectField('Leave Type', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    reason = TextAreaField('Reason', validators=[Optional()])
    submit = SubmitField('Submit Request')


class ProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    phone = StringField('Phone', validators=[Optional()])
    submit = SubmitField('Update Profile')
