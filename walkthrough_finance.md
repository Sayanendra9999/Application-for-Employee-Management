# Finance Module Improvements — Walkthrough

## New Features Added

### 1. Employee Expense Claims Management
The portal allows employees to submit expense claims from their self-service dashboard (`EmployeeExpense` model). We have now built the management interface for the Finance team to review these claims.

#### Changes Made:
- **`app/finance/routes.py`**:
  - Added `/employee-expenses` route to view all submitted employee expense claims.
  - Added `/employee-expenses/<int:claim_id>/approve` (POST) to approve a claim and mark it as reviewed by the current user.
  - Added `/employee-expenses/<int:claim_id>/reject` (POST) to reject a claim.
- **`app/templates/finance/employee_expenses.html`**:
  - Created a new data table view showing the Employee Name, Employee Code, Category, Amount, Date, Description, and Status.
  - Included inline action buttons (Approve / Reject) for claims that are currently in `Pending` status.
- **`app/templates/finance/dashboard.html`**:
  - Added an "Employee Expenses" button under the **Quick Actions** section to allow easy navigation to the new claims management page.

---

## How to Test

1. **Submit a Claim as an Employee**:
   - Log in as an employee (e.g., `john_doe` / `john123`).
   - Go to the **Employee Dashboard** and click **Submit Expense**.
   - Fill out the form and save.

2. **Review as Finance**:
   - Log in as a Finance user or Admin (e.g., `finance_head` / `fin123` or `admin` / `admin123`).
   - Go to the **Finance Module**.
   - Scroll down to the **Quick Actions** section and click **Employee Expenses**.
   - You should see the list of all employee expense claims, including the one you just submitted.
   - Click the green checkmark to **Approve** or the red cross to **Reject**. The status will update accordingly.
