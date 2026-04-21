"""Auth routes — login, logout, change password."""

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.auth import bp
from app.auth.forms import LoginForm, ChangePasswordForm
from app.models import User
from app.extensions import db
from flask import jsonify


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.must_change_password:
            return redirect(url_for('auth.change_password'))
        return redirect(url_for('main_dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('auth.login'))
        if not user.is_active:
            flash('Your account has been deactivated. Contact admin.', 'warning')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember.data)

        # Check if user must change password on first login
        if user.must_change_password:
            flash('Please set a new password before continuing.', 'warning')
            return redirect(url_for('auth.change_password'))

        flash(f'Welcome back, {user.full_name}!', 'success')
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main_dashboard'))

    return render_template('login.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    is_forced = current_user.must_change_password

    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('change_password.html', form=form, forced=is_forced)

        if form.current_password.data == form.new_password.data:
            flash('New password must be different from the current password.', 'warning')
            return render_template('change_password.html', form=form, forced=is_forced)

        current_user.set_password(form.new_password.data)
        current_user.must_change_password = False
        db.session.commit()
        flash('Password updated successfully!', 'success')
        return redirect(url_for('main_dashboard'))

    return render_template('change_password.html', form=form, forced=is_forced)


@bp.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request payload.'}), 400
        
    user_input = data.get('identity')
    if not user_input:
        return jsonify({'error': 'Email or username is required.'}), 400
        
    # Check if user exists by email or username
    user = User.query.filter((User.email == user_input) | (User.username == user_input)).first()
    
    if not user:
        return jsonify({'error': 'No account found with that email or username.'}), 404
        
    # Mocking successful email sent
    return jsonify({'message': 'Password reset link sent to your email.'}), 200
