# PM Module — Step 2: Estimated Hours & Employee Actual Hours Logging

## Context

This is a follow-up change to the PM module in `c:\JGpc\app_at_present`. After Step 1 (Admin creates/assigns projects to PMs), we now need to track **time estimation and actual hours** at both the project and task level.

## What to Change

1. When a project is created, Admin enters **estimated total hours** for the project.
2. When a task is created within a project, the Project Manager enters **estimated hours** for that task.
3. When an employee (assigned to a task) logs into their account, they can **manually enter actual hours spent** on the task upon completion.
4. The system tracks estimated vs actual hours so PMs and Admin can see time overruns.

---

## Step-by-step Changes

### 1. Add `estimated_hours` to Project model

**File:** `app/models.py` — `Project` class

- Add: `estimated_hours = db.Column(db.Float, default=0.0)` — total estimated hours for the entire project

**File:** `schema.sql` — `projects` table

- Add: `estimated_hours REAL DEFAULT 0.0`

**File:** Admin project creation form (from Step 1)

- Add an "Estimated Hours" number input field to the project creation form
- This field is filled by Admin when creating the project

---

### 2. Add `estimated_hours` and `actual_hours` to Task model

**File:** `app/models.py` — `Task` class

- Add: `estimated_hours = db.Column(db.Float, default=0.0)` — PM's estimate for this task
- Add: `actual_hours = db.Column(db.Float, default=0.0)` — employee's self-reported actual hours spent

**File:** `schema.sql` — `tasks` table

- Add: `estimated_hours REAL DEFAULT 0.0`
- Add: `actual_hours REAL DEFAULT 0.0`

---

### 3. Task creation form — PM enters estimated hours

**File:** `app/pm/forms.py` — `TaskForm`

- Add: `estimated_hours = FloatField('Estimated Hours', validators=[Optional()])` 

**File:** `app/pm/routes.py` — `add_task()` and `edit_task()`

- Save `form.estimated_hours.data` to `task.estimated_hours`

**File:** `app/templates/pm/task_form.html`

- Render the "Estimated Hours" field in the task creation/edit form

---

### 4. Employee logs actual hours on task completion

**File:** `app/templates/pm/project_detail.html` — Tasks section

- For each task assigned to the current user, show an **"Log Hours"** action (button or inline input)
- When clicked, show a small form/modal where the employee enters the actual hours they spent
- This should only be available to the **assigned employee** (not PMs or other members)

**File:** `app/pm/routes.py`

- Add new route: `POST /tasks/<int:task_id>/log-hours`
  - Only the assigned employee (`task.assigned_to == current_user.id`) can log hours
  - Accepts `actual_hours` (float) from the form
  - Updates `task.actual_hours`
  - Optionally auto-sets task status to "Done" if the employee is logging final hours (or keep status separate)
  - Flash success message and redirect back to project detail

---

### 5. Display estimated vs actual hours

**File:** `app/templates/pm/project_detail.html`

- Show project-level: "Estimated: X hrs" at the top
- Show project-level: "Actual (total): Y hrs" — sum of all `task.actual_hours` in the project
- In the tasks table, add two new columns:
  - "Est. Hours" — `task.estimated_hours`
  - "Actual Hours" — `task.actual_hours` (shows `—` if not yet logged)
- Highlight in red/warning if `actual_hours > estimated_hours` (overrun)

**File:** `app/templates/pm/projects.html` — projects list

- Add an "Est. Hours" column showing `project.estimated_hours`

**File:** `app/templates/pm/dashboard.html`

- No major changes needed, but optionally show total estimated vs actual hours across all visible projects

---

### 6. Seed data — add estimated and actual hours to sample data

**File:** `seed_data.py`

- Set `estimated_hours` on existing projects:
  - "Enterprise Portal" → `estimated_hours = 500`
  - "Mobile App v2" → `estimated_hours = 300`
  - "Data Analytics Dashboard" → `estimated_hours = 200`
- Set `estimated_hours` and `actual_hours` on existing tasks:
  - "Design database schema" (Done) → estimated: 40, actual: 35
  - "Implement authentication" (Done) → estimated: 60, actual: 72
  - "Build HR module" (In Progress) → estimated: 80, actual: 0
  - "Build Finance module" (In Progress) → estimated: 80, actual: 0
  - "Frontend polish" (Pending) → estimated: 50, actual: 0
  - "Wireframe design" (Pending) → estimated: 30, actual: 0

---

## What NOT to change

- Task status workflow (Pending → In Progress → Done) remains manual and separate from hour logging
- No automatic hour tracking or timers — this is manual entry only
- No changes to milestones, notifications, or member management
- No approval workflow for logged hours (employee enters, it saves directly)

---

## Verification Steps

### Setup
1. Run `python seed_data.py` to re-seed with estimated/actual hours data

### Test 1: Project has estimated hours
1. Login as `admin` / `admin123`
2. Create a new project from Admin dashboard → verify "Estimated Hours" field is present
3. Enter 100 hours, assign to a PM, submit
4. Go to PM module → open the project → verify "Estimated: 100 hrs" is displayed

### Test 2: PM creates task with estimated hours
1. Login as `pm_lead` / `pm123`
2. Open "Enterprise Portal" project → click "Add Task"
3. Verify "Estimated Hours" field is present in the task form
4. Create a task with estimated hours = 20, assign to `john_doe`
5. Verify the task appears in the task list with "Est. Hours: 20"

### Test 3: Employee logs actual hours
1. Login as `john_doe` / `john123`
2. Go to PM module → open "Enterprise Portal" project
3. Find a task assigned to John (e.g., "Build HR module") → verify "Log Hours" button is visible
4. Click "Log Hours" → enter 45 hours → submit
5. Verify the task now shows "Actual: 45 hrs" in the task list
6. Verify tasks NOT assigned to John do NOT show the "Log Hours" button

### Test 4: Overrun highlighting
1. Login as `pm_lead` / `pm123`
2. Open "Enterprise Portal" → look at task "Implement authentication"
3. Verify it shows estimated: 60, actual: 72 — and the actual hours are highlighted in red/warning (overrun)

### Test 5: Project-level totals
1. Open "Enterprise Portal" project detail
2. Verify project shows "Estimated: 500 hrs" and "Actual: [sum of all task actual hours] hrs" near the top
