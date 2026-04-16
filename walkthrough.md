# Enterprise Portal — Walkthrough

## ✅ Project Status: COMPLETE

All **75 files** have been created and the SQLite database has been seeded with dummy data.

---

## Project Structure (75 files)

```
c:\JGpc\app_at_present\
├── app.py                          # Entry point
├── config.py                       # SQLite config
├── requirements.txt                # 9 Python dependencies
├── seed_data.py                    # Dummy data seeder
├── schema.sql                      # Reference SQL schema
├── enterprise_portal.db            # SQLite database (auto-created)
│
├── app/
│   ├── __init__.py                 # App factory (create_app)
│   ├── extensions.py               # db, login_manager, migrate, csrf
│   ├── models.py                   # 12 SQLAlchemy models
│   ├── decorators.py               # @admin_required, @module_required
│   │
│   ├── auth/                       # Login / Logout
│   ├── admin/                      # User CRUD + module assignment
│   ├── hr/                         # Employees, leaves, attendance
│   ├── pm/                         # Projects, tasks, members
│   ├── finance/                    # Expenses, invoices, salaries
│   ├── employee/                   # Personal dashboard, profile, tasks, leaves
│   │
│   └── templates/                  # 23 Jinja2 templates
│       ├── base.html               # Master layout
│       ├── login.html              # Login page
│       ├── dashboard.html          # Module card grid
│       ├── admin/ (4 templates)
│       ├── hr/ (5 templates)
│       ├── pm/ (5 templates)
│       ├── finance/ (7 templates)
│       ├── employee/ (5 templates)
│       └── errors/ (3 templates)
│
└── static/
    ├── css/style.css               # Full custom theme (~550 lines)
    └── js/app.js                   # Sidebar toggle, confirmations, salary calc
```

---

## How to Run Locally

Open a terminal in `c:\JGpc\app_at_present` and run:

```bash
# 1. Install dependencies (already done)
pip install -r requirements.txt

# 2. Seed the database with test data (already done)
python -c "import sys; sys.stdout.reconfigure(encoding='utf-8'); exec(open('seed_data.py', encoding='utf-8').read())"

# 3. Start the app
python app.py

# 4. Open in browser
# http://localhost:5000
```

> [!NOTE]
> If step 2 gives a Unicode error, use the `-c` wrapper shown above. This is a Windows console encoding issue.

---

## Test Accounts

| Username | Password | Role | Accessible Modules |
|---|---|---|---|
| `admin` | `admin123` | **Admin (superuser)** | Admin, HR, PM, Finance, Employee |
| `hr_manager` | `hr123` | HR Manager | HR, Employee |
| `pm_lead` | `pm123` | PM Lead | PM, Employee |
| `finance_head` | `fin123` | Finance Head | Finance, Employee |
| `john_doe` | `john123` | Developer | PM, Employee |
| `jane_smith` | `jane123` | Accountant | Finance, Employee |
| `bob_wilson` | `bob123` | HR Staff | HR, Employee |

---

## What Was Built

### 1. Authentication & RBAC
- Single login page with session-based auth (Flask-Login)
- `@admin_required` decorator — restricts to admin users
- `@module_required(slug)` decorator — checks `user_modules` table
- Admin bypasses all module checks
- Dynamic sidebar + dashboard — shows only permitted modules

### 2. Admin Module
- Dashboard with system-wide stats (users, employees, projects, tasks)
- Full user CRUD (create, edit, deactivate)
- Module permission assignment via checkbox grid
- Employee module auto-assigned to new users

### 3. HR Module
- Employee records CRUD (linked to user accounts)
- Leave request management with approve/reject actions
- Attendance log viewer with status badges

### 4. Project Management Module
- Project CRUD with status tracking
- Team member management (add/remove with roles)
- Task CRUD with assignment, priority, status, due dates
- Project detail page with members sidebar + task list

### 5. Finance Module
- Dashboard with financial summaries (invoiced, expenses, salary paid, net revenue)
- Expense tracking with approve/reject workflow
- Invoice management with status tracking
- Salary records with Basic/HRA/Deductions breakdown
- Live net salary calculator in the form (JavaScript)

### 6. Employee Module
- Personal dashboard with task stats, pending leaves, department info
- Profile view/edit
- My Tasks view (assigned tasks across all projects)
- My Leaves history + new leave request form

### 7. Frontend Design
- Bootstrap 5.3 with custom CSS theme
- Dark indigo sidebar with hover animations
- Glassmorphism login page with gradient background
- Stat cards with colored top borders and icon badges
- Module cards with gradient icons and hover effects
- Responsive layout (mobile sidebar toggle)
- Auto-dismissing flash messages
- Delete confirmation dialogs

### 8. Database
- SQLite (zero setup, file-based)
- 12 normalized tables with foreign keys and unique constraints
- Pre-seeded with: 7 users, 6 employees, 5 leaves, ~60 attendance records, 3 projects, 10 tasks, 5 expenses, 3 invoices, 18 salary records

---

## Key Technical Decisions

| Decision | Rationale |
|---|---|
| **SQLite over MySQL** | Zero setup for development; swap to MySQL by changing one config line |
| **Flask Blueprints** | Clean module separation; each module is independently maintainable |
| **Context processor** | `user_modules` injected into all templates for dynamic sidebar |
| **Deactivate vs Delete** | Users are soft-deleted (deactivated) to preserve data integrity |
| **CSRF protection** | All forms use Flask-WTF with hidden CSRF tokens |
| **Password hashing** | Werkzeug's `generate_password_hash` (pbkdf2:sha256) |

---

## Migrating to MySQL Later

When ready for production, just change one line in [config.py](file:///c:/JGpc/app_at_present/config.py):

```python
# Change this:
SQLALCHEMY_DATABASE_URI = 'sqlite:///enterprise_portal.db'

# To this:
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://user:password@localhost/enterprise_portal'
```

Then `pip install pymysql` and re-run `seed_data.py`. All code remains identical.
