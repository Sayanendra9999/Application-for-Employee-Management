# Production-Level HR Module Upgrade

## Background

The current HR module is a basic CRUD (5 routes, 2 forms, 5 templates). This plan upgrades it into a production-grade HR system where **Admin defines rules** and **HR executes operations** based on those rules.

**Key principle:** Admin owns configuration (departments, roles, policies). HR consumes those configurations — never duplicates them.

---

## User Review Required

> [!IMPORTANT]
> **New Admin configuration tables** will be added (Department, Designation, LeavePolicy, AttendanceRule). This changes the Admin module's scope from "user management only" to "user management + HR configuration".

> [!WARNING]
> **Database will be re-seeded.** The `seed_data.py` will be updated with sample departments, designations, leave policies, and HR data. Existing test data will be recreated.

> [!IMPORTANT]
> **File uploads** for Document Management will be stored in `static/uploads/documents/`. This directory will be auto-created. Max file size: 5MB.

---

## Proposed Changes

### Component 1: Admin Module — Configuration Tables

Admin becomes the **rule engine**. HR reads these tables but never writes to them.

#### [NEW] New Database Models (added to `models.py`)

| Model | Purpose | Key Fields |
|---|---|---|
| `Department` | Org structure | name, code, description, is_active |
| `Designation` | Job roles | title, department_id (FK), level, is_active |
| `LeavePolicy` | Leave rules | leave_type, total_days, carry_forward, is_active |
| `AttendanceRule` | Work hours | work_start, work_end, late_threshold_mins, half_day_hours, full_day_hours |
| `AuditLog` | Track all changes | user_id, action, entity_type, entity_id, details, timestamp |

#### [MODIFY] [models.py](file:///c:/JGpc/app_at_present/app/models.py)
- Add 5 new models above
- Modify `Employee`: change `department` (string) → `department_id` (FK to Department), `designation` (string) → `designation_id` (FK to Designation)
- Add `LeaveBalance` model to track per-employee per-leave-type balances
- Add `PerformanceReview`, `PayrollInput`, `JobPosting`, `Candidate`, `Interview`, `EmployeeDocument` models

#### [MODIFY] [admin/routes.py](file:///c:/JGpc/app_at_present/app/admin/routes.py)
- Add CRUD routes for: Departments, Designations, Leave Policies, Attendance Rules
- Each is a simple list + add/edit page

#### [NEW] admin/config_forms.py
- Forms for Department, Designation, LeavePolicy, AttendanceRule

#### [NEW] admin templates (4 new templates)
- `admin/departments.html` — list + add/edit
- `admin/designations.html` — list + add/edit
- `admin/leave_policies.html` — list + add/edit
- `admin/attendance_rules.html` — list + add/edit

#### [MODIFY] [admin/dashboard.html](file:///c:/JGpc/app_at_present/app/templates/admin/dashboard.html)
- Add quick links to new configuration pages

---

### Component 2: HR Module — Production Upgrade

Restructured into clean sub-modules with services layer.

#### New HR folder structure:
```
app/hr/
├── __init__.py              # Blueprint
├── routes.py                # All HR routes (employees, attendance, leaves, etc.)
├── forms.py                 # All HR forms
└── services.py              # Business logic (leave validation, attendance calc, etc.)
```

#### HR Feature Breakdown:

**1. Employee Management** (upgrade existing)
- Department/Designation now come from Admin-defined dropdowns
- Employee profile view page (detailed card)
- Search/filter employees

**2. Attendance System** (new)
- Check-in / Check-out for employees
- Auto-calculate working hours
- Apply Admin-configured attendance rules (late threshold, half-day detection)
- Monthly attendance summary view
- Attendance report with filters (date range, department, status)

**3. Leave Management** (upgrade existing)
- Leave balance tracking per employee per leave type
- Validate leave against Admin-defined policies (max days, balance check)
- Auto-deduct balance on approval
- Leave calendar view
- Bulk approve/reject

**4. Performance Management** (new)
- Create review cycles (quarterly/annual)
- Manager submits ratings (1-5 scale) + written feedback
- Employee can view their reviews
- Performance summary per employee

**5. Recruitment** (new)
- Create job postings (linked to Admin departments + designations)
- Add candidates with resume info
- Track interview stages (Applied → Screening → Interview → Offer → Hired/Rejected)
- Interview scheduling and feedback

**6. Payroll Input** (new — HR side only)
- Generate monthly payroll input for Finance
- Auto-pulls: attendance summary, leaves taken
- HR adds: bonuses, deductions, notes
- Status: Draft → Submitted (to Finance)
- Does NOT calculate salary — Finance handles that

**7. Document Management** (new)
- Upload employee documents (ID proof, offer letter, etc.)
- Document type categorization
- View/download documents

#### [MODIFY] HR Routes — expanded from 6 routes to ~30 routes
#### [MODIFY] HR Forms — expanded from 2 forms to ~12 forms
#### [NEW] HR Services — `services.py` for business logic
#### [NEW] HR Templates — 18 new templates (from current 5 to ~23)

```
templates/hr/
├── dashboard.html           # Enhanced with more stats + charts
├── employees.html           # List with search filter
├── employee_form.html       # Create/edit with Admin dropdowns
├── employee_detail.html     # [NEW] Profile card view
├── attendance.html          # [UPGRADED] With filters + summary
├── attendance_checkin.html  # [NEW] Check-in/out form
├── attendance_report.html   # [NEW] Monthly report
├── leaves.html              # [UPGRADED] With balance info
├── leave_balances.html      # [NEW] Balance overview
├── performance.html         # [NEW] Review list
├── performance_form.html    # [NEW] Submit review
├── performance_detail.html  # [NEW] View review
├── recruitment.html         # [NEW] Job postings list
├── job_form.html            # [NEW] Create/edit job
├── candidates.html          # [NEW] Candidate list
├── candidate_form.html      # [NEW] Add/edit candidate
├── interview_form.html      # [NEW] Schedule interview
├── payroll_input.html       # [NEW] Monthly payroll prep
├── payroll_form.html        # [NEW] Edit payroll input
├── documents.html           # [NEW] Document list
├── document_upload.html     # [NEW] Upload form
```

---

### Component 3: Seed Data Update

#### [MODIFY] [seed_data.py](file:///c:/JGpc/app_at_present/seed_data.py)
- Add departments: Engineering, Human Resources, Finance, Marketing, Operations
- Add designations per department
- Add leave policies: Casual (12), Sick (10), Earned (15)
- Add attendance rules: 09:00–18:00, 15min late threshold
- Add leave balances for all employees
- Add sample performance reviews
- Add sample job postings and candidates
- Add sample payroll input records

---

### Component 4: Supporting Infrastructure

#### [MODIFY] [config.py](file:///c:/JGpc/app_at_present/config.py)
- Add `UPLOAD_FOLDER` and `MAX_CONTENT_LENGTH` (5MB) for document uploads

#### [MODIFY] [decorators.py](file:///c:/JGpc/app_at_present/app/decorators.py)
- Add `@hr_required` decorator (shortcut for `@module_required('hr')`)

#### [MODIFY] [style.css](file:///c:/JGpc/app_at_present/static/css/style.css)
- Add styles for: employee detail cards, tabbed navigation, document list, performance stars, recruitment pipeline

---

## Open Questions

> [!IMPORTANT]
> **Scope confirmation:** This plan adds ~40 new files and ~15 new database tables. The implementation will take multiple steps. Should I proceed with all 7 HR features, or would you prefer to start with a subset (e.g., Employee + Attendance + Leaves first)?

---

## Verification Plan

### Automated Tests
- Re-seed database and verify all tables are created
- Run `python app.py` and verify no import errors
- Browser test: login as admin → verify new config pages
- Browser test: login as HR → verify all new HR features

### Manual Verification
- Create a department in Admin → verify it appears in HR employee form
- Submit a leave request → verify policy validation works
- Check-in/out → verify working hours calculation
- Submit payroll input → verify it doesn't calculate salary
