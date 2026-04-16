"""Finance routes — salaries, expenses, invoices."""

from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.finance import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Expense, Invoice, SalaryRecord, Employee
from app.finance.forms import ExpenseForm, InvoiceForm, SalaryForm


@bp.route('/')
@module_required('finance')
def dashboard():
    total_expenses = db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0)).scalar()
    pending_expenses = Expense.query.filter_by(status='Pending').count()
    total_invoiced = db.session.query(db.func.coalesce(db.func.sum(Invoice.amount), 0)).scalar()
    unpaid_invoices = Invoice.query.filter_by(status='Unpaid').count()
    total_salary_paid = db.session.query(
        db.func.coalesce(db.func.sum(SalaryRecord.net_salary), 0)
    ).filter(SalaryRecord.status == 'Paid').scalar()
    recent_expenses = Expense.query.order_by(Expense.date.desc()).limit(5).all()
    recent_invoices = Invoice.query.order_by(Invoice.issue_date.desc()).limit(5).all()
    return render_template('finance/dashboard.html',
                           total_expenses=total_expenses,
                           pending_expenses=pending_expenses,
                           total_invoiced=total_invoiced,
                           unpaid_invoices=unpaid_invoices,
                           total_salary_paid=total_salary_paid,
                           recent_expenses=recent_expenses,
                           recent_invoices=recent_invoices)


# ── Expenses ─────────────────────────────────────────────────────────────────
@bp.route('/expenses')
@module_required('finance')
def expenses():
    all_expenses = Expense.query.order_by(Expense.date.desc()).all()
    return render_template('finance/expenses.html', expenses=all_expenses)


@bp.route('/expenses/add', methods=['GET', 'POST'])
@module_required('finance')
def add_expense():
    form = ExpenseForm()
    if form.validate_on_submit():
        expense = Expense(
            category=form.category.data,
            amount=form.amount.data,
            date=form.date.data,
            description=form.description.data or '',
            submitted_by=current_user.id
        )
        db.session.add(expense)
        db.session.commit()
        flash('Expense recorded.', 'success')
        return redirect(url_for('finance.expenses'))
    return render_template('finance/expense_form.html', form=form, title='Add Expense')


@bp.route('/expenses/<int:expense_id>/edit', methods=['GET', 'POST'])
@module_required('finance')
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    form = ExpenseForm(obj=expense)
    if form.validate_on_submit():
        expense.category = form.category.data
        expense.amount = form.amount.data
        expense.date = form.date.data
        expense.description = form.description.data or ''
        db.session.commit()
        flash('Expense updated.', 'success')
        return redirect(url_for('finance.expenses'))
    return render_template('finance/expense_form.html', form=form, title='Edit Expense', expense=expense)


@bp.route('/expenses/<int:expense_id>/approve', methods=['POST'])
@module_required('finance')
def approve_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    expense.status = 'Approved'
    db.session.commit()
    flash('Expense approved.', 'success')
    return redirect(url_for('finance.expenses'))


@bp.route('/expenses/<int:expense_id>/reject', methods=['POST'])
@module_required('finance')
def reject_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    expense.status = 'Rejected'
    db.session.commit()
    flash('Expense rejected.', 'warning')
    return redirect(url_for('finance.expenses'))


# ── Invoices ─────────────────────────────────────────────────────────────────
@bp.route('/invoices')
@module_required('finance')
def invoices():
    all_invoices = Invoice.query.order_by(Invoice.issue_date.desc()).all()
    return render_template('finance/invoices.html', invoices=all_invoices)


@bp.route('/invoices/add', methods=['GET', 'POST'])
@module_required('finance')
def add_invoice():
    form = InvoiceForm()
    if form.validate_on_submit():
        if Invoice.query.filter_by(invoice_number=form.invoice_number.data).first():
            flash('Invoice number already exists.', 'danger')
            return render_template('finance/invoice_form.html', form=form, title='New Invoice')
        invoice = Invoice(
            invoice_number=form.invoice_number.data,
            client_name=form.client_name.data,
            amount=form.amount.data,
            issue_date=form.issue_date.data,
            due_date=form.due_date.data,
            status=form.status.data,
            description=form.description.data or ''
        )
        db.session.add(invoice)
        db.session.commit()
        flash(f'Invoice {invoice.invoice_number} created.', 'success')
        return redirect(url_for('finance.invoices'))
    return render_template('finance/invoice_form.html', form=form, title='New Invoice')


@bp.route('/invoices/<int:invoice_id>/edit', methods=['GET', 'POST'])
@module_required('finance')
def edit_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    form = InvoiceForm(obj=invoice)
    if form.validate_on_submit():
        existing = Invoice.query.filter(Invoice.invoice_number == form.invoice_number.data,
                                         Invoice.id != invoice.id).first()
        if existing:
            flash('Invoice number already exists.', 'danger')
            return render_template('finance/invoice_form.html', form=form,
                                   title='Edit Invoice', invoice=invoice)
        invoice.invoice_number = form.invoice_number.data
        invoice.client_name = form.client_name.data
        invoice.amount = form.amount.data
        invoice.issue_date = form.issue_date.data
        invoice.due_date = form.due_date.data
        invoice.status = form.status.data
        invoice.description = form.description.data or ''
        db.session.commit()
        flash(f'Invoice {invoice.invoice_number} updated.', 'success')
        return redirect(url_for('finance.invoices'))
    return render_template('finance/invoice_form.html', form=form, title='Edit Invoice', invoice=invoice)


# ── Salaries ─────────────────────────────────────────────────────────────────
@bp.route('/salaries')
@module_required('finance')
def salaries():
    records = SalaryRecord.query.order_by(SalaryRecord.year.desc(),
                                           SalaryRecord.month.desc()).all()
    return render_template('finance/salaries.html', records=records)


@bp.route('/salaries/add', methods=['GET', 'POST'])
@module_required('finance')
def add_salary():
    form = SalaryForm()
    employees = Employee.query.order_by(Employee.emp_code).all()

    if form.validate_on_submit():
        emp_id = request.form.get('employee_id', type=int)
        if not emp_id:
            flash('Please select an employee.', 'danger')
            return render_template('finance/salary_form.html', form=form,
                                   employees=employees, title='Add Salary Record')
        basic = form.basic.data or 0
        hra = form.hra.data or 0
        deductions = form.deductions.data or 0
        net_salary = basic + hra - deductions

        record = SalaryRecord(
            employee_id=emp_id,
            month=form.month.data,
            year=form.year.data,
            basic=basic,
            hra=hra,
            deductions=deductions,
            net_salary=net_salary,
            status=form.status.data
        )
        db.session.add(record)
        db.session.commit()
        flash('Salary record created.', 'success')
        return redirect(url_for('finance.salaries'))
    return render_template('finance/salary_form.html', form=form,
                           employees=employees, title='Add Salary Record')
