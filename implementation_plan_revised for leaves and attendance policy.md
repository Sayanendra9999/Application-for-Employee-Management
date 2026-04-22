# Leave & Attendance Module Upgrade — Role-Based Policies + Shift Management

Extend the existing Enterprise Portal with enhanced Leave Policy (role-based), Shift Management, and advanced Attendance/Leave workflow features.

## Current State Summary

The app is a **Flask/SQLAlchemy** (not MERN) application with SQLite. The existing Leave/Attendance features:

| Feature | Current State |
|---|---|
| **Leave Policies** | Global (not role-based). Admin defines `leave_type + total_days + carry_forward` |
| **Attendance Rules** | Single global config row (`AttendanceRule`: `work_start`, `work_end`, `late_threshold`, etc.) — acts as a "General Shift" |
| **Leave Workflow** | Employee submits → HR approves/rejects (single step) |
| **Shifts** | ❌ No shift model — only the single `AttendanceRule` config |
| **Role/Designation Linked Policies** | ❌ Leave policies are not tied to designations |

---

## User Review Required

> [!IMPORTANT]
> **Preserving the "General Shift" Concept**: The existing `AttendanceRule` table acts as the default/general shift. Per your request, we will **keep it** as the fallback. New named shifts (Morning, Afternoon, Night) will be added as a separate `Shift` model. Employees not assigned to a specific shift will use the General (AttendanceRule) defaults.

> [!IMPORTANT]
> **Role-Based Leave Policies**: The prompt asks for leave policies per "role" (Intern, Employee, Senior, Manager). In this app, the equivalent of "role" is **Designation** (which already has levels: Junior, Mid, Senior, Lead, Head). We'll link leave policies to **Designation** so that different designation levels get different leave quotas.

> [!WARNING]
> **Database Migration**: Since this is SQLite + SQLAlchemy, any schema changes will require running `seed_data.py` to re-initialize or performing manual `ALTER TABLE` statements. We'll update `seed_data.py` with new shift/policy data.

---

## Proposed Changes

### Component 1: Database Models (`app/models.py`)

New models and model modifications to support the feature set.

---

#### [NEW] `Shift` Model

```python
class Shift(db.Model):
    __tablename__ = 'shifts'
    id, shift_name, start_time, end_time, grace_period_mins,
    min_working_hours, late_mark_after_mins, overtime_eligible,
    is_active, created_at
```

Each shift defines its own timing, grace period, late-mark rules, and OT eligibility.

#### [MODIFY] `LeavePolicy` Model

Add fields to support role-based (designation-linked) policies:

```diff
 class LeavePolicy:
+    designation_id = ForeignKey('designations.id', nullable=True)  # NULL = applies to all
+    monthly_accrual = Boolean(default=False)
+    encashment_allowed = Boolean(default=False)
+    max_per_request = Integer(default=None)        # Max days allowed per single request
+    blackout_dates = Text(default='')               # JSON list of date ranges
     # Remove UNIQUE constraint on leave_type so same type can exist for different designations
```

- If `designation_id` is `NULL` → policy is the **global default** for that leave type.
- If `designation_id` is set → policy overrides the default for employees with that designation.

#### [MODIFY] `Employee` Model

```diff
 class Employee:
+    shift_id = ForeignKey('shifts.id', nullable=True)  # NULL = General Shift
```

Add relationship to `Shift`.

#### [MODIFY] `Leave` Model

```diff
 class Leave:
+    manager_status = String(20, default='Pending')      # Manager approval step
+    manager_approved_by = ForeignKey('users.id')
+    hr_status = String(20, default='Pending')            # HR final approval
+    hr_approved_by = ForeignKey('users.id')
```

Supports the 2-step leave workflow (Manager → HR).

#### [NEW] `CompOff` Model

```python
class CompOff(db.Model):
    __tablename__ = 'comp_offs'
    id, employee_id, earned_date, hours_extra, status, used_date, is_active
```

Track compensatory offs earned from overtime work.

#### [NEW] `ShiftSwapRequest` Model

```python
class ShiftSwapRequest(db.Model):
    __tablename__ = 'shift_swap_requests'
    id, employee_id, current_shift_id, requested_shift_id, reason,
    status, reviewed_by, created_at
```

Employee can request HR to change their shift.

---

### Component 2: Schema & Seed Data

#### [MODIFY] [schema.sql](file:///c:/JGpc/app_at_present/schema.sql)
- Add `shifts` table
- Add `comp_offs` table
- Add `shift_swap_requests` table
- Modify `leave_policies` to add new columns
- Modify `employees` to add `shift_id`
- Modify `leaves` to add multi-step approval columns

#### [MODIFY] [seed_data.py](file:///c:/JGpc/app_at_present/seed_data.py)
- Create sample shifts (Morning, Afternoon, Night)
- Create designation-specific leave policies
- Assign shifts to some employees
- Add sample comp-off entries and shift swap requests

---

### Component 3: Admin Module — Shift & Policy Management

#### [MODIFY] [config_forms.py](file:///c:/JGpc/app_at_present/app/admin/config_forms.py)
- Add `ShiftForm` — create/edit shifts with all fields
- Modify `LeavePolicyForm` — add designation dropdown, accrual, encashment, max_per_request, blackout

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/admin/routes.py)
- Add CRUD routes for shifts: `/shifts`, `/shifts/add`, `/shifts/<id>/edit`
- Update leave policy routes to handle designation linkage
- Pass `total_shifts` to dashboard

#### [NEW] `admin/shifts.html` — List all shifts
#### [NEW] `admin/shift_form.html` — Create/edit shift
#### [MODIFY] `admin/dashboard.html` — Add Shifts link in HR Configuration card
#### [MODIFY] `admin/leave_policy_form.html` — Add new fields
#### [MODIFY] `admin/leave_policies.html` — Show designation column

---

### Component 4: HR Module — Shift Assignment, Enhanced Leave/Attendance

#### [MODIFY] [services.py](file:///c:/JGpc/app_at_present/app/hr/services.py)
- `get_attendance_rules_for_employee(emp_id)` — returns shift-specific or general rules
- `perform_checkin()` / `perform_checkout()` — use employee's assigned shift rules
- `validate_leave_request()` — check blackout dates, max_per_request
- `auto_mark_absent()` — mark absent if no login and no approved leave
- `calculate_comp_off()` — earn comp-off from overtime
- `approve_leave()` — multi-step (manager → HR)
- `initialize_leave_balances()` — use designation-specific policies
- Night shift handling in attendance calc

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/hr/routes.py)
- Shift assignment when editing employee
- Leave approval with multi-step workflow
- Attendance override endpoint
- Shift swap request management
- Comp-off listing/approval

#### [MODIFY] [forms.py](file:///c:/JGpc/app_at_present/app/hr/forms.py)
- Add `shift_id` to `EmployeeForm`
- Add `AttendanceOverrideForm`

#### [NEW] `hr/shift_swap_requests.html`
#### [NEW] `hr/comp_offs.html`
#### [MODIFY] `hr/employee_form.html` — Add shift dropdown
#### [MODIFY] `hr/leaves.html` — Show multi-step approval status
#### [MODIFY] `hr/attendance_checkin.html` — Show employee's shift info

---

### Component 5: Employee Module — View Shift, Enhanced Dashboard

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/employee/routes.py)
- Add shift swap request route
- Show shift info on dashboard

#### [MODIFY] [services.py](file:///c:/JGpc/app_at_present/app/employee/services.py)
- `get_my_shift()` — fetch assigned shift
- `submit_shift_swap_request()` — request shift change
- `get_my_comp_offs()` — fetch earned comp-offs

#### [MODIFY] `employee/dashboard.html` — Show shift timing, comp-off balance
#### [NEW] `employee/shift_swap.html` — Submit shift swap request

---

### Component 6: Documentation

#### [NEW] `admin_hr_employee_LA_changes.md`
Full change documentation explaining all modifications made to each module.

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Designation = Role** | The app already has `Designation` with levels (1-5). Creating a separate `Role` table would duplicate this. We use designation as the role concept. |
| **General Shift preserved** | The `AttendanceRule` config stays as the default fallback. Named shifts are optional overrides. |
| **Multi-step leave approval** | Added `manager_status` and `hr_status` columns to `Leave`. The old `status` column becomes the final status. |
| **Blackout dates as JSON text** | Simple approach; stored as a JSON string of date ranges to avoid a separate table. |
| **Night shift handling** | Attendance stored against login date; `calc_working_hours()` updated to handle cross-midnight math. |

---

## Verification Plan

### Automated Tests
1. Run `python seed_data.py` — confirm all new tables created and seeded
2. Run `python app.py` — confirm app starts without errors
3. Test via browser:
   - Admin: Create shifts, link leave policies to designations
   - HR: Assign shifts to employees, process multi-step leaves
   - Employee: View shift, apply leave, check comp-offs

### Manual Verification
- Login as each role and verify the dashboards show correct shift/leave data
- Test night shift attendance calculation (login Day 1, logout Day 2)
- Test auto-absent marking logic
- Verify comp-off earning from overtime
