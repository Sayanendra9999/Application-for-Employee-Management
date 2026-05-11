# Manual Testing Guide — Manager-Based Leave Approval Workflow

## Prerequisites
1. Run the migration: `flask db upgrade`
2. Re-seed the database: `python seed_data.py` (or manually assign managers via HR)
3. Start the app: `flask run` or `python app.py`

## Test Users (from seed data)

| User | Role | EMP Code | Reporting Manager |
|------|------|----------|-------------------|
| System Admin | Admin | — | — |
| Priya Sharma | HR + Employee | EMP001 | None (senior) |
| Rahul Verma | Employee | EMP002 | Priya Sharma |
| John Doe | Employee | EMP004 | Priya Sharma |
| Jane Smith | Employee | EMP005 | Priya Sharma |
| Bob Wilson | Employee | EMP006 | Priya Sharma |

> **Note**: Adjust the above based on actual seed data assignments. Priya acts as the Team Lead / Manager for the other employees.

---

## Test Scenario 1: HR Assigns Reporting Manager

**Goal**: Verify HR can assign a reporting manager to an employee.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as **Priya Sharma** (HR) | HR dashboard loads |
| 2 | Navigate to **HR → Employees** | Employee list visible |
| 3 | Click **Edit** on **Rahul Verma (EMP002)** | Edit employee form opens |
| 4 | Look for **"Reporting Manager"** dropdown | Dropdown shows all active employees (except Rahul himself) |
| 5 | Select **Priya Sharma** as reporting manager | Selection made |
| 6 | Click **Save** | Flash: "Employee EMP002 updated." |
| 7 | Re-open Rahul's edit form | Reporting Manager shows "Priya Sharma" pre-selected |

---

## Test Scenario 2: Employee Submits Leave — Manager Gets Notified

**Goal**: Verify both Manager and HR receive notifications when an employee submits a leave.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as **Rahul Verma** (Employee) | Employee dashboard loads |
| 2 | Navigate to **Employee Space → Leaves** | Leave history page |
| 3 | Click **"Request Leave"** | Leave request form opens |
| 4 | Fill form: Casual Leave, tomorrow to day-after, "Family function" | Form filled |
| 5 | Leave "Mark as Urgent" **unchecked** | Normal flow |
| 6 | Click **Submit Request** | Flash: "Leave request submitted (X day(s))" |
| 7 | Check **Rahul's Notifications** page | Should see "Leave Request Submitted" notification |
| 8 | Logout → Login as **Priya Sharma** | Switch user |
| 9 | Check **Employee Space → Notifications** | Should see "Leave Request from Team Member" from Rahul |
| 10 | Also check HR module notifications badge | Should show increased count |

---

## Test Scenario 3: Manager Approves Leave (Normal Flow)

**Goal**: Verify Manager → HR two-step approval.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as **Priya Sharma** (Manager) | Dashboard loads |
| 2 | Look for **"My Team"** in sidebar | "My Team" link visible with pending badge count |
| 3 | Click **"My Team"** | Team overview: shows Rahul, John, Jane, Bob as direct reports |
| 4 | Click **"Team Leaves"** or the pending leaves count | Team leaves page shows Rahul's pending leave |
| 5 | Verify leave shows: Employee name, dates, type, reason | All details visible |
| 6 | Click **Approve** (✓ button) | Flash: "Leave approved by manager. Awaiting HR final approval." |
| 7 | Verify Rahul's leave row: Manager = "Approved ✓", Status still "Pending" | Manager approved, HR pending |
| 8 | Logout → Login as **Priya Sharma** (now in HR role) | Switch to HR module |
| 9 | Navigate to **HR → Leaves** | Leave list visible |
| 10 | Find Rahul's leave | Manager column: "Approved by Priya Sharma ✓", HR column: "Pending" |
| 11 | Click **Approve** | Flash: "Leave approved (X days deducted)" |
| 12 | Verify Final status: "Approved", Manager: "Approved", HR: "Approved" | ✅ Complete |
| 13 | Logout → Login as **Rahul Verma** | Check notifications |
| 14 | Check Notifications | Should see "Manager Approved" and "Leave Approved" notifications |

---

## Test Scenario 4: Manager Rejects Leave

**Goal**: Verify manager rejection is final.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as **Rahul Verma**, submit a new leave request | Leave submitted |
| 2 | Logout → Login as **Priya Sharma** | Switch to manager |
| 3 | Go to **My Team → Team Leaves** | See Rahul's new pending leave |
| 4 | Click **Reject** (✗ button) | Rejection reason modal/form appears |
| 5 | Enter reason: "Team is short-staffed this week" | Reason entered |
| 6 | Submit rejection | Flash: "Leave rejected by manager." |
| 7 | Verify leave status: **Rejected**, Manager: "Rejected" | ✅ Final |
| 8 | Logout → Login as **Rahul Verma** | Check notifications |
| 9 | Check Notifications | Should see "Leave Rejected by Manager" with reason |

---

## Test Scenario 5: Urgent Leave — Bypass Manager

**Goal**: Verify urgent leaves go directly to HR, skipping manager.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as **Rahul Verma** | Employee dashboard |
| 2 | Go to **Leaves → Request Leave** | Leave form |
| 3 | Fill form: Sick Leave, today, today, "Not feeling well" | Form filled |
| 4 | **Check** "Mark as Urgent" checkbox | Urgent flag enabled |
| 5 | Submit | Flash: "Leave request submitted" |
| 6 | Logout → Login as **Priya Sharma** | Manager login |
| 7 | Go to **My Team → Team Leaves** | Rahul's urgent leave should NOT appear here for action (or show as "Urgent - Direct to HR") |
| 8 | Go to **HR → Leaves** | Rahul's urgent leave visible with Manager: "N/A", HR: "Pending" |
| 9 | Approve via HR | Flash: "Leave approved" |
| 10 | Manager column should show **"N/A"** | ✅ Skipped correctly |

---

## Test Scenario 6: Employee Without Manager — Direct to HR

**Goal**: Verify senior employees (no manager assigned) skip to HR automatically.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as **Priya Sharma** (has no reporting manager) | Employee dashboard |
| 2 | Go to **Leaves → Request Leave** | Leave form |
| 3 | Verify no "My Team" link shows for Priya if she has no reports... wait, Priya IS the manager. Let's test with another senior. | — |
| 3b | Alternative: Via HR, ensure some employee has `reporting_manager = None` | Setup |
| 4 | Login as that employee, submit leave | Leave submitted |
| 5 | Check leave status | Manager: "N/A", HR: "Pending" |
| 6 | Only HR gets notification (no manager notification) | ✅ Correct |

---

## Test Scenario 7: "My Team" Sidebar Visibility

**Goal**: Verify sidebar shows "My Team" only for managers.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as **Priya Sharma** (manager of several employees) | Dashboard loads |
| 2 | Check sidebar under "Employee Space" | **"My Team"** link visible with badge |
| 3 | Logout → Login as **Rahul Verma** (not a manager) | Dashboard loads |
| 4 | Check sidebar under "Employee Space" | **"My Team"** link **NOT visible** |

---

## Test Scenario 8: HR Override — Approve Without Manager

**Goal**: Verify HR can approve even if manager hasn't acted.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Have an employee submit a leave (manager = pending) | Leave in pending state |
| 2 | Login as HR | HR module |
| 3 | Go to **HR → Leaves** | See the leave with Manager: "Pending" |
| 4 | Click **Approve** | HR can still approve directly |
| 5 | Verify: Final status = "Approved", Manager = "Pending", HR = "Approved" | ✅ HR override works |

---

## Test Scenario 9: Dashboard Team Card

**Goal**: Verify manager sees team info on dashboard.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as **Priya Sharma** | Employee dashboard |
| 2 | Look for "My Team" card/section on dashboard | Card visible showing: Team size, pending leave requests count |
| 3 | Click "Review" or pending count link | Navigates to Team Leaves page |

---

## Test Scenario 10: Leave Cancellation Still Works

**Goal**: Regression test — employee can still cancel leaves.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as employee, go to My Leaves | Leave history |
| 2 | Find a pending leave, click **Cancel** | Cancellation dialog |
| 3 | Confirm cancellation | Leave status: "Cancelled", balance restored if was approved |

---

## Edge Cases to Verify

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| 1 | Manager tries to approve own leave | Should not be possible (self not in direct reports) |
| 2 | Manager is changed mid-process | Old manager should no longer see the leave in their Team Leaves |
| 3 | Employee with manager submits urgent leave | Goes directly to HR, manager_status = N/A |
| 4 | HR rejects leave that manager already approved | Final status = Rejected, balance NOT deducted |
| 5 | Multiple pending leaves from same employee | All show individually in manager's Team Leaves |
