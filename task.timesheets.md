# Timesheet System Implementation — Task Tracker

## Phase 1: Schema & Model Setup
- [x] Create `timesheets` table in `schema.sql`
- [x] Add `Timesheet` SQLAlchemy model in `app/models.py`
- [x] Add `employee.timesheets` relationship
- [x] Deprecate `pm.log_task_hours` route
- [x] Deprecate `employee.log_task_hours` route
- [x] Remove old Log Hours modals from all templates

## Phase 2: Employee Space (Submission)
- [x] Create `TimesheetForm` in `app/employee/forms.py`
- [x] Add timesheet services in `app/employee/services.py`
  - [x] `get_my_timesheets()` with filters
  - [x] `get_assigned_projects_for_employee()`
  - [x] `get_tasks_for_project_user()`
  - [x] `submit_timesheet()` with validation & re-submit logic
  - [x] `get_timesheet_summary()` (monthly stats)
  - [x] `get_weekly_timesheet_hours()`
- [x] Add employee routes
  - [x] `my_timesheets` — list with filters
  - [x] `submit_timesheet` — form with AJAX task dropdown
  - [x] `api_tasks_for_project` — AJAX endpoint
- [x] Create templates
  - [x] `employee/my_timesheets.html`
  - [x] `employee/timesheet_form.html`
- [x] Update employee dashboard with timesheet summary card

## Phase 3: PM Module (Approvals)
- [x] Add `Timesheet` to PM model imports
- [x] Add pending timesheet count to PM dashboard
- [x] Add PM dashboard stat card for pending timesheets
- [x] Add PM routes
  - [x] `timesheet_approvals` — list with filters
  - [x] `approve_timesheet` — approve + auto-sync `task.actual_hours`
  - [x] `reject_timesheet` — reject with reason
  - [x] `bulk_approve_timesheets` — batch approve
- [x] Create `pm/timesheet_approvals.html` template

## Phase 4: HR Module (Oversight)
- [x] Add `Timesheet` to HR model imports
- [x] Add timesheet stats to HR dashboard context
- [x] Add HR routes
  - [x] `timesheets` — organization-wide view with department/status/date filters
  - [x] `timesheet_attendance_comparison` — side-by-side with overtime flags
- [x] Create templates
  - [x] `hr/timesheets.html`
  - [x] `hr/timesheet_comparison.html`

## Phase 5: Admin Module (Global Oversight)
- [x] Add `Timesheet` to Admin model imports
- [x] Add timesheet counts to Admin dashboard context
- [x] Add Admin routes
  - [x] `timesheets` — global report with all filters
  - [x] `force_approve_timesheet` — admin override approve
  - [x] `force_reject_timesheet` — admin override reject (with hour reversal)
  - [x] `export_timesheets` — CSV and Excel export
- [x] Create `admin/timesheets.html` template

## Phase 6: Verification
- [x] App starts cleanly with `db.create_all()`
- [x] All 12 timesheet routes registered
- [x] No old `log_task_hours` template references remain
- [ ] Add sidebar navigation links for timesheets
- [ ] End-to-end functional testing with seed data
