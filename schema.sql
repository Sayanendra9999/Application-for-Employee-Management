-- ═══════════════════════════════════════════════════════════════════════
-- Enterprise Portal — SQL Schema Reference (SQLite compatible)
-- Updated: PM Module Upgrade (milestones, notifications, lifecycle)
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    phone VARCHAR(20) DEFAULT '',
    is_admin BOOLEAN DEFAULT 0,
    is_active_user BOOLEAN DEFAULT 1,
    must_change_password BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    slug VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(200) DEFAULT '',
    icon VARCHAR(50) DEFAULT 'fas fa-cube'
);

CREATE TABLE IF NOT EXISTS user_modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    UNIQUE(user_id, module_id)
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    emp_code VARCHAR(20) NOT NULL UNIQUE,
    department_id INTEGER REFERENCES departments(id),
    designation_id INTEGER REFERENCES designations(id),
    date_of_joining DATE,
    salary REAL DEFAULT 0,
    bank_account VARCHAR(30) DEFAULT '',
    pan_number VARCHAR(15) DEFAULT '',
    is_active BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS leaves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type VARCHAR(30) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_days INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'Pending',
    reason TEXT DEFAULT '',
    rejection_reason TEXT DEFAULT '',
    approved_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    check_in VARCHAR(10) DEFAULT '',
    check_out VARCHAR(10) DEFAULT '',
    working_hours REAL DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'Present',
    notes VARCHAR(250) DEFAULT '',
    UNIQUE(employee_id, date)
);

-- ═══════════════════════════════════════════════════════════════════════
-- PM MODULE TABLES — UPGRADED
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    start_date DATE,
    end_date DATE,
    deadline DATE,
    status VARCHAR(30) DEFAULT 'Not Started',
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'Developer',
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id)
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    assigned_to INTEGER REFERENCES users(id),
    priority VARCHAR(20) DEFAULT 'Medium',
    status VARCHAR(20) DEFAULT 'Pending',
    due_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    deadline DATE,
    status VARCHAR(30) DEFAULT 'Pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, title)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    message TEXT DEFAULT '',
    category VARCHAR(30) DEFAULT 'info',
    is_read BOOLEAN DEFAULT 0,
    link VARCHAR(500) DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ═══════════════════════════════════════════════════════════════════════
-- FINANCE TABLES
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category VARCHAR(60) NOT NULL,
    amount REAL NOT NULL,
    date DATE,
    description TEXT DEFAULT '',
    submitted_by INTEGER NOT NULL REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'Pending'
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number VARCHAR(30) NOT NULL UNIQUE,
    client_name VARCHAR(150) NOT NULL,
    amount REAL NOT NULL,
    issue_date DATE,
    due_date DATE,
    status VARCHAR(20) DEFAULT 'Unpaid',
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS salary_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    month VARCHAR(20) NOT NULL,
    year INTEGER NOT NULL,
    basic REAL DEFAULT 0,
    hra REAL DEFAULT 0,
    deductions REAL DEFAULT 0,
    net_salary REAL DEFAULT 0,
    status VARCHAR(20) DEFAULT 'Pending',
    UNIQUE(employee_id, month, year)
);

-- ═══════════════════════════════════════════════════════════════════════
-- ADMIN / HR CONFIG TABLES
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    code VARCHAR(20) NOT NULL UNIQUE,
    description VARCHAR(250) DEFAULT '',
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS designations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(100) NOT NULL,
    department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    level INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(title, department_id)
);

CREATE TABLE IF NOT EXISTS leave_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    leave_type VARCHAR(50) NOT NULL UNIQUE,
    total_days INTEGER NOT NULL DEFAULT 12,
    carry_forward BOOLEAN DEFAULT 0,
    max_carry_days INTEGER DEFAULT 0,
    description VARCHAR(250) DEFAULT '',
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_start VARCHAR(5) DEFAULT '09:00',
    work_end VARCHAR(5) DEFAULT '18:00',
    late_threshold_mins INTEGER DEFAULT 15,
    half_day_hours REAL DEFAULT 4.0,
    full_day_hours REAL DEFAULT 8.0,
    is_active BOOLEAN DEFAULT 1,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER,
    details TEXT DEFAULT '',
    ip_address VARCHAR(45) DEFAULT '',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ═══════════════════════════════════════════════════════════════════════
-- ADDITIONAL HR TABLES
-- ═══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS leave_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type VARCHAR(50) NOT NULL,
    total_allocated INTEGER DEFAULT 0,
    used INTEGER DEFAULT 0,
    year INTEGER NOT NULL,
    UNIQUE(employee_id, leave_type, year)
);

CREATE TABLE IF NOT EXISTS payroll_inputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    month VARCHAR(20) NOT NULL,
    year INTEGER NOT NULL,
    working_days INTEGER DEFAULT 0,
    present_days INTEGER DEFAULT 0,
    leaves_taken INTEGER DEFAULT 0,
    overtime_hours REAL DEFAULT 0.0,
    bonus REAL DEFAULT 0.0,
    deduction_notes TEXT DEFAULT '',
    status VARCHAR(20) DEFAULT 'Draft',
    submitted_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(employee_id, month, year)
);

CREATE TABLE IF NOT EXISTS employee_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    doc_type VARCHAR(50) NOT NULL,
    filename VARCHAR(250) NOT NULL,
    original_name VARCHAR(250) DEFAULT '',
    uploaded_by INTEGER NOT NULL REFERENCES users(id),
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
