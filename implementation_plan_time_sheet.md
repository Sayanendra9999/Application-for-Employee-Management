# Timesheet Feature — Implementation Plan

## Background

Adding a production-tier Timesheet system to the Enterprise Portal that allows employees to log hours, PMs to approve them, HR to correlate with attendance/payroll, and Admin to have full oversight. Every change must integrate seamlessly with the existing module architecture.

---

## Viability Analysis: Proposed Schema vs. Existing Structure

After a thorough review of the existing codebase, here is how the proposed timesheet schema fits:

### ✅ What Fits Perfectly (No Changes Needed to Existing Tables)

| Proposed Column | Maps To | Status |
|---|---|---|
| `employee_id → employees` | Existing `employees.id` | ✅ Direct FK |
| `project_id → projects` | Existing `projects.id` | ✅ Direct FK |
| `task_id → tasks` | Existing `tasks.id` | ✅ Direct FK (optional) |
| `approved_by → users` | Existing `users.id` | ✅ Same pattern as `leaves.approved_by` |
| `status` enum (Pending/Approved/Rejected) | Same pattern as `leaves.status`, `employee_expenses.status` | ✅ Consistent |
| Notification hooks | Existing `notifications` table + `create_notification()` utility | ✅ Reuse directly |
| Audit trail | Existing `audit_logs` table + `log_audit()` helpers | ✅ Reuse directly |

### ⚠️ Key Relationship Consideration

The existing schema uses **`users.id`** for task assignment (`tasks.assigned_to → users.id`) and project membership (`project_members.user_id → users.id`), but the employee table uses **`employees.id`** as PK with `employees.user_id → users.id`.

The timesheet needs **both**:
- `employee_id` → for HR/payroll correlation (maps to attendance, leaves, salary)
- Connection to `project_id` and `task_id` → for PM tracking (these use `users.id` for assignment)

**Decision:** The `timesheets` table should store `employee_id` (FK to `employees.id`) as the primary owner, since we can always resolve `user_id` via the `Employee.user_id` relationship. This keeps HR/payroll queries clean.

### ✅ Auto-Sync with `tasks.actual_hours` — Already Exists

Your existing `tasks` table already has:
```sql
actual_hours REAL DEFAULT 0.0  -- Employee's actual spent hours
```
And the PM module already has a `log_task_hours` route. The Timesheet approval workflow will **replace** direct hour logging with an audited, approval-based flow where `actual_hours` is updated only upon PM approval.

---

## User Review Required

> [!IMPORTANT]
> **Existing `log_task_hours` behavior change:** Currently, employees can directly update `tasks.actual_hours` via both the PM and Employee modules. With timesheets, should we:
> - **(A)** Remove direct hour logging entirely — all hours must go through timesheet submission/approval?
> - **(B)** Keep both — direct logging for quick updates, timesheets for formal tracking?
> 
> Recommendation: **(A)** — Single source of truth. The timesheet replaces direct hour logging.

> [!IMPORTANT]
> **Billable vs. Non-Billable hours:** Should the timesheet track whether hours are billable (for client invoicing) or non-billable (internal/admin work)? This affects the `invoices` table integration.

> [!WARNING]
> **Database migration:** Since you're using SQLite (`enterprise_portal.db`) with `db.create_all()`, adding the new table is non-destructive. However, if we modify existing columns (e.g., adding `total_timesheet_hours` to `projects`), existing data will be preserved but the column will default to 0. No data loss risk.

## Open Questions

1. **Weekly vs. Daily submission:** Should employees submit one timesheet entry per day per task, or a weekly batch? (Plan assumes daily per-task granularity — most flexible.)

2. **HR Overtime threshold:** Should the system automatically flag when `timesheet_hours > attendance_working_hours` for a given day as potential overtime? If yes, should it auto-generate `comp_offs` records?

3. **Export format preference:** CSV only, or also Excel (.xlsx)? Excel requires `openpyxl` dependency.

4. **Rejection re-submission:** When a PM rejects a timesheet, should the employee be able to edit and re-submit the same entry, or create a new one?

---

## Proposed Changes

### Phase 1: Database Schema & Model

#### [NEW] `timesheets` table in [schema.sql](file:///c:/JGpc/app_at_present/schema.sql)

```sql
CREATE TABLE IF NOT EXISTS timesheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    date DATE NOT NULL,
    hours_worked REAL NOT NULL DEFAULT 0.0,
    description TEXT DEFAULT '',
    status VARCHAR(20) DEFAULT 'Pending',       -- Pending, Approved, Rejected
    rejection_reason TEXT DEFAULT '',
    approved_by INTEGER REFERENCES users(id),
    approved_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(employee_id, project_id, task_id, date)  -- One entry per employee per project per task per day
);
```

#### [MODIFY] `Timesheet` model in [models.py](file:///c:/JGpc/app_at_present/app/models.py)

Add a new `Timesheet` SQLAlchemy model following the exact pattern of existing models (`Leave`, `EmployeeExpense`), with:
- Relationships to `Employee`, `Project`, `Task`, `User` (approver)
- `@property` helpers for display (e.g., `employee_name`, `project_name`)
- Add `timesheets` relationship to the `Employee` model backref

---

### Phase 2: Employee Space — "My Timesheets" Tab

#### [MODIFY] [services.py](file:///c:/JGpc/app_at_present/app/employee/services.py)

Add timesheet service functions following existing patterns:
- `get_my_timesheets(employee_id, status=None, date_from=None, date_to=None)` — Query with filters
- `get_my_assigned_projects(user_id)` — Get projects where employee is a member (reuses existing `get_my_projects`)
- `get_tasks_for_project(user_id, project_id)` — Get tasks assigned to user in a project
- `submit_timesheet(employee, project_id, task_id, date, hours, description, ip)` — Validates, creates entry, notifies PM
- `get_timesheet_summary(employee_id, year, month)` — Monthly totals

#### [NEW] [forms.py](file:///c:/JGpc/app_at_present/app/employee/forms.py) updates

Add `TimesheetForm` with:
- `project_id` — SelectField (populated dynamically from assigned projects)
- `task_id` — SelectField (filtered by project, optional)
- `date` — DateField
- `hours_worked` — FloatField (validators: min=0.25, max=24)
- `description` — TextAreaField

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/employee/routes.py)

Add routes:
- `GET /employee/timesheets` — List view with status/date filters
- `GET/POST /employee/timesheets/submit` — Submission form
- `GET /employee/api/tasks-for-project/<project_id>` — AJAX endpoint for dynamic task dropdown
- `GET /employee/timesheets/summary` — Monthly calendar/summary view

#### [NEW] [my_timesheets.html](file:///c:/JGpc/app_at_present/app/templates/employee/my_timesheets.html)

List view with status badges (Pending/Approved/Rejected), date range filter, matching existing Employee Space design patterns (same card layout as `my_leaves.html`).

#### [NEW] [timesheet_form.html](file:///c:/JGpc/app_at_present/app/templates/employee/timesheet_form.html)

Form template following `leave_request.html` pattern with dynamic task filtering via AJAX.

#### [MODIFY] [dashboard.html](file:///c:/JGpc/app_at_present/app/templates/employee/dashboard.html)

Add a "Timesheets" summary card showing:
- Hours logged this week/month
- Pending approvals count
- Quick-submit link

---

### Phase 3: PM Module — Timesheet Approvals

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/pm/routes.py)

Add routes:
- `GET /pm/timesheet-approvals` — Dashboard showing pending timesheets for PM's projects
- `POST /pm/timesheets/<id>/approve` — Approve + auto-sync `task.actual_hours` and project totals
- `POST /pm/timesheets/<id>/reject` — Reject with reason + notify employee
- `GET /pm/api/timesheets` — JSON API for timesheet data

Key logic on approval:
```python
# On PM approval:
timesheet.status = 'Approved'
timesheet.approved_by = current_user.id
timesheet.approved_at = datetime.utcnow()

# Auto-sync: Add hours to task's actual_hours
if timesheet.task_id:
    task = Task.query.get(timesheet.task_id)
    task.actual_hours += timesheet.hours_worked

# Notify employee
notify(employee.user_id, 'Timesheet Approved', ...)

# Check project status
project.check_and_update_status()
```

#### [NEW] [timesheet_approvals.html](file:///c:/JGpc/app_at_present/app/templates/pm/timesheet_approvals.html)

Approval dashboard with bulk approve/reject, grouped by project, matching PM dashboard styling.

#### [MODIFY] [dashboard.html](file:///c:/JGpc/app_at_present/app/templates/pm/dashboard.html)

Add "Pending Timesheet Approvals" count card with link.

---

### Phase 4: HR Module — Attendance Correlation & Payroll Sync

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/hr/routes.py)

Add routes:
- `GET /hr/timesheets` — Organization-wide timesheet view with dept/date filters
- `GET /hr/timesheets/attendance-comparison` — Side-by-side: attendance hours vs. timesheet hours per day per employee
- `GET /hr/timesheets/department-summary` — Manager view: direct reports' utilization

#### [MODIFY] [services.py](file:///c:/JGpc/app_at_present/app/hr/services.py)

Add service functions:
- `get_timesheet_attendance_comparison(employee_id, year, month)` — Returns daily comparison data
- `get_department_timesheet_summary(department_id, year, month)` — Aggregate by department
- `get_timesheet_hours_for_payroll(employee_id, month, year)` — Approved hours for payroll input

#### [MODIFY] [payroll_generate route](file:///c:/JGpc/app_at_present/app/hr/routes.py#L698-L720)

When generating payroll inputs, auto-populate `overtime_hours` from approved timesheet data that exceeds standard working hours (from `attendance_rules`).

#### [NEW] [timesheets.html](file:///c:/JGpc/app_at_present/app/templates/hr/timesheets.html) — HR timesheet overview
#### [NEW] [timesheet_comparison.html](file:///c:/JGpc/app_at_present/app/templates/hr/timesheet_comparison.html) — Attendance vs. Timesheet

#### [MODIFY] [dashboard.html](file:///c:/JGpc/app_at_present/app/templates/hr/dashboard.html)

Add timesheet-related stats card.

---

### Phase 5: Admin Module — Global Oversight & Export

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/admin/routes.py)

Add routes:
- `GET /admin/timesheets` — Global report: all timesheets with filters (date, project, status, employee)
- `POST /admin/timesheets/<id>/force-approve` — Override approval
- `POST /admin/timesheets/<id>/force-reject` — Override rejection
- `POST /admin/timesheets/<id>/edit` — Admin edit capability
- `GET /admin/timesheets/export` — CSV/Excel export with date range filters

#### [NEW] [timesheets.html](file:///c:/JGpc/app_at_present/app/templates/admin/timesheets.html) — Global report view
#### [MODIFY] [dashboard.html](file:///c:/JGpc/app_at_present/app/templates/admin/dashboard.html) — Add timesheet summary card

---

### Phase 6: Notification Hooks

All notifications use the existing `notifications` table and `create_notification()` / `notify()` helpers. No new infrastructure needed.

| Trigger | Recipient | Message |
|---|---|---|
| Employee submits timesheet | PM (via `project.assigned_pm`) | "New timesheet submitted for [Project]" |
| PM approves timesheet | Employee (via `employee.user_id`) | "Your timesheet for [Date] has been approved" |
| PM rejects timesheet | Employee | "Your timesheet for [Date] was rejected: [Reason]" |
| Admin force-approves/rejects | Both PM and Employee | "Admin override on timesheet #[ID]" |
| Weekly compliance check (optional) | HR users | "[N] employees haven't submitted timesheets this week" |

---

## File Summary

| Action | File | Description |
|---|---|---|
| MODIFY | `schema.sql` | Add `timesheets` table |
| MODIFY | `app/models.py` | Add `Timesheet` model + `Employee.timesheets` backref |
| MODIFY | `app/employee/forms.py` | Add `TimesheetForm` |
| MODIFY | `app/employee/services.py` | Add timesheet CRUD services |
| MODIFY | `app/employee/routes.py` | Add timesheet routes |
| NEW | `app/templates/employee/my_timesheets.html` | List view |
| NEW | `app/templates/employee/timesheet_form.html` | Submission form |
| MODIFY | `app/templates/employee/dashboard.html` | Add timesheet card |
| MODIFY | `app/pm/routes.py` | Add approval routes |
| NEW | `app/templates/pm/timesheet_approvals.html` | Approval dashboard |
| MODIFY | `app/templates/pm/dashboard.html` | Add pending count card |
| MODIFY | `app/hr/routes.py` | Add HR timesheet views |
| MODIFY | `app/hr/services.py` | Add comparison/payroll services |
| NEW | `app/templates/hr/timesheets.html` | HR overview |
| NEW | `app/templates/hr/timesheet_comparison.html` | Attendance vs. Timesheet |
| MODIFY | `app/templates/hr/dashboard.html` | Add stats card |
| MODIFY | `app/admin/routes.py` | Add admin oversight routes |
| NEW | `app/templates/admin/timesheets.html` | Global report |
| MODIFY | `app/templates/admin/dashboard.html` | Add summary card |
| MODIFY | `seed_data.py` | Add sample timesheet data |

---

## Verification Plan

### Automated Tests
1. Run `python app.py` — verify `db.create_all()` creates the `timesheets` table without errors
2. Run seed data script to populate test timesheets
3. Test each API endpoint via browser or curl

### Manual Verification
1. Login as Employee → Submit timesheet → Verify it appears as Pending
2. Login as PM → Approve/Reject → Verify `task.actual_hours` syncs
3. Login as HR → Verify attendance comparison view populates correctly
4. Login as Admin → Verify global view, force-approve, export functionality
5. Verify notifications appear in all relevant user inboxes

### Browser Testing
- Navigate all new routes and verify templates render without errors
- Test dynamic task dropdown via AJAX on the submission form
- Verify responsive layout matches existing Employee/PM/HR/Admin design patterns

---

## Execution Order

1. **Schema + Model** (Phase 1) — Foundation, zero risk to existing functionality
2. **Employee Submission** (Phase 2) — End-to-end for a single user
3. **PM Approval + Auto-Sync** (Phase 3) — Core business logic
4. **HR + Admin Views** (Phase 4 + 5) — Reporting layers
5. **Notification Hooks** (Phase 6) — Wired in during each phase, finalized here
6. **Seed Data + Testing** — Comprehensive validation
