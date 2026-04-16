# Enterprise Portal — Implementation Plan

## Goal

Build a complete, locally-runnable enterprise web application that combines **Admin, HR, Project Management, Finance, and Employee** modules behind a single login page with role-based access control (RBAC). The Admin is the superuser who assigns employees access to one or more modules.

---

## System Architecture

```mermaid
graph TD
    subgraph "Client (Browser)"
        UI["HTML/CSS/Bootstrap + Jinja2 Templates"]
    end

    subgraph "Flask Application"
        AUTH["Auth Blueprint<br/>/auth"]
        ADMIN["Admin Blueprint<br/>/admin"]
        HR["HR Blueprint<br/>/hr"]
        PM["PM Blueprint<br/>/pm"]
        FIN["Finance Blueprint<br/>/finance"]
        EMP["Employee Blueprint<br/>/employee"]
        MW["Middleware<br/>login_required + role_required"]
    end

    subgraph "Database (MySQL)"
        DB[(MySQL 8.x)]
    end

    UI -->|HTTP Requests| AUTH
    UI --> ADMIN
    UI --> HR
    UI --> PM
    UI --> FIN
    UI --> EMP
    AUTH --> MW
    ADMIN --> MW
    HR --> MW
    PM --> MW
    FIN --> MW
    EMP --> MW
    MW --> DB
```

### Key Design Decisions

| Concern | Decision |
|---|---|
| Authentication | Flask-Login with session-based auth |
| Password hashing | Werkzeug `generate_password_hash` / `check_password_hash` |
| ORM | Flask-SQLAlchemy (SQLAlchemy 2.x) |
| Migrations | Flask-Migrate (Alembic) |
| Forms | Flask-WTF with CSRF protection |
| Frontend | Bootstrap 5.3 + vanilla JS + Jinja2 |
| RBAC | `user_modules` junction table + custom `@module_required` decorator |
| Structure | Flask Blueprints — one per module |

---

## Database Schema

```mermaid
erDiagram
    users {
        int id PK
        varchar username UK
        varchar email UK
        varchar password_hash
        varchar full_name
        varchar phone
        boolean is_admin
        boolean is_active
        datetime created_at
    }

    modules {
        int id PK
        varchar name UK
        varchar slug UK
        varchar description
        varchar icon
    }

    user_modules {
        int id PK
        int user_id FK
        int module_id FK
    }

    employees {
        int id PK
        int user_id FK
        varchar emp_code UK
        varchar department
        varchar designation
        date date_of_joining
        decimal salary
        varchar bank_account
        varchar pan_number
    }

    leaves {
        int id PK
        int employee_id FK
        varchar leave_type
        date start_date
        date end_date
        varchar status
        text reason
        int approved_by FK
    }

    attendance {
        int id PK
        int employee_id FK
        date date
        time check_in
        time check_out
        varchar status
    }

    projects {
        int id PK
        varchar name
        text description
        date start_date
        date end_date
        varchar status
        int created_by FK
    }

    project_members {
        int id PK
        int project_id FK
        int user_id FK
        varchar role
    }

    tasks {
        int id PK
        int project_id FK
        varchar title
        text description
        int assigned_to FK
        varchar priority
        varchar status
        date due_date
    }

    expenses {
        int id PK
        varchar category
        decimal amount
        date date
        text description
        int submitted_by FK
        varchar status
    }

    invoices {
        int id PK
        varchar invoice_number UK
        varchar client_name
        decimal amount
        date issue_date
        date due_date
        varchar status
    }

    salary_records {
        int id PK
        int employee_id FK
        varchar month
        int year
        decimal basic
        decimal hra
        decimal deductions
        decimal net_salary
        varchar status
    }

    users ||--o{ user_modules : "has"
    modules ||--o{ user_modules : "assigned to"
    users ||--o| employees : "profile"
    employees ||--o{ leaves : "requests"
    employees ||--o{ attendance : "logs"
    projects ||--o{ project_members : "has"
    users ||--o{ project_members : "member of"
    projects ||--o{ tasks : "contains"
    users ||--o{ tasks : "assigned"
    users ||--o{ expenses : "submits"
    employees ||--o{ salary_records : "earns"
```

---

## Project File Structure

```
c:\JGpc\app_at_present\
├── app.py                          # Application factory
├── config.py                       # Configuration (DB URI, secret key)
├── requirements.txt                # Python dependencies
├── seed_data.py                    # Dummy data seeder script
├── schema.sql                      # Raw SQL schema (reference)
│
├── app/
│   ├── __init__.py                 # create_app() factory
│   ├── extensions.py               # db, login_manager, migrate, csrf
│   ├── models.py                   # All SQLAlchemy models
│   ├── decorators.py               # @login_required, @module_required
│   │
│   ├── auth/
│   │   ├── __init__.py             # Blueprint registration
│   │   ├── routes.py               # /login, /logout
│   │   └── forms.py                # LoginForm
│   │
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── routes.py               # User CRUD, role/module assignment
│   │   └── forms.py                # UserForm, ModuleAssignForm
│   │
│   ├── hr/
│   │   ├── __init__.py
│   │   ├── routes.py               # Employee CRUD, leaves, attendance
│   │   └── forms.py
│   │
│   ├── pm/
│   │   ├── __init__.py
│   │   ├── routes.py               # Project/Task CRUD, assignment
│   │   └── forms.py
│   │
│   ├── finance/
│   │   ├── __init__.py
│   │   ├── routes.py               # Salary, expenses, invoices
│   │   └── forms.py
│   │
│   ├── employee/
│   │   ├── __init__.py
│   │   ├── routes.py               # Personal dashboard, tasks, leaves
│   │   └── forms.py
│   │
│   └── templates/
│       ├── base.html               # Master layout with nav + sidebar
│       ├── login.html              # Single login page
│       ├── dashboard.html          # Module-card landing page
│       ├── components/
│       │   ├── _navbar.html
│       │   ├── _sidebar.html
│       │   ├── _flash_messages.html
│       │   └── _pagination.html
│       ├── admin/
│       │   ├── dashboard.html
│       │   ├── users.html
│       │   ├── user_form.html
│       │   └── assign_modules.html
│       ├── hr/
│       │   ├── dashboard.html
│       │   ├── employees.html
│       │   ├── employee_form.html
│       │   ├── leaves.html
│       │   └── attendance.html
│       ├── pm/
│       │   ├── dashboard.html
│       │   ├── projects.html
│       │   ├── project_form.html
│       │   ├── project_detail.html
│       │   ├── tasks.html
│       │   └── task_form.html
│       ├── finance/
│       │   ├── dashboard.html
│       │   ├── salaries.html
│       │   ├── expenses.html
│       │   ├── expense_form.html
│       │   ├── invoices.html
│       │   └── invoice_form.html
│       └── employee/
│           ├── dashboard.html
│           ├── profile.html
│           ├── my_tasks.html
│           ├── my_leaves.html
│           └── leave_request.html
│
├── static/
│   ├── css/
│   │   └── style.css              # Custom theme overrides
│   ├── js/
│   │   └── app.js                 # Sidebar toggle, charts, interactivity
│   └── img/
│       └── logo.png               # App logo
```

---

## Proposed Changes

### Phase 1 — Configuration & Dependencies

#### [NEW] [requirements.txt](file:///c:/JGpc/app_at_present/requirements.txt)
- Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, PyMySQL, Werkzeug, python-dotenv

#### [NEW] [config.py](file:///c:/JGpc/app_at_present/config.py)
- `Config` class with `SQLALCHEMY_DATABASE_URI`, `SECRET_KEY`, `WTF_CSRF_ENABLED`
- Support `DATABASE_URL` env var override or default to `mysql+pymysql://root:password@localhost/enterprise_portal`

---

### Phase 2 — Application Factory & Extensions

#### [NEW] [app/__init__.py](file:///c:/JGpc/app_at_present/app/__init__.py)
- `create_app()` factory: init extensions, register all 6 blueprints, configure login manager

#### [NEW] [app/extensions.py](file:///c:/JGpc/app_at_present/app/extensions.py)
- Instantiate `SQLAlchemy`, `LoginManager`, `Migrate`, `CSRFProtect`

#### [NEW] [app.py](file:///c:/JGpc/app_at_present/app.py)
- Entry point: `from app import create_app; app = create_app(); app.run(debug=True)`

---

### Phase 3 — Models & Decorators

#### [NEW] [app/models.py](file:///c:/JGpc/app_at_present/app/models.py)
All 12 tables as SQLAlchemy models:
- `User`, `Module`, `UserModule`, `Employee`, `Leave`, `Attendance`
- `Project`, `ProjectMember`, `Task`, `Expense`, `Invoice`, `SalaryRecord`
- User model implements `UserMixin` for Flask-Login

#### [NEW] [app/decorators.py](file:///c:/JGpc/app_at_present/app/decorators.py)
- `@login_required` (from Flask-Login)
- `@admin_required` — checks `current_user.is_admin`
- `@module_required(module_slug)` — checks user has access to the given module via `user_modules`

---

### Phase 4 — Auth Blueprint

#### [NEW] [app/auth/routes.py](file:///c:/JGpc/app_at_present/app/auth/routes.py)
- `GET/POST /auth/login` — validate credentials, `login_user()`, redirect to dashboard
- `GET /auth/logout` — `logout_user()`, redirect to login
- On successful login, redirect to `/dashboard` which shows module cards dynamically

#### [NEW] [app/auth/forms.py](file:///c:/JGpc/app_at_present/app/auth/forms.py)
- `LoginForm` with username, password, remember me

---

### Phase 5 — Admin Blueprint

#### [NEW] [app/admin/routes.py](file:///c:/JGpc/app_at_present/app/admin/routes.py)
- `GET /admin/` — Admin dashboard with stats (total users, active/inactive, module usage)
- `GET /admin/users` — List all users
- `GET/POST /admin/users/add` — Create new user
- `GET/POST /admin/users/<id>/edit` — Edit user
- `POST /admin/users/<id>/delete` — Deactivate user
- `GET/POST /admin/users/<id>/modules` — Assign/revoke module access
- All routes protected with `@admin_required`

#### [NEW] [app/admin/forms.py](file:///c:/JGpc/app_at_present/app/admin/forms.py)
- `UserForm`, `ModuleAssignForm` (multi-checkbox for modules)

---

### Phase 6 — HR Blueprint

#### [NEW] [app/hr/routes.py](file:///c:/JGpc/app_at_present/app/hr/routes.py)
- `GET /hr/` — HR dashboard (employee count, pending leaves, attendance summary)
- `GET /hr/employees` — Employee list, `GET/POST /hr/employees/add|edit`
- `GET /hr/leaves` — All leave requests, approve/reject actions
- `GET /hr/attendance` — Attendance log view
- Protected with `@module_required('hr')`

---

### Phase 7 — Project Management Blueprint

#### [NEW] [app/pm/routes.py](file:///c:/JGpc/app_at_present/app/pm/routes.py)
- `GET /pm/` — PM dashboard (project count, task stats, overdue items)
- `GET /pm/projects` — Project list, `GET/POST /pm/projects/add|edit`
- `GET /pm/projects/<id>` — Detail with members + tasks
- `GET/POST /pm/tasks/add|edit` — Task CRUD with assignment
- Protected with `@module_required('pm')`

---

### Phase 8 — Finance Blueprint

#### [NEW] [app/finance/routes.py](file:///c:/JGpc/app_at_present/app/finance/routes.py)
- `GET /finance/` — Finance dashboard (total salary outflow, expenses, invoice totals)
- `GET /finance/salaries` — Salary records list
- `GET /finance/expenses` — Expense list + add/edit
- `GET /finance/invoices` — Invoice list + add/edit
- Protected with `@module_required('finance')`

---

### Phase 9 — Employee Blueprint

#### [NEW] [app/employee/routes.py](file:///c:/JGpc/app_at_present/app/employee/routes.py)
- `GET /employee/` — Personal dashboard (my tasks, leaves pending, upcoming deadlines)
- `GET /employee/profile` — View/edit own profile
- `GET /employee/tasks` — My assigned tasks
- `GET/POST /employee/leaves` — My leaves + request new leave
- Protected with `@module_required('employee')` (all logged-in users get this by default)

---

### Phase 10 — Frontend Templates & Static Assets

#### [NEW] templates/base.html
- Bootstrap 5.3 CDN, Google Fonts (Inter), sidebar + top navbar layout
- Dynamic sidebar: only show links for modules the user has access to (via `current_user.modules`)
- Flash message component, footer

#### [NEW] templates/login.html
- Clean centered login card with gradient background, app branding

#### [NEW] templates/dashboard.html
- Module cards grid — only permitted modules shown
- Each card links to that module's dashboard
- Icons per module (Font Awesome)

#### [NEW] static/css/style.css
- Custom dark/light theme with CSS variables
- Glassmorphism cards, smooth transitions, hover animations
- Sidebar styling, responsive breakpoints
- Dashboard stat-card gradients

#### [NEW] static/js/app.js
- Sidebar toggle for mobile, confirmation dialogs, dynamic form validation

---

### Phase 11 — Seed Data & SQL Schema

#### [NEW] [schema.sql](file:///c:/JGpc/app_at_present/schema.sql)
- Raw DDL for all tables (MySQL syntax) — serves as reference

#### [NEW] [seed_data.py](file:///c:/JGpc/app_at_present/seed_data.py)
- Runnable script that populates the database with test data:

| User | Password | Role | Modules |
|---|---|---|---|
| `admin` | `admin123` | Admin (superuser) | All modules |
| `hr_manager` | `hr123` | HR Manager | HR, Employee |
| `pm_lead` | `pm123` | PM Lead | PM, Employee |
| `finance_head` | `fin123` | Finance Head | Finance, Employee |
| `john_doe` | `john123` | Developer | PM, Employee |
| `jane_smith` | `jane123` | Accountant | Finance, Employee |
| `bob_wilson` | `bob123` | HR Staff | HR, Employee |

Plus sample data: 5 employees, 3 projects, 10 tasks, 15 attendance records, 5 leave requests, 5 expenses, 3 invoices, salary records for 3 months.

---

## Authentication & Authorization Flow

```mermaid
sequenceDiagram
    actor User
    participant Login as Login Page
    participant Auth as Auth Blueprint
    participant MW as Middleware
    participant Dash as Dashboard
    participant Mod as Module Page

    User->>Login: Enter credentials
    Login->>Auth: POST /auth/login
    Auth->>Auth: Validate password hash
    alt Valid credentials
        Auth->>Auth: login_user(user)
        Auth->>Dash: Redirect to /dashboard
        Dash->>Dash: Query user_modules
        Dash->>User: Show permitted module cards
        User->>Mod: Click module card
        Mod->>MW: @module_required check
        alt Has access
            MW->>Mod: Allow access
            Mod->>User: Render module page
        else No access
            MW->>User: 403 Forbidden
        end
    else Invalid credentials
        Auth->>User: Flash error, re-render login
    end
```

---

## User Review Required

> [!IMPORTANT]
> **MySQL Configuration**: The default database URI will be `mysql+pymysql://root:password@localhost/enterprise_portal`. Please confirm:
> 1. Your MySQL root password (or preferred user/password)
> 2. Whether MySQL is installed and running on your machine
> 3. If you'd like me to include SQLite as a fallback for easier testing

> [!IMPORTANT]
> **Bootstrap Theme**: I'll use a modern dark sidebar + light content area design. The login page will feature a gradient background. Let me know if you have a different visual preference.

---

## Open Questions

1. **MySQL credentials**: What username/password should I configure for the database connection? (I'll default to `root:password` if not specified)
2. **Port**: Should the Flask app run on the default port 5000, or a different one?
3. **SQLite fallback**: Would you like SQLite as an alternative for quick testing without MySQL setup?

---

## Verification Plan

### Automated Tests
- Run `python seed_data.py` to verify all tables are created and populated
- Run `python app.py` and verify the app starts without errors
- Test each login credential from the seed data table

### Manual Verification (Browser)
1. Login as `admin` → verify all 5 module cards visible
2. Login as `hr_manager` → verify only HR + Employee cards visible
3. Navigate to `/admin/` as a non-admin → verify 403
4. Navigate to `/finance/` as `hr_manager` → verify 403
5. Run full CRUD cycle on each module (create, read, update, delete)
6. Take screenshots of key pages for the walkthrough
