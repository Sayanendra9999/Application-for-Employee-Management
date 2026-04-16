# HR Module — Production Upgrade Walkthrough

## Overview

The HR module has been upgraded from a basic prototype (5 routes, 2 forms) into a production-grade system with **15 routes**, **6 forms**, a **services layer**, and full integration with Admin-configured policies.

**Key Principle:** Admin defines rules → HR executes operations based on those rules.

---

## Architecture

```
app/hr/
├── __init__.py          # Blueprint registration
├── routes.py            # 15 routes (dashboard, employees, attendance, leaves)
├── forms.py             # 6 forms (Employee, LeaveAction, CheckInOut, Filter, Balance)
└── services.py          # Business logic layer (attendance rules, leave validation)
```

---

## Features Implemented (Batch 1)

### 1. Employee Management — UPGRADED

| Before | After |
|---|---|
| Free-text department/designation | **Dropdown from Admin-configured** departments & designations |
| No search/filter | **Department filter + name/code search** |
| No detail page | **Employee profile card** with leave balances, recent attendance, recent leaves |
| No dynamic designation | **AJAX-powered** designation dropdown that changes based on selected department |

**Routes:**
- `GET /hr/employees` — List with filters
- `GET/POST /hr/employees/add` — Create (Admin dropdowns)
- `GET/POST /hr/employees/<id>/edit` — Edit (Admin dropdowns)
- `GET /hr/employees/<id>` — Detail/profile page
- `GET /hr/api/designations/<dept_id>` — API for dynamic dropdown

**When employee is created:** Leave balances are automatically initialized from Admin-defined leave policies.

---

### 2. Attendance System — NEW

| Feature | Details |
|---|---|
| **Check-in / Check-out** | HR records employee check-in/out with time |
| **Working hours calculation** | Auto-calculated from check-in to check-out |
| **Late detection** | Applies Admin-configured late threshold (default: 15 mins after 09:00) |
| **Half-day detection** | Auto-detects based on Admin-configured minimum hours (default: 4h) |
| **Attendance records** | Filterable by department, status, date range |
| **Monthly report** | Summary per employee: present, late, absent, half-day, total hours, effective days |
| **Admin rules display** | Every attendance page shows the active Admin rules |

**Routes:**
- `GET /hr/attendance` — Records with filters
- `GET/POST /hr/attendance/check-in` — Check-in/out form + today's status
- `GET /hr/attendance/report` — Monthly summary report

**How it works:**
```
Admin sets: work_start=09:00, late_threshold=15min, half_day_hours=4.0
    ↓
HR checks in employee at 10:30 → System marks "Late" (30 > 15 threshold)
    ↓
HR checks out at 13:00 → 2.5 hours < 4.0 → System marks "Half-Day"
```

---

### 3. Leave Management — UPGRADED

| Before | After |
|---|---|
| Hardcoded leave types (Casual, Sick, Earned) | **Dynamic from Admin leave policies** |
| No balance tracking | **Per-employee per-type balance tracking** with used/remaining |
| No policy validation | **Full validation**: balance check, overlap detection, weekend exclusion |
| No rejection reason | **Rejection reason** captured via prompt |
| No balance deduction | **Auto-deduct** balance on approval |

**Routes:**
- `GET /hr/leaves` — Leave list with status filter
- `POST /hr/leaves/<id>/action` — Approve/reject with balance management
- `GET /hr/leave-balances` — All employees' balances overview

**Validation flow (in services.py):**
```
Employee submits leave request
    ↓
1. Check policy exists and is active
2. Calculate working days (exclude weekends)
3. Check leave balance (remaining >= requested)
4. Check for overlapping approved/pending leaves
    ↓
If valid → Submit as Pending
HR approves → Balance auto-deducted
HR rejects → No balance change, reason recorded
```

---

## Services Layer

All business logic lives in `app/hr/services.py`, not in routes. This keeps routes thin and logic testable.

| Service | Purpose |
|---|---|
| `get_attendance_rules()` | Fetches Admin-configured attendance rules |
| `perform_checkin()` | Check-in with late detection |
| `perform_checkout()` | Check-out with working hours + half-day detection |
| `get_attendance_summary()` | Monthly summary for payroll input |
| `get_leave_balance()` | Single employee's balance for a leave type |
| `initialize_leave_balances()` | Creates balances from Admin policies |
| `validate_leave_request()` | Full leave validation against policies |
| `approve_leave()` | Approve + deduct balance |
| `reject_leave()` | Reject + record reason |
| `get_departments_for_dropdown()` | Admin departments for forms |
| `get_designations_for_dropdown()` | Admin designations for forms |
| `log_audit()` | Audit trail logging |

---

## Employee Module Changes

The Employee module (`app/employee/`) also received updates:
- **Leave request** now validates against Admin policies (balance check, overlap detection)
- **Leave types** loaded dynamically from Admin leave policies (not hardcoded)
- **Leave balances** shown on employee dashboard and leaves page
- **Leave days** calculated excluding weekends

---

## Files Modified/Created

| File | Status |
|---|---|
| `app/models.py` | Modified — Added Department, Designation, LeavePolicy, AttendanceRule, AuditLog, LeaveBalance + batch2 stubs |
| `app/hr/routes.py` | Rewritten — 6 routes → 15 routes |
| `app/hr/forms.py` | Rewritten — 2 forms → 6 forms |
| `app/hr/services.py` | **New** — Business logic layer |
| `app/employee/routes.py` | Modified — Policy validation + balance tracking |
| `app/employee/forms.py` | Modified — Dynamic leave types |
| `app/templates/hr/dashboard.html` | Rewritten — Dept breakdown, attendance stats, admin rules |
| `app/templates/hr/employees.html` | Rewritten — Filters, search, view action |
| `app/templates/hr/employee_form.html` | Rewritten — Admin dropdowns, dynamic AJAX |
| `app/templates/hr/employee_detail.html` | **New** — Profile card page |
| `app/templates/hr/attendance.html` | Rewritten — Filters, working hours, rules banner |
| `app/templates/hr/attendance_checkin.html` | **New** — Check-in/out form |
| `app/templates/hr/attendance_report.html` | **New** — Monthly summary report |
| `app/templates/hr/leaves.html` | Rewritten — Status filter, rejection reason |
| `app/templates/hr/leave_balances.html` | **New** — Balance overview |
| `seed_data.py` | Rewritten — Departments, designations, policies, balances |
| `static/css/style.css` | Modified — Module checkbox grid styles |
