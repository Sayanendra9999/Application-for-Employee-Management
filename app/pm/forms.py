"""PM forms — Projects, Tasks, Milestones."""

from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, DateField, SelectField,
                     SubmitField, FloatField)
from wtforms.validators import DataRequired, Optional, Length


class ProjectForm(FlaskForm):
    name = StringField('Project Name', validators=[DataRequired(), Length(2, 150)])
    description = TextAreaField('Description', validators=[Optional()])
    start_date = DateField('Start Date', validators=[Optional()])
    end_date = DateField('End Date', validators=[Optional()])
    deadline = DateField('Deadline', validators=[Optional()])
    estimated_hours = FloatField('Estimated Hours', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('Not Started', 'Not Started'),
        ('In Progress', 'In Progress'),
        ('On Hold', 'On Hold'),
        ('Completed', 'Completed')
    ])
    assigned_pm = SelectField('Assign to Project Manager', coerce=int,
                              validators=[Optional()])
    submit = SubmitField('Save Project')


class TaskForm(FlaskForm):
    title = StringField('Task Title', validators=[DataRequired(), Length(2, 200)])
    description = TextAreaField('Description', validators=[Optional()])
    assigned_to = SelectField('Assign To', coerce=int, validators=[Optional()])
    priority = SelectField('Priority', choices=[
        ('Low', 'Low'), ('Medium', 'Medium'),
        ('High', 'High'), ('Critical', 'Critical')
    ])
    status = SelectField('Status', choices=[
        ('Pending', 'Pending'), ('In Progress', 'In Progress'), ('Done', 'Done')
    ])
    estimated_hours = FloatField('Estimated Hours', validators=[Optional()])
    due_date = DateField('Due Date', validators=[Optional()])
    submit = SubmitField('Save Task')


class MilestoneForm(FlaskForm):
    title = StringField('Milestone Title', validators=[DataRequired(), Length(2, 200)])
    description = TextAreaField('Description', validators=[Optional()])
    deadline = DateField('Deadline', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed')
    ])
    submit = SubmitField('Save Milestone')
