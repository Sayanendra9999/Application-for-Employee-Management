# Secure Authentication Module — Token-Based Password Flows

Upgrade the existing `app/auth` blueprint from basic login/logout + temp-password to a full, token-based secure authentication system with proper service/utility layers, matching the patterns already established in the HR module.

## Current State Analysis

| Feature | Current | Target |
|---|---|---|
| User creation | Admin assigns temp password (`Welcome@XXXX`), user sees it on screen | Admin creates user → system emails a "Set Password" link with secure token |
| Password hashing | `werkzeug.security` (`generate_password_hash`) | `bcrypt` via `flask-bcrypt` |
| Forgot password | Stub endpoint, no real logic | Full flow: generate token → email reset link → validate & reset |
| Auth service layer | None (logic inline in routes) | `app/auth/services.py` (matches HR pattern) |
| Auth utilities | None | `app/auth/utils/` with `token_utils.py`, `password_utils.py`, `email_utils.py` |
| Token model | Does not exist | `PasswordResetToken` in `app/models.py` |
| Rate limiting | None | Max 5 forgot-password requests per email per hour |

## User Review Required

> [!IMPORTANT]
> **Breaking Change — Password Hashing Migration**: Switching from `werkzeug.security` to `bcrypt` means **existing password hashes become invalid**. Two options:
> 1. **Dual-check approach** (recommended): Try bcrypt first, fall back to werkzeug. On successful werkzeug login, re-hash with bcrypt. Zero downtime.
> 2. **Hard cutover**: Force all existing users to reset passwords. Disruptive.
>
> The plan uses Option 1 (dual-check).

> [!WARNING]
> **Admin user creation flow change**: Currently, the admin sees the temp password on screen and manually tells the user. The new flow sends an email instead. If SMTP is not configured, the app will fall back to a **mock mode** that logs the link to the console (for dev) and still shows the link on screen as a fallback.

> [!IMPORTANT]
> **Email Configuration**: The new flow requires SMTP settings in `config.py`. In development, email will be mocked (printed to console). You'll need to configure real SMTP credentials for production.

## Open Questions

1. **Token link base URL**: The set-password link will be `https://yourapp.com/auth/set-password?token=<token>`. Should this use the Flask `request.host_url` dynamically, or should a `BASE_URL` config be set in `config.py`?

2. **Should the admin still see the temp password on screen as a fallback?** (Useful during dev when SMTP isn't configured.) The plan currently keeps this as a fallback alongside the email.

3. **Do you want the set-password and reset-password pages to be JSON API endpoints only, or also render HTML forms?** Your existing auth uses HTML templates (Jinja). The plan implements **both**: HTML form pages for browser users + JSON API validation.

---

## Proposed Changes

### Database Model

#### [MODIFY] [models.py](file:///c:/JGpc/app_at_present/app/models.py)

Add `PasswordResetToken` model after the `AuditLog` model:

```python
class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    expiry_time = db.Column(db.DateTime, nullable=False)  # 15 min from creation
    is_used = db.Column(db.Boolean, default=False)
    purpose = db.Column(db.String(20), default='set_password')  # set_password, reset_password
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='password_tokens')
```

Update the `User` model's `set_password` and `check_password` methods to use bcrypt with werkzeug fallback.

---

### Auth Utilities

#### [NEW] [token_utils.py](file:///c:/JGpc/app_at_present/app/auth/utils/token_utils.py)

- `generate_secure_token()` — Uses `secrets.token_urlsafe(48)` to generate a cryptographically secure token
- `build_set_password_url(token)` — Constructs the full URL for the set-password page
- `build_reset_password_url(token)` — Constructs the full URL for the reset-password page

#### [NEW] [password_utils.py](file:///c:/JGpc/app_at_present/app/auth/utils/password_utils.py)

- `hash_password(plain)` — Hash using bcrypt
- `check_password(plain, hashed)` — Verify bcrypt hash
- `check_password_with_fallback(plain, hashed)` — Try bcrypt first, then werkzeug fallback (migration helper)
- `validate_password_strength(password)` — Enforce min 8 chars, at least 1 uppercase, 1 digit, 1 special char

#### [NEW] [email_utils.py](file:///c:/JGpc/app_at_present/app/auth/utils/email_utils.py)

- `send_set_password_email(user, url)` — Send the "Set Your Password" email
- `send_reset_password_email(user, url)` — Send the "Reset Your Password" email
- Uses SMTP if configured in `config.py`, otherwise **mocks** by printing to console with a `[MOCK EMAIL]` prefix
- HTML email templates with professional styling

#### [NEW] [\_\_init\_\_.py](file:///c:/JGpc/app_at_present/app/auth/utils/__init__.py)

Empty init to make `utils/` a package.

---

### Auth Service Layer

#### [NEW] [services.py](file:///c:/JGpc/app_at_present/app/auth/services.py)

Business logic functions (matching the `app/hr/services.py` pattern):

| Function | Description |
|---|---|
| `create_token(user_id, purpose)` | Generate token, store in DB with 15-min expiry, return token string |
| `verify_token(token_str)` | Validate token exists, not expired, not used. Return `(success, user_id_or_error)` |
| `set_password(token_str, new_password)` | Verify token → hash password → save → mark token used |
| `initiate_forgot_password(email)` | Look up user, generate token, send email. Always return success (don't leak user existence) |
| `reset_password(token_str, new_password)` | Same as set_password but for reset purpose |
| `check_rate_limit(email)` | Count tokens for email in last hour, block if ≥ 5 |
| `log_auth_audit(user_id, action, details)` | Convenience wrapper for AuditLog |

---

### Auth Routes

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/auth/routes.py)

Update and add routes:

| Route | Method | Description |
|---|---|---|
| `/auth/login` | GET, POST | **Unchanged** — existing login flow |
| `/auth/logout` | GET | **Unchanged** — existing logout |
| `/auth/change-password` | GET, POST | **Unchanged** — existing forced change |
| `/auth/set-password` | GET, POST | **NEW** — Render form (GET), validate token & set password (POST) |
| `/auth/forgot-password` | GET, POST | **REPLACE** — Render form (GET), generate token & send email (POST). Replaces the current stub API |
| `/auth/reset-password` | GET, POST | **NEW** — Render form (GET), validate token & reset password (POST) |

#### [MODIFY] [forms.py](file:///c:/JGpc/app_at_present/app/auth/forms.py)

Add new WTForms:
- `SetPasswordForm` — token (hidden), new_password, confirm_password
- `ForgotPasswordForm` — email
- `ResetPasswordForm` — token (hidden), new_password, confirm_password

---

### Auth Templates

#### [NEW] [set_password.html](file:///c:/JGpc/app_at_present/app/templates/auth/set_password.html)

"Set Your Password" page — renders when user clicks the email link. Shows token validation status and password form.

#### [NEW] [forgot_password.html](file:///c:/JGpc/app_at_present/app/templates/auth/forgot_password.html)

"Forgot Password?" page — email input form with success/error flash messages. Consistent with existing login page styling.

#### [NEW] [reset_password.html](file:///c:/JGpc/app_at_present/app/templates/auth/reset_password.html)

"Reset Your Password" page — similar to set_password.html, validates token and allows new password entry.

---

### Admin Module Update

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/admin/routes.py)

Update `add_user()` (line 86-143):
- **Remove** temp password generation and `session['new_user_info']`
- Instead: create user with a placeholder password hash, generate a `set_password` token, send email with "Set Password" link
- **Keep fallback**: If email mock mode, still store the link in `session['new_user_info']` so admin can manually share it

Update `reset_password()` (line 229-241):
- Instead of setting a temp password, generate a `reset_password` token and send email
- Keep screen fallback for dev mode

---

### Config Update

#### [MODIFY] [config.py](file:///c:/JGpc/app_at_present/config.py)

Add email/SMTP configuration:

```python
# Email / SMTP (set in environment for production)
MAIL_SERVER = os.environ.get('MAIL_SERVER', '')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@enterprise-portal.com')

# Auth security
PASSWORD_TOKEN_EXPIRY_MINS = 15
FORGOT_PASSWORD_RATE_LIMIT = 5  # max requests per hour per email
```

---

### Dependencies

#### [MODIFY] [requirements.txt](file:///c:/JGpc/app_at_present/requirements.txt)

Add:
```
flask-bcrypt==1.0.1
```

---

## File Summary

| File | Action | Description |
|---|---|---|
| `app/models.py` | MODIFY | Add `PasswordResetToken` model, update `User` password methods for bcrypt |
| `app/auth/utils/__init__.py` | NEW | Package init |
| `app/auth/utils/token_utils.py` | NEW | Secure token generation & URL building |
| `app/auth/utils/password_utils.py` | NEW | bcrypt hashing, verification, strength validation |
| `app/auth/utils/email_utils.py` | NEW | SMTP/mock email sending |
| `app/auth/services.py` | NEW | Business logic layer |
| `app/auth/routes.py` | MODIFY | Add set-password, forgot-password, reset-password routes |
| `app/auth/forms.py` | MODIFY | Add 3 new WTForms |
| `app/templates/auth/set_password.html` | NEW | Set password page |
| `app/templates/auth/forgot_password.html` | NEW | Forgot password page |
| `app/templates/auth/reset_password.html` | NEW | Reset password page |
| `app/admin/routes.py` | MODIFY | Update user creation & reset to use token flow |
| `config.py` | MODIFY | Add SMTP & token config |
| `requirements.txt` | MODIFY | Add flask-bcrypt |

---

## Verification Plan

### Automated Tests
1. Run `python app.py` and verify no import errors
2. Test token generation: create a user via admin → check console for mock email with set-password link
3. Test set-password flow: visit the link → set password → verify login works
4. Test forgot-password: submit email → check console for reset link
5. Test reset-password: visit the link → reset password → verify login works
6. Test expired token: wait 15 mins (or manually set expiry in DB) → verify rejection
7. Test rate limiting: submit forgot-password 6 times → verify 6th is blocked
8. Test existing user login: verify existing werkzeug-hashed passwords still work (dual-check fallback)

### Manual Verification
- Walk through the full flow in browser
- Verify all flash messages and error handling
- Confirm audit log entries are created for token generation and password changes
