# PM Module Upgrade — Complete Walkthrough

## Overview

The **Project Manager (PM) module** has been upgraded from a basic project/task tracker into a
**production-grade project management system** with milestones, notifications, progress tracking,
team roles, and REST APIs. This document covers every change made, the impact on the Admin module,
and all API endpoints.

---

## Table of Contents

1. [What Changed in the PM Module](#1-pm-module-changes)
2. [What Changed in the Admin Module](#2-admin-module-changes)
3. [Database Schema Changes](#3-database-schema-changes)
4. [API Endpoints Reference](#4-api-endpoints)
5. [Files Modified / Created](#5-file-manifest)
6. [Bug Fixes Applied](#6-bug-fixes)
7. [Integration Points](#7-integration-points)

---

## 1. PM Module Changes

### 1.1 Project Lifecycle (UPGRADED)

| Before | After |
|--------|-------|
| Status: `Planning`, `In Progress`, `On Hold`, `Completed` | Status: `Not Started`, `In Progress`, `On Hold`, `Completed` |
| No deadline field | `deadline` field added (hard deadline separate from end_date) |
| No duplicate check | **Unique project name** enforced (case-insensitive) |
| No progress tracking | Auto-calculated **progress %** based on completed tasks |
| No delay detection | `is_delayed` flag when past deadline |
| No `updated_at` tracking | `updated_at` auto-updated on changes |

**Route changes:**
- `POST /pm/projects/<id>/delete` — **NEW** route to delete a project (cascades to tasks, members, milestones)
- Duplicate name check on both `add_project` and `edit_project`

### 1.2 Team Assignment (UPGRADED)

| Before | After |
|--------|-------|
| Roles: `Member`, `Lead`, `Observer` | Roles: `Developer`, `Tester`, `Designer`, `Lead`, `Observer` |
| No notification on assignment | Employee notified when added/removed |
| No `joined_at` tracking | `joined_at` timestamp added |

### 1.3 Task Management (UPGRADED)

| Before | After |
|--------|-------|
| Status: `To Do`, `In Progress`, `Done` | Status: `Pending`, `In Progress`, `Done` |
| No notification on assignment | Employee notified when task assigned or updated |
| No notification on completion | PM creator notified when task marked Done |
| No `updated_at` tracking | `updated_at` auto-updated on changes |
| No audit logging | All CRUD logged to `audit_logs` |

### 1.4 Milestones (NEW)

Each project can have milestones with:
- **Title** (unique per project)
- **Description**
- **Deadline**
- **Status**: `Pending`, `In Progress`, `Completed`
- **Overdue detection**: `is_overdue` flag

**Routes:**
| Method | URL | Description |
|--------|-----|-------------|
| GET/POST | `/pm/projects/<id>/milestones/add` | Create milestone |
| GET/POST | `/pm/milestones/<id>/edit` | Edit milestone |
| POST | `/pm/milestones/<id>/delete` | Delete milestone |

### 1.5 Progress Tracking (NEW)

- **Auto-calculated** on `Project.progress` property
- Formula: `(tasks with status Done / total tasks) × 100`
- Displayed as a **visual progress bar** in:
  - PM Dashboard (recent projects table)
  - Projects list
  - Project detail page

### 1.6 PM Dashboard (UPGRADED)

**Before:** 6 stat cards (total projects, active, total tasks, done, in progress, overdue)

**After:** 8 stat cards in 2 rows:

| Row | Cards |
|-----|-------|
| Row 1 | Total Projects · Active Projects · Completed · On Hold |
| Row 2 | Pending Tasks · Tasks Completed · Overdue Tasks · Milestones Done |

**Additional changes:**
- Notification banner (shows unread count with link to notifications page)
- Progress bar column in Recent Projects table
- Deadline column with delay indicators (red icon)

### 1.7 Notifications (NEW)

**Notification model** (`notifications` table):
- `user_id` — recipient
- `title`, `message` — content
- `category` — `info`, `success`, `warning`, `danger`
- `is_read` — read/unread state
- `link` — optional URL to relevant page

**Events that trigger notifications:**

| Event | Recipient | Category |
|-------|-----------|----------|
| Employee added to project | Employee | info |
| Employee removed from project | Employee | warning |
| Task assigned to employee | Employee | info |
| Task reassigned to new employee | New employee | info |
| Task status changed | Assigned employee | info |
| Task marked Done | Project creator (PM) | success |
| Project delayed | Project creator (PM) | warning |
| Milestone completed | Project creator (PM) | success |

**Notification routes:**
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/pm/notifications` | View all notifications |
| POST | `/pm/notifications/<id>/read` | Mark single notification as read |
| POST | `/pm/notifications/mark-all-read` | Mark all as read |

---

## 2. Admin Module Changes

### What Stayed the Same ✅

| Feature | Status |
|---------|--------|
| User CRUD (create, edit, deactivate) | **Unchanged** |
| Auto-generated passwords (Welcome@XXXX) | **Unchanged** |
| Module assignment checkboxes | **Unchanged** |
| Password reset | **Unchanged** |
| Department management | **Unchanged** |
| Designation management | **Unchanged** |
| Leave policy management | **Unchanged** |
| Attendance rules | **Unchanged** |
| Audit log viewer | **Unchanged** |

### What Changed ➕

#### 2.1 Admin Dashboard — New "PM Overview" Card

The Admin dashboard previously had **2 quick-link cards** (User Management + HR Configuration).
Now it has **3 quick-link cards**:

```
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│  User Management  │  │  HR Configuration │  │   PM Overview     │  ← NEW
│  · Manage Users   │  │  · Departments    │  │  · Active Proj.   │
│                   │  │  · Designations   │  │  · Completed Proj.│
│                   │  │  · Leave Policies │  │  · Pending Tasks  │
│                   │  │  · Attend. Rules  │  │  · Milestones     │
│                   │  │                   │  │  · Audit Logs     │
└───────────────────┘  └───────────────────┘  └───────────────────┘
```

#### 2.2 Admin Routes — New Variables Passed to Dashboard

**Before (`admin/routes.py` → `dashboard()`):**
```python
total_projects, total_tasks
```

**After:**
```python
total_projects, active_projects, completed_projects,
total_tasks, pending_tasks,
total_milestones, total_notifications
```

#### 2.3 Admin Routes — New Model Imports

```diff
 from app.models import (User, Module, UserModule, Employee, Project, Task,
+                        Milestone, Notification,
                         Department, Designation, LeavePolicy, AttendanceRule, AuditLog)
```

#### 2.4 Audit Logging for PM Actions

All PM CRUD operations now write to the shared `audit_logs` table (which the Admin module
already reads). New entity types visible in the Admin Audit Log viewer:

| Entity Type | Actions |
|-------------|---------|
| `Project` | CREATE, UPDATE, DELETE |
| `ProjectMember` | CREATE, DELETE |
| `Task` | CREATE, UPDATE, DELETE |
| `Milestone` | CREATE, UPDATE, DELETE |

#### 2.5 Admin Dashboard Template

| Change | Detail |
|--------|--------|
| Layout | 2-column → **3-column** quick-link section |
| New card | "PM Overview" showing active/completed projects, pending tasks, milestones |
| Audit Logs link | Moved from HR Configuration card to PM Overview card |

### No Admin Routes Were Added or Removed

The PM module upgrade did **not** add any new routes to the Admin module. It only:
1. Added new imports (`Milestone`, `Notification`)
2. Added new query variables to the existing `dashboard()` route
3. Updated the existing `admin/dashboard.html` template

---

## 3. Database Schema Changes

### New Tables

#### `milestones`
```sql
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
```

#### `notifications`
```sql
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
```

### Modified Tables

#### `projects` (modified)
```diff
- name VARCHAR(150) NOT NULL,
+ name VARCHAR(150) NOT NULL UNIQUE,
+ deadline DATE,
- status VARCHAR(30) DEFAULT 'Planning',
+ status VARCHAR(30) DEFAULT 'Not Started',
+ updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
```

#### `project_members` (modified)
```diff
- role VARCHAR(50) DEFAULT 'Member',
+ role VARCHAR(50) DEFAULT 'Developer',
+ joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
```

#### `tasks` (modified)
```diff
- status VARCHAR(20) DEFAULT 'To Do',
+ status VARCHAR(20) DEFAULT 'Pending',
+ updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
```

---

## 4. API Endpoints

### Web UI Routes (HTML)

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/pm/` | PM Dashboard |
| GET | `/pm/projects` | Projects list (with status filter) |
| GET/POST | `/pm/projects/add` | Create project |
| GET | `/pm/projects/<id>` | Project detail |
| GET/POST | `/pm/projects/<id>/edit` | Edit project |
| POST | `/pm/projects/<id>/delete` | Delete project |
| POST | `/pm/projects/<id>/add-member` | Add team member |
| POST | `/pm/projects/<id>/remove-member/<mid>` | Remove team member |
| GET/POST | `/pm/projects/<id>/tasks/add` | Create task |
| GET/POST | `/pm/tasks/<id>/edit` | Edit task |
| POST | `/pm/tasks/<id>/delete` | Delete task |
| GET/POST | `/pm/projects/<id>/milestones/add` | Create milestone |
| GET/POST | `/pm/milestones/<id>/edit` | Edit milestone |
| POST | `/pm/milestones/<id>/delete` | Delete milestone |
| GET | `/pm/notifications` | View notifications |
| POST | `/pm/notifications/<id>/read` | Mark notification read |
| POST | `/pm/notifications/mark-all-read` | Mark all read |

### REST API Routes (JSON)

| Method | URL | Response |
|--------|-----|----------|
| GET | `/pm/api/projects` | All projects with progress, delay status |
| GET | `/pm/api/projects/<id>` | Single project with members, tasks, milestones |
| GET | `/pm/api/projects/<id>/tasks` | All tasks for project |
| GET | `/pm/api/projects/<id>/milestones` | All milestones for project |
| GET | `/pm/api/projects/<id>/members` | All members of project |
| GET | `/pm/api/notifications` | Current user's notifications + unread count |

**Sample API response — `GET /pm/api/projects`:**
```json
{
  "projects": [
    {
      "id": 1,
      "name": "Project Alpha",
      "status": "In Progress",
      "progress": 67,
      "is_delayed": false,
      "deadline": "2026-06-30",
      "members_count": 5,
      "tasks_count": 12,
      "milestones_count": 3,
      "created_by": "John Admin",
      "created_at": "2026-04-15T10:00:00"
    }
  ],
  "total": 1
}
```

---

## 5. File Manifest

### Modified Files

| File | What Changed |
|------|-------------|
| `app/models.py` | Project: added `deadline`, `updated_at`, `unique=True` on name, `milestones` relationship, `progress` + `is_delayed` properties. ProjectMember: role default changed to `Developer`, added `joined_at`. Task: status default `Pending`, added `updated_at`. **New models:** `Milestone`, `Notification` |
| `app/pm/forms.py` | ProjectForm: added `deadline` field, statuses updated to lifecycle values. TaskForm: statuses to Pending/In Progress/Done. **New:** `MilestoneForm` |
| `app/pm/routes.py` | **Complete rewrite**: Added notify helper, audit logging, duplicate prevention, project delete, milestone CRUD, notification system, status filter, 6 REST API endpoints |
| `app/admin/routes.py` | Added `Milestone, Notification` imports. Dashboard query expanded with `active_projects`, `completed_projects`, `pending_tasks`, `total_milestones`, `total_notifications` |
| `app/templates/pm/dashboard.html` | 8 stat cards, notification banner, progress bars, deadline column |
| `app/templates/pm/projects.html` | Status filter tabs, progress bar column, deadline with delay indicator, delete action |
| `app/templates/pm/project_detail.html` | Progress bar, milestones panel, expanded team roles, project delete |
| `app/templates/pm/project_form.html` | Added deadline field |
| `app/templates/admin/dashboard.html` | 3-column layout, new "PM Overview" card |
| `static/css/style.css` | Added `.badge-not-started`, `.badge-in-progress`, `.badge-on-hold`, progress bar styles |
| `schema.sql` | Full sync with all current models |

### New Files

| File | Purpose |
|------|---------|
| `app/templates/pm/milestone_form.html` | Milestone create/edit form |
| `app/templates/pm/notifications.html` | Notifications list page |
| `walkthrough_pm.md` | This document |

---

## 6. Bug Fixes Applied

| Issue | Fix |
|-------|-----|
| Duplicate project names allowed | Added `unique=True` on `Project.name` + case-insensitive check in routes |
| No cascade delete for projects | `Project.delete` route now cascades to tasks, members, milestones |
| Missing audit trail for PM actions | All PM CRUD writes to `audit_logs` |
| Task status inconsistency (`To Do`) | Standardized to `Pending`, `In Progress`, `Done` |
| Role options too limited | Expanded to `Developer`, `Tester`, `Designer`, `Lead`, `Observer` |
| No `updated_at` tracking | Added to Project and Task models |
| No feedback on team/task changes | Notification system covers all major events |
| Missing progress visibility | Progress bar displayed in dashboard, list, and detail views |

---

## 7. Integration Points

### How PM Feeds Admin

```
PM creates/updates Project → Audit Log created → Admin sees in Audit Logs viewer
PM dashboard stats → Admin dashboard shows PM Overview card
PM notifications table → Admin can see total notification count
```

### How PM Interacts with Employees

```
PM assigns task → Notification sent to employee
PM updates task → Notification sent to employee
PM adds member to project → Notification sent to employee
Employee completes task → Notification sent to PM (project creator)
```

### How PM Uses the User System

```
Users table → Project members (foreign key: user_id)
Users table → Task assignment (foreign key: assigned_to)
Users table → Project creator (foreign key: created_by)
Users table → Notification recipient (foreign key: user_id)
Admin module_required decorator → PM routes protected by 'pm' module slug
```

### Migration Notes

After pulling these changes, run the following to update the database:

```bash
# Option 1: Let SQLAlchemy create new tables (existing data preserved)
python app.py
# This runs db.create_all() which creates milestones + notifications tables

# Option 2: If using Flask-Migrate
flask db migrate -m "PM module upgrade: milestones, notifications"
flask db upgrade
```

Existing project data will be preserved. The `status` default changes only affect new records.
