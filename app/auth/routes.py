"""Auth routes — login, logout, change password, forgot/reset password."""

from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Message

from app.auth import bp
from app.auth.forms import LoginForm, ChangePasswordForm, ResetPasswordForm
from app.models import User
from app.extensions import db, mail


# ---------------------------------------------------------------------------
# Helpers — Token generation / verification
# ---------------------------------------------------------------------------
def _get_serializer():
    """Return an itsdangerous serializer using the app's SECRET_KEY."""
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])


def generate_reset_token(user):
    """Generate a time-limited password-reset token for the given user."""
    s = _get_serializer()
    return s.dumps(user.email, salt='password-reset-salt')


def verify_reset_token(token):
    """Verify token and return the User, or None if invalid/expired."""
    s = _get_serializer()
    max_age = current_app.config.get('PASSWORD_RESET_EXPIRY', 1800)
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
    return User.query.filter_by(email=email).first()


def send_reset_email(user, token):
    """Send a password-reset email with the token link."""
    reset_url = url_for('auth.reset_password', token=token, _external=True)

    msg = Message(
        subject='Password Reset — Enterprise Portal',
        recipients=[user.email],
        reply_to='noreply@enterpriseportal.com',
    )
    msg.html = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width:520px; margin:0 auto;
                padding:32px; background:#ffffff; border-radius:12px;
                box-shadow:0 4px 16px rgba(0,0,0,0.08);">
        <div style="text-align:center; margin-bottom:24px;">
            <div style="width:56px; height:56px; background:linear-gradient(135deg,#2563eb,#6366f1);
                        border-radius:14px; display:inline-flex; align-items:center;
                        justify-content:center; color:#fff; font-size:1.5rem;">
                🔐
            </div>
        </div>
        <h2 style="text-align:center; color:#1e293b; margin-bottom:8px;">Password Reset Request</h2>
        <p style="color:#64748b; text-align:center; font-size:0.95rem; margin-bottom:24px;">
            Hi <strong>{user.full_name}</strong>, we received a request to reset your password.
        </p>
        <div style="text-align:center; margin-bottom:24px;">
            <a href="{reset_url}"
               style="display:inline-block; padding:14px 32px; background:linear-gradient(135deg,#2563eb,#6366f1);
                      color:#ffffff; text-decoration:none; border-radius:10px; font-weight:600;
                      font-size:0.95rem; box-shadow:0 4px 12px rgba(37,99,235,0.35);">
                Reset My Password
            </a>
        </div>
        <p style="color:#94a3b8; font-size:0.82rem; text-align:center; margin-bottom:16px;">
            This link will expire in <strong>30 minutes</strong>. If you didn't request this, you can safely ignore this email.
        </p>
        <hr style="border:none; border-top:1px solid #f1f5f9; margin:20px 0;">
        <p style="color:#cbd5e1; font-size:0.75rem; text-align:center;">
            Enterprise Portal &bull; Secured Access
        </p>
        <p style="color:#cbd5e1; font-size:0.7rem; text-align:center; margin-top:8px;">
            ⚠ This is an automated message. Please do not reply to this email.
        </p>
    </div>
    """
    mail.send(msg)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# ---------------------------------------------------------------------------
# Change Password (authenticated users)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Forgot Password (AJAX — from login modal)
# ---------------------------------------------------------------------------
@bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request payload.'}), 400

    user_input = data.get('identity')
    if not user_input:
        return jsonify({'error': 'Email or username is required.'}), 400

    # Check if user exists by email or username
    user = User.query.filter(
        (User.email == user_input) | (User.username == user_input)
    ).first()

    if not user:
        return jsonify({'error': 'No account found with that email or username.'}), 404

    # Check that email config is set up
    if not current_app.config.get('MAIL_USERNAME'):
        return jsonify({
            'error': 'Email service is not configured. Please contact your administrator.'
        }), 503

    # Generate token and send email
    try:
        token = generate_reset_token(user)
        send_reset_email(user, token)
        return jsonify({
            'message': f'Password reset link has been sent to {user.email}. Please check your inbox.'
        }), 200
    except Exception as e:
        current_app.logger.error(f'Failed to send reset email: {e}')
        return jsonify({
            'error': 'Failed to send email. Please try again later or contact your administrator.'
        }), 500


# ---------------------------------------------------------------------------
# Reset Password (user clicks link from email)
# ---------------------------------------------------------------------------
@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # If user is already logged in, just go to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main_dashboard'))

    user = verify_reset_token(token)
    if not user:
        flash('The password reset link is invalid or has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth.login'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.new_password.data)
        user.must_change_password = False
        db.session.commit()
        flash('Your password has been reset successfully! You can now sign in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', form=form, token=token)
