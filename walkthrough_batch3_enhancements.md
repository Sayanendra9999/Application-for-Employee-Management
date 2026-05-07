# Enterprise Portal — Phase 3 Implementation Walkthrough

This document outlines the features and workflows implemented to complete the high-priority requirements for the **Security**, **Administrative**, and **HR Workflows** modules.

---

## 1. Security Enhancements (Auth Module)
We hardened the authentication layer to prevent brute-force attacks and enforce better password standards.

- **Account Lockout Mechanism**: 
  - The `User` database model was expanded with `failed_login_attempts` and `locked_until` fields.
  - If a user enters an incorrect password **5 consecutive times**, their account is automatically locked for **15 minutes**.
- **Password Complexity Rules**:
  - The `set_password` function now strictly validates passwords. New passwords must be at least **8 characters** long and contain a mix of uppercase letters, lowercase letters, numbers, and special characters.
- **Login History Logging**:
  - A new `LoginHistory` table was created to meticulously track every login attempt (Success, Failed, Locked). It captures the user's IP address, timestamp, and context details for robust security auditing.

## 2. Administrative Controls (Admin Module)
New dashboards and management features were integrated to give administrators finer control over the system.

- **Login Activity Dashboard**: 
  - Admins can now view a detailed, paginated ledger of all user login attempts (`/admin/login-history`).
  - Added an **"Unlock Account"** quick action so admins can manually restore access to users who triggered the account lockout feature.
- **Soft-Deletes for Organizational Units**:
  - Instead of permanently deleting crucial structures (which would break historical records), Departments and Designations now use a **Soft-Delete** toggle. Admins can safely "Deactivate" and "Restore" them using the ban/undo icons.
- **Global Notification System**:
  - Built a notification engine where Admins can broadcast messages (`/admin/notifications`). They can target all users simultaneously or select an individual user, choosing alert severities like Info, Success, Warning, or Alert.
- **Company Holiday Management**:
  - Created a robust CRUD system for admins to declare and manage Public, Restricted, and Optional holidays (`/admin/holidays`).

## 3. HR Workflows & Approvals (HR Module)
HR processes were expanded to introduce deeper request workflows and document management.

- **Attendance Regularization Workflow**:
  - **Employee Side**: Staff who miss a swipe or face system errors can now submit a formal "Regularization Request," specifying the past date, the corrected check-in/check-out times, and a justification.
  - **HR Side**: HR gets a dedicated dashboard (`/hr/attendance-regularizations`) to review these claims. Approving a request automatically injects the corrected times directly into the employee's `Attendance` record.
- **Leave Cancellation Protocol**:
  - **Employee Side**: Employees can proactively cancel their own `Pending` or `Approved` leave requests directly from their dashboard.
  - **Refund Automation**: If an `Approved` leave is cancelled, the system automatically detects this and refunds the exact number of days back to the employee's `LeaveBalance`.
  - **HR Overrides**: HR retains the ultimate authority to forcibly cancel any employee's leave from their management view if necessary.
- **Sensitive Profile Updates**:
  - **Employee Side**: Certain fields (like PAN, Bank Account, Phone) are locked for standard editing. Employees must now submit an `Update Request` to alter these details.
  - **HR Side**: HR can approve or reject these requests (`/hr/profile-update-requests`). Approving a request instantly patches the employee's secure profile data.
- **Candidate Resume Processing**:
  - The Recruitment module was upgraded to handle file attachments. HR can upload `.pdf` or Word document resumes when creating or editing a Candidate. The documents are securely saved with UUID hashes, and a one-click download button is now available directly on the Job Detail view.

## 4. UI/UX & Navigation Updates
To ensure all these new features are easily accessible, the portal navigation was heavily updated:
- The **Admin Dashboard** and **Global Sidebar** were updated with permanent quick-links to Login History, Global Notifications, and Company Holidays.
- The **HR Dashboard** was expanded with new quick action buttons for the Regularization and Profile Update queues.
- We injected **19 National & Regional Holidays** (including Telangana Formation Day) directly into the database so the Holiday Calendar is instantly populated and ready to use.
