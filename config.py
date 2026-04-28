import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'enterprise-portal-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'enterprise_portal.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    # File uploads
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads', 'documents')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'txt', 'xlsx', 'xls'}

    # ── Email / SMTP configuration (for password reset emails) ───────────
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ('true', '1', 'yes')
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ('true', '1', 'yes')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')          # e.g. yourapp@gmail.com
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')          # Gmail App Password
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', MAIL_USERNAME)

    # Token expiry for password reset links (seconds) — default 30 minutes
    PASSWORD_RESET_EXPIRY = int(os.environ.get('PASSWORD_RESET_EXPIRY', 1800))
