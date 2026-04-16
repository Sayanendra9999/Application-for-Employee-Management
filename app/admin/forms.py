"""Admin forms."""

from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, SubmitField,
                     SelectMultipleField, widgets)
from wtforms.validators import DataRequired, Email, Length, Optional


class MultiCheckboxField(SelectMultipleField):
    """Renders a list of checkboxes."""
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class UserCreateForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(2, 150)])
    phone = StringField('Phone', validators=[Optional(), Length(0, 20)])
    is_admin = BooleanField('Admin Privileges')
    modules = MultiCheckboxField('Assign Modules', coerce=int)
    submit = SubmitField('Create User')


class UserEditForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(2, 150)])
    phone = StringField('Phone', validators=[Optional(), Length(0, 20)])
    password = PasswordField('New Password (leave blank to keep current)', validators=[Optional(), Length(6, 128)])
    is_admin = BooleanField('Admin Privileges')
    is_active = BooleanField('Active')
    modules = MultiCheckboxField('Assign Modules', coerce=int)
    submit = SubmitField('Update User')


class ModuleAssignForm(FlaskForm):
    modules = MultiCheckboxField('Modules', coerce=int)
    submit = SubmitField('Save Permissions')
