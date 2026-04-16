# Enterprise Portal — Production Readiness Guide

This document covers **every change** you need to make to turn the current prototype into a production-ready application that safely stores real data.

---

## Table of Contents

1. [Database: Move from SQLite to MySQL/PostgreSQL](#1-database-move-from-sqlite-to-mysqlpostgresql)
2. [Security Hardening](#2-security-hardening)
3. [WSGI Server (Stop Using Flask Dev Server)](#3-wsgi-server-stop-using-flask-dev-server)
4. [Environment Configuration](#4-environment-configuration)
5. [Logging & Monitoring](#5-logging--monitoring)
6. [Data Persistence & Backups](#6-data-persistence--backups)
7. [Input Validation & Data Integrity](#7-input-validation--data-integrity)
8. [Session & Auth Hardening](#8-session--auth-hardening)
9. [Performance & Scalability](#9-performance--scalability)
10. [Migration Checklist](#10-migration-checklist)

---

## 1. Database: Move from SQLite to MySQL/PostgreSQL

### Why SQLite is Not Production-Ready

| Problem | Impact |
|---|---|
| Single file, no server | One corrupted write = entire database lost |
| No concurrent write support | Multiple users writing simultaneously = locked database errors |
| No user authentication | Anyone with file system access can read/modify all data |
| No network access | Can't separate app server from database server |
| Limited data types | No native DECIMAL, DATETIME precision may vary |

### Recommended: PostgreSQL (or MySQL)

PostgreSQL is the industry standard for production Flask apps. MySQL is also fine if you're more familiar.

### Step-by-Step Migration

#### A. Install PostgreSQL/MySQL

```bash
# PostgreSQL (recommended)
# Download from: https://www.postgresql.org/download/windows/
# Or use Docker:
docker run --name enterprise-db -e POSTGRES_PASSWORD=strongpassword -e POSTGRES_DB=enterprise_portal -p 5432:5432 -d postgres:16

# MySQL alternative
# Download from: https://dev.mysql.com/downloads/installer/
```

#### B. Create the Database

```sql
-- PostgreSQL
CREATE DATABASE enterprise_portal;
CREATE USER app_user WITH ENCRYPTED PASSWORD 'your_strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE enterprise_portal TO app_user;

-- MySQL
CREATE DATABASE enterprise_portal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'your_strong_password_here';
GRANT ALL PRIVILEGES ON enterprise_portal.* TO 'app_user'@'localhost';
FLUSH PRIVILEGES;
```

#### C. Install Python Driver

```bash
# For PostgreSQL
pip install psycopg2-binary

# For MySQL
pip install pymysql
```

#### D. Update config.py

```python
# BEFORE (SQLite - development only)
SQLALCHEMY_DATABASE_URI = 'sqlite:///enterprise_portal.db'

# AFTER (PostgreSQL - production)
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    'postgresql://app_user:your_strong_password_here@localhost:5432/enterprise_portal'

# AFTER (MySQL alternative)
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    'mysql+pymysql://app_user:your_strong_password_here@localhost:3306/enterprise_portal'
```

#### E. Use Flask-Migrate for Schema Management

Never use `db.create_all()` in production. Use migrations instead:

```bash
# Initialize migrations (one time)
flask db init

# Generate migration from models
flask db migrate -m "Initial schema"

# Apply migration to database
flask db upgrade
```

> [!CAUTION]
> After switching databases, run `seed_data.py` ONCE to create initial admin user and modules. Then **delete seed_data.py from the production server** — it drops all tables!

---

## 2. Security Hardening

### A. Secret Key

The current `SECRET_KEY` is hardcoded. In production, **this must be a random, unguessable value stored outside the code**.

```python
# config.py — PRODUCTION
import os

class Config:
    SECRET_KEY = os.environ['SECRET_KEY']  # MUST be set, crash if missing
    # Generate one with: python -c "import secrets; print(secrets.token_hex(32))"
```

```bash
# .env file (NEVER commit this to git)
SECRET_KEY=a3f8b2c9e1d4f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0
DATABASE_URL=postgresql://app_user:password@localhost:5432/enterprise_portal
```

### B. Debug Mode OFF

```python
# app.py — PRODUCTION
if __name__ == '__main__':
    app.run(debug=False)  # NEVER debug=True in production

# Better: use environment variable
app.run(debug=os.environ.get('FLASK_DEBUG', '0') == '1')
```

> [!WARNING]
> `debug=True` exposes an interactive debugger that lets anyone execute Python code on your server. This is a **critical security vulnerability**.

### C. HTTPS (SSL/TLS)

All production traffic must use HTTPS. Add to config:

```python
class Config:
    SESSION_COOKIE_SECURE = True        # Cookies only sent over HTTPS
    SESSION_COOKIE_HTTPONLY = True       # JS cannot access session cookie
    SESSION_COOKIE_SAMESITE = 'Lax'     # Prevent CSRF via cross-site requests
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
```

### D. Password Policy

Currently passwords just need 6+ characters. For production, enforce stronger rules:

```python
# app/admin/forms.py — add a custom validator
from wtforms.validators import ValidationError
import re

def strong_password(form, field):
    password = field.data
    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters.')
    if not re.search(r'[A-Z]', password):
        raise ValidationError('Password must contain an uppercase letter.')
    if not re.search(r'[a-z]', password):
        raise ValidationError('Password must contain a lowercase letter.')
    if not re.search(r'[0-9]', password):
        raise ValidationError('Password must contain a digit.')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError('Password must contain a special character.')
```

### E. Rate Limiting (Prevent Brute Force)

```bash
pip install Flask-Limiter
```

```python
# app/__init__.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

def create_app():
    app = Flask(__name__)
    limiter.init_app(app)
    ...

# app/auth/routes.py
from app import limiter

@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Max 5 login attempts per minute
def login():
    ...
```

### F. CSRF Protection

Already implemented via Flask-WTF. Verify that every form template includes `{{ form.hidden_tag() }}` — all of ours do.

### G. SQL Injection Protection

Already safe — SQLAlchemy uses parameterized queries. **Never write raw SQL with string formatting.** All our code uses ORM queries.

### H. XSS Protection

Jinja2 auto-escapes all `{{ variables }}` by default. We're safe. Just never use `{{ variable | safe }}` with user-generated content.

---

## 3. WSGI Server (Stop Using Flask Dev Server)

### Why

Flask's built-in server (`app.run()`) is single-threaded and not designed for production load.

### Recommended: Gunicorn + Nginx

#### A. Install Gunicorn

```bash
pip install gunicorn
```

> [!NOTE]
> Gunicorn doesn't run natively on Windows. For Windows production, use **Waitress** instead:
> ```bash
> pip install waitress
> ```

#### B. Create wsgi.py

```python
# wsgi.py (new file in project root)
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
```

#### C. Run with Gunicorn (Linux/Mac)

```bash
gunicorn --workers 4 --bind 0.0.0.0:8000 wsgi:app
```

#### D. Run with Waitress (Windows)

```bash
waitress-serve --host 0.0.0.0 --port 8000 wsgi:app
```

#### E. Nginx as Reverse Proxy (recommended)

```nginx
# /etc/nginx/sites-available/enterprise-portal
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/app_at_present/static;
        expires 30d;
    }
}
```

---

## 4. Environment Configuration

### A. Create Separate Configs

```python
# config.py — PRODUCTION VERSION
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv()


class Config:
    """Base config."""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class DevelopmentConfig(Config):
    """Local development."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'enterprise_portal.db')
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-not-for-production'


class ProductionConfig(Config):
    """Production server."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    SECRET_KEY = os.environ['SECRET_KEY']
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class TestingConfig(Config):
    """Unit tests."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'testing-key'
    WTF_CSRF_ENABLED = False


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}
```

### B. .env File (for Production Server)

```env
# .env — NEVER commit to Git
FLASK_ENV=production
SECRET_KEY=a3f8b2c9e1d4f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0
DATABASE_URL=postgresql://app_user:strongpassword@localhost:5432/enterprise_portal
```

### C. .gitignore

```gitignore
# .gitignore
*.db
*.pyc
__pycache__/
.env
instance/
migrations/
*.log
```

---

## 5. Logging & Monitoring

### A. Add Application Logging

```python
# app/__init__.py — add logging setup inside create_app()
import logging
from logging.handlers import RotatingFileHandler
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    ...

    # Production logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = RotatingFileHandler(
            'logs/enterprise_portal.log',
            maxBytes=10_240_000,   # 10 MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Enterprise Portal startup')

    return app
```

### B. Log Important Events

```python
# In auth/routes.py
app.logger.info(f'User {user.username} logged in from {request.remote_addr}')
app.logger.warning(f'Failed login attempt for username: {form.username.data}')

# In admin/routes.py
app.logger.info(f'Admin {current_user.username} created user {user.username}')
app.logger.info(f'Module permissions updated for user {user.username}')
```

### C. Monitor with Health Check

```python
# Add to app/__init__.py
@app.route('/health')
def health_check():
    try:
        db.session.execute(db.text('SELECT 1'))
        return {'status': 'healthy', 'database': 'connected'}, 200
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}, 500
```

---

## 6. Data Persistence & Backups

### A. Database Backups

```bash
# PostgreSQL — daily backup script
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
pg_dump -U app_user enterprise_portal > /backups/enterprise_portal_${TIMESTAMP}.sql

# Keep last 30 days only
find /backups/ -name "*.sql" -mtime +30 -delete

# MySQL equivalent
mysqldump -u app_user -p enterprise_portal > /backups/enterprise_portal_${TIMESTAMP}.sql
```

Schedule this with **cron** (Linux) or **Task Scheduler** (Windows) to run daily.

### B. Connection Pooling

```python
# config.py — prevents "too many connections" errors
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 1800,
}
```

### C. Seed Data Strategy for Production

> [!CAUTION]
> The current `seed_data.py` calls `db.drop_all()` which **destroys all data**. For production:

1. Run `seed_data.py` **once** on initial setup to create the admin user and module records
2. **Delete or rename** `seed_data.py` after running it
3. For future data seeding, create a **safe** migration script:

```python
# safe_seed.py — production-safe initial setup
"""Creates only the admin user and modules if they don't exist."""

from app import create_app
from app.extensions import db
from app.models import User, Module

app = create_app()

with app.app_context():
    # Create tables if they don't exist
    db.create_all()

    # Create modules if they don't exist
    if Module.query.count() == 0:
        modules = [
            Module(name='Admin', slug='admin',
                   description='System administration & user management',
                   icon='fas fa-shield-halved'),
            Module(name='HR', slug='hr',
                   description='Human resources, employees & attendance',
                   icon='fas fa-people-group'),
            Module(name='Project Management', slug='pm',
                   description='Projects, tasks & team collaboration',
                   icon='fas fa-diagram-project'),
            Module(name='Finance', slug='finance',
                   description='Salary, expenses, invoices & reports',
                   icon='fas fa-indian-rupee-sign'),
            Module(name='Employee', slug='employee',
                   description='Personal dashboard, tasks & leaves',
                   icon='fas fa-user-circle'),
        ]
        db.session.add_all(modules)
        db.session.commit()
        print('Modules created.')

    # Create admin if doesn't exist
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@company.com',
                     full_name='System Admin', is_admin=True)
        admin.set_password('CHANGE_THIS_IMMEDIATELY')
        db.session.add(admin)
        db.session.commit()
        print('Admin user created. CHANGE THE PASSWORD IMMEDIATELY.')
    else:
        print('Admin already exists. Skipping.')
```

---

## 7. Input Validation & Data Integrity

### A. Server-Side Validation (Already Partially Done)

All forms use Flask-WTF validators. Additional production hardening:

```python
# Add length limits to all text fields to prevent oversized inputs
# Add regex validation to fields like PAN, phone, emp_code
# Example:
from wtforms.validators import Regexp

pan_number = StringField('PAN', validators=[
    Optional(),
    Regexp(r'^[A-Z]{5}[0-9]{4}[A-Z]$', message='Invalid PAN format')
])
```

### B. Database-Level Validation

Add validation at the model layer for critical fields:

```python
# In models.py
from sqlalchemy.orm import validates

class Employee(db.Model):
    @validates('salary')
    def validate_salary(self, key, value):
        if value < 0:
            raise ValueError('Salary cannot be negative')
        return value

class Leave(db.Model):
    @validates('end_date')
    def validate_end_date(self, key, value):
        if self.start_date and value < self.start_date:
            raise ValueError('End date cannot be before start date')
        return value
```

### C. File Upload Security (If Added Later)

If you add file uploads (profile photos, documents), always:
- Validate file type and size
- Store outside the web root
- Use random filenames, never user-supplied names

---

## 8. Session & Auth Hardening

### A. Session Timeout

```python
# config.py
from datetime import timedelta

class ProductionConfig(Config):
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
```

```python
# app/__init__.py — make all sessions permanent (respect the timeout)
@app.before_request
def make_session_permanent():
    from flask import session
    session.permanent = True
```

### B. Account Lockout (After Failed Attempts)

```python
# Add to User model
class User(UserMixin, db.Model):
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)

# In auth/routes.py
from datetime import datetime, timedelta

def login():
    user = User.query.filter_by(username=form.username.data).first()
    if user and user.locked_until and user.locked_until > datetime.utcnow():
        flash('Account locked. Try again in 15 minutes.', 'danger')
        return redirect(url_for('auth.login'))

    if user and not user.check_password(form.password.data):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
        db.session.commit()
```

### C. Password Change Feature

Add a "Change Password" route for users to update their own passwords (currently only admin can set passwords).

---

## 9. Performance & Scalability

### A. Database Query Optimization

```python
# Use eager loading to avoid N+1 queries
# BEFORE (N+1 — one query per user's modules):
users = User.query.all()  # then template accesses user.modules for each

# AFTER:
from sqlalchemy.orm import joinedload
users = User.query.options(joinedload(User.modules)).all()
```

### B. Static File Caching

Let Nginx serve static files directly (shown in Nginx config above). Add cache headers:

```python
# config.py
SEND_FILE_MAX_AGE_DEFAULT = 2592000  # 30 days
```

### C. Pagination

For tables that may grow large (attendance, salary records), add pagination:

```python
# Instead of:
records = Attendance.query.all()

# Use:
page = request.args.get('page', 1, type=int)
records = Attendance.query.order_by(Attendance.date.desc()).paginate(
    page=page, per_page=50, error_out=False
)
```

### D. Database Indexing

Add indexes to frequently queried columns:

```python
class Attendance(db.Model):
    employee_id = db.Column(db.Integer, ..., index=True)
    date = db.Column(db.Date, nullable=False, index=True)

class Task(db.Model):
    assigned_to = db.Column(db.Integer, ..., index=True)
    status = db.Column(db.String(20), default='To Do', index=True)
```

---

## 10. Migration Checklist

Here's a priority-ordered checklist for moving to production:

### Critical (Do Before Going Live)

| # | Task | File(s) to Change |
|---|---|---|
| 1 | Replace SQLite with PostgreSQL/MySQL | `config.py`, `requirements.txt` |
| 2 | Set `SECRET_KEY` from environment variable | `config.py`, `.env` |
| 3 | Set `debug=False` | `app.py` or `wsgi.py` |
| 4 | Use Gunicorn/Waitress instead of Flask dev server | New `wsgi.py` |
| 5 | Set secure cookie flags | `config.py` |
| 6 | Remove/rename `seed_data.py` after initial setup | `seed_data.py` |
| 7 | Create `.gitignore` excluding `.env`, `.db`, `__pycache__` | New `.gitignore` |
| 8 | Enable HTTPS via Nginx or cloud provider | Nginx config |
| 9 | Change all test user passwords | Via admin panel |

### Important (Do Within First Week)

| # | Task | File(s) to Change |
|---|---|---|
| 10 | Add rate limiting to login | `app/__init__.py`, `app/auth/routes.py` |
| 11 | Add application logging | `app/__init__.py` |
| 12 | Set up database backups (daily) | Cron/Task Scheduler script |
| 13 | Add password strength validation | `app/admin/forms.py` |
| 14 | Add session timeout | `config.py`, `app/__init__.py` |
| 15 | Use Flask-Migrate for schema changes | Terminal commands |
| 16 | Add connection pooling config | `config.py` |

### Nice to Have (Add Over Time)

| # | Task | Description |
|---|---|---|
| 17 | Pagination | Attendance, salary records, large lists |
| 18 | Audit logging | Track who changed what and when |
| 19 | Email notifications | Leave approvals, new task assignments |
| 20 | Export to Excel/PDF | Financial reports, attendance sheets |
| 21 | Dashboard charts | Chart.js for visual analytics |
| 22 | Two-factor authentication | TOTP via an authenticator app |
| 23 | Automated tests | pytest + coverage |
| 24 | CI/CD pipeline | Auto-deploy on code push |
| 25 | Docker containerization | Dockerfile + docker-compose.yml |

---

## Quick Reference: Production Config Template

```python
# config.py — Copy-paste ready production config
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class ProductionConfig:
    # Core
    SECRET_KEY = os.environ['SECRET_KEY']
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = False

    # Security
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    REMEMBER_COOKIE_DURATION = timedelta(days=7)

    # Database connection pool
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
        'pool_recycle': 1800,
    }

    # Static files
    SEND_FILE_MAX_AGE_DEFAULT = 2592000
```

---

> [!IMPORTANT]
> **Rule of thumb**: Your current app works perfectly for internal testing and demos. Before putting **real employee data** (salaries, PAN numbers, bank accounts) into it, complete at least items **1-9** from the Critical checklist above. Those 9 changes cover 90% of production risk.
