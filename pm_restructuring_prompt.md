# PM Module — Step 1: Admin Creates & Assigns Projects, PM Sees Only Theirs

## Context

The Enterprise Portal (`c:\JGpc\app_at_present`) is a Flask app. The PM module currently has a **flat** structure — anyone with `pm` module access sees all projects and can create projects. There is no concept of project ownership by a specific Project Manager.

## What to Change

**Core change:** Move project creation from PM module to the **Admin dashboard**. Admin creates projects and assigns each to a specific employee (who becomes the Project Manager). When that PM logs into the PM module, they see **only their assigned projects**. Admin sees **all projects** in PM module since they are a super user. Remove the "Add Project" option from the PM module entirely.

---

## Step-by-step Changes

### 1. Add `assigned_pm` column to `Project` model

**File:** `app/models.py` — `Project` class

- Add: `assigned_pm = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)`
- Add relationship: `pm_owner = db.relationship('User', foreign_keys=[assigned_pm])`
- Keep existing `created_by` as-is (will always be Admin)

**File:** `schema.sql` — `projects` table

- Add: `assigned_pm INTEGER REFERENCES users(id)` to match the model

---

### 2. Move project creation to Admin dashboard

**File:** `app/admin/routes.py`

- Add new route `GET/POST /admin/projects/add` — project creation form with:
  - All existing project fields (name, description, start_date, end_date, deadline, status)
  - New field: "Assign to Project Manager" — dropdown of employees/users who have the `pm` module assigned
  - On submit: create the project with `created_by = current_user.id` (admin) and `assigned_pm = selected_user_id`
- Add new route `GET /admin/projects` — list all projects with their assigned PMs (optional, for admin management)

**File:** `app/admin/forms.py` or `app/admin/config_forms.py`

- Add `AdminProjectForm` with all project fields + `assigned_pm = SelectField('Assign to Project Manager', coerce=int)`

**File:** `app/templates/admin/dashboard.html`

- Add a "Create Project" link/button in a suitable card (e.g., alongside User Management and HR Configuration cards), linking to `/admin/projects/add`

**File:** `app/templates/admin/project_form.html` — **[NEW]**

- Project creation form template for admin, including the "Assign to Project Manager" dropdown

---

### 3. Remove project creation from PM module

**File:** `app/pm/routes.py`

- Remove or disable the `add_project()` route. If keeping the route, restrict it to return 403 for non-admin users (or remove entirely).
- Remove `edit_project()` and `delete_project()` routes for non-admin users (PMs should not delete/edit project-level settings — only manage tasks/members within their project).

**File:** `app/templates/pm/dashboard.html`

- Remove the "New Project" button (`<a href="{{ url_for('pm.add_project') }}"...>`)

**File:** `app/templates/pm/projects.html`

- Remove any "Add Project" / "New Project" button

**File:** `app/templates/pm/project_detail.html`

- Remove "Edit Project" and "Delete Project" buttons for non-admin users
- Admin can still edit/delete if needed

---

### 4. PM dashboard — scope projects to assigned PM

**File:** `app/pm/routes.py` — `dashboard()` route

- If `current_user.is_admin` → show **all projects** (super user sees everything)
- Else → query only `Project.query.filter_by(assigned_pm=current_user.id)`
- All stat counts (total_projects, active_projects, pending_tasks, overdue_tasks, etc.) must be **scoped** to these filtered projects only
- Recent projects list must also be scoped

**File:** `app/pm/routes.py` — `projects()` route

- Same scoping logic: admin sees all, PM sees only `assigned_pm == current_user.id`

---

### 5. Project detail page — show assigned PM

**File:** `app/templates/pm/project_detail.html`

- Display "Project Manager: {{ project.pm_owner.full_name }}" prominently near the top (if assigned)

---

### 6. Seed data — add a test Project Manager user

**File:** `seed_data.py`

- Add a new user:
  ```
  username: pm_manager
  email: pm_manager@company.com
  full_name: Amit Kumar
  password: pm_mgr123
  modules: ['pm', 'employee']
  ```
- Create an Employee record for this user
- Set `assigned_pm` on existing projects:
  - "Enterprise Portal" → assigned to `pm_lead` (Rahul Verma)
  - "Mobile App v2" → assigned to `pm_manager` (Amit Kumar)
  - "Data Analytics Dashboard" → assigned to `pm_lead` (Rahul Verma)
- All projects should have `created_by = admin` (since admin creates all projects now)

---

## What NOT to change (leave for later steps)

- No changes to Admin dashboard PM Overview (future step)
- No changes to team member scoping (members see all projects for now)
- No changes to task assignment dropdown (keep showing all users for now)
- No changes to member add/remove permissions
- No Team Lead permissions changes

---

## Verification Steps

### Setup
1. Run `python seed_data.py` to re-seed the database with new data

### Test 1: Admin creates a project from Admin dashboard
1. Login as `admin` / `admin123`
2. Go to **Admin dashboard** → verify a "Create Project" link/button is visible
3. Click it → verify the project form appears with an **"Assign to Project Manager"** dropdown
4. Verify the dropdown lists PM-module users: Rahul Verma, Amit Kumar, John Doe (all users with `pm` module)
5. Fill in project details, assign to **Amit Kumar**, submit
6. Verify project is created successfully with a flash message

### Test 2: PM module — no "Add Project" for anyone
1. Still logged in as `admin` → go to **PM module dashboard**
2. Verify the "New Project" button is **removed**
3. Go to PM projects list → verify no "Add Project" button exists
4. Logout

### Test 3: Project Manager sees only their projects
1. Login as `pm_manager` / `pm_mgr123`
2. Go to PM module dashboard → verify **only "Mobile App v2"** and the newly created project (from Test 1) appear
3. Verify stats (total projects, active, tasks, etc.) reflect **only** these projects
4. Verify "New Project" button is **not visible**
5. Click into "Mobile App v2" → verify project detail loads, shows "Project Manager: Amit Kumar"
6. Verify PM can still add team members, create tasks, and manage milestones within this project
7. Logout

### Test 4: Another PM sees only their projects
1. Login as `pm_lead` / `pm123`
2. Go to PM dashboard → verify **only "Enterprise Portal" and "Data Analytics Dashboard"** appear
3. Verify "Mobile App v2" is **NOT visible**
4. Verify stats are scoped to only these 2 projects
5. Logout

### Test 5: Admin sees all projects in PM module
1. Login as `admin` / `admin123`
2. Go to PM module dashboard → verify **all projects** appear (Enterprise Portal, Mobile App v2, Data Analytics Dashboard, and any created in Test 1)
3. Verify stats reflect **all** projects in the system
4. Click into any project → verify project detail loads with assigned PM name shown
5. Logout

### Test 6: Non-PM user cannot see PM dashboard
1. Login as `jane_smith` / `jane123` (Finance user, no `pm` module)
2. Try navigating to PM dashboard URL directly → verify access is denied / redirected
