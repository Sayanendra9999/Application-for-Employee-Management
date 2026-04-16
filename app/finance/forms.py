"""Finance forms."""

from flask_wtf import FlaskForm
from wtforms import (StringField, FloatField, DateField, SelectField,
                     TextAreaField, IntegerField, SubmitField)
from wtforms.validators import DataRequired, Optional, Length


class ExpenseForm(FlaskForm):
    category = SelectField('Category', choices=[
        ('Travel', 'Travel'), ('Software', 'Software'),
        ('Office Supplies', 'Office Supplies'), ('Marketing', 'Marketing'),
        ('Utilities', 'Utilities'), ('Other', 'Other')
    ], validators=[DataRequired()])
    amount = FloatField('Amount (₹)', validators=[DataRequired()])
    date = DateField('Date', validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Save Expense')


class InvoiceForm(FlaskForm):
    invoice_number = StringField('Invoice Number', validators=[DataRequired(), Length(2, 30)])
    client_name = StringField('Client Name', validators=[DataRequired(), Length(2, 150)])
    amount = FloatField('Amount (₹)', validators=[DataRequired()])
    issue_date = DateField('Issue Date', validators=[Optional()])
    due_date = DateField('Due Date', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('Unpaid', 'Unpaid'), ('Paid', 'Paid'),
        ('Overdue', 'Overdue'), ('Cancelled', 'Cancelled')
    ])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Save Invoice')


class SalaryForm(FlaskForm):
    month = SelectField('Month', choices=[
        ('January', 'January'), ('February', 'February'), ('March', 'March'),
        ('April', 'April'), ('May', 'May'), ('June', 'June'),
        ('July', 'July'), ('August', 'August'), ('September', 'September'),
        ('October', 'October'), ('November', 'November'), ('December', 'December')
    ], validators=[DataRequired()])
    year = IntegerField('Year', validators=[DataRequired()])
    basic = FloatField('Basic Pay (₹)', validators=[DataRequired()])
    hra = FloatField('HRA (₹)', validators=[Optional()])
    deductions = FloatField('Deductions (₹)', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('Pending', 'Pending'), ('Processed', 'Processed'), ('Paid', 'Paid')
    ])
    submit = SubmitField('Save Record')
