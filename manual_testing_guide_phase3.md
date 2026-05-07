# Comprehensive Manual Testing Guide — Phase 3 Features

Before you begin, ensure your local Flask development server is running (`python app.py` or `flask run`) and that you have a fresh environment ready.

---

## Part 1: Security & Authentication Testing

### Test 1.1: Password Complexity Enforcement
1. Log in to the portal using any existing account.
2. Go to your **Profile** (click your name in the top right) and select **Change Password**.
3. Attempt to set a simple password (e.g., `password123`).
4. **Expected Result**: The system should reject the change with an error stating the password must be at least 8 characters and include uppercase, lowercase, numbers, and special characters.
5. Try setting a valid password (e.g., `Secure@123!`). 
6. **Expected Result**: The password update should be successful.

### Test 1.2: Brute-Force Account Lockout
1. Log out of the application completely.
2. Attempt to log in with a valid username but an **incorrect password** exactly **5 times** in a row.
3. On the 5th attempt, you should see an error message stating your account is locked for 15 minutes.
4. Now, enter the *correct* password.
5. **Expected Result**: The system should still reject the login and display the lockout message.

### Test 1.3: Admin Login History & Unlock Feature
1. Log in using an **Admin** account.
2. Look at the bottom left sidebar and click on **Login History** (under Admin Quick Links).
3. **Expected Result**: You should see a table showing the 5 failed attempts and the "Locked" status.
4. Under the "Actions" column for that locked user, click the green **Unlock** icon.
5. **Expected Result**: The lock should be removed. You can now log out, and log back in successfully with that previously locked account.

---

## Part 2: Admin Workflows Testing

### Test 2.1: Department & Designation Soft-Deletes
1. Log in as an **Admin** and navigate to the **Admin Dashboard**.
2. Click on **Departments** in the HR Configuration card.
3. Find a department and click the red **Deactivate** icon (the ban symbol). Confirm the prompt.
4. **Expected Result**: The department's status should change from "Active" to "Inactive". The department is *not* deleted from the database but will be hidden from normal dropdowns.
5. Click the green **Restore** icon on that same department.
6. **Expected Result**: The status should return to "Active".

### Test 2.2: Global Notifications
1. As an **Admin**, click on **Notifications** in the bottom left sidebar.
2. Fill out the "Send New Notification" form:
   * **Target**: Select **All Users**.
   * **Title**: "Test Notification".
   * **Category**: Select "Success" or "Alert".
   * **Message**: "This is a global test."
3. Click **Send**.
4. Log in as a normal **Employee**. Check the top right bell icon (if configured) or navigate to your **Employee Space -> Notifications**.
5. **Expected Result**: The employee should see the newly broadcasted notification.

### Test 2.3: Holiday Calendar Viewer
1. As an **Admin**, click on **Company Holidays** in the bottom left sidebar.
2. **Expected Result**: You should see the list of 19 Indian festivals and Telangana Formation Day that we seeded.
3. Click **Add Holiday**, create a new test holiday, and save it.
4. Log in as an **Employee**, open the sidebar, and navigate to **Holidays** (you may need to access `http://localhost:5000/employee/holidays` directly if you haven't linked it in the employee sidebar yet).
5. **Expected Result**: The employee should see a beautiful card-based layout showing all the company holidays, including the one you just added.

---

## Part 3: HR & Employee Workflows Testing

### Test 3.1: Candidate Resume Upload
1. Log in as an **HR User** and go to **HR Dashboard -> Recruitment**.
2. Click on any active Job Posting to view its details.
3. Click **Add Candidate**. Fill in the details (Name, Email, etc.).
4. Under "Resume Document", choose a `.pdf` or `.docx` file from your computer and click **Submit**.
5. **Expected Result**: You will be redirected back to the candidate list. Next to the candidate you just added, click the blue **PDF Icon** in the actions column. The resume file should successfully download to your computer.

### Test 3.2: Sensitive Profile Update Approvals
1. Log in as an **Employee** and go to **Employee Space -> My Analytics** (or navigate to `http://localhost:5000/employee/profile` to view your profile).
2. Click the **Request Update** button under the "Request Sensitive Update" card.
3. Select "Bank Account" or "PAN", enter a new fake value, and submit.
4. Log in as an **HR User** and go to the **HR Dashboard**. Under the Quick Actions grid, click **Profile Update Requests**.
5. **Expected Result**: You should see the employee's pending request. 
6. Click the green checkmark to approve it. 
7. Check the Employee's profile again — the bank account/PAN number should now reflect the new approved value.

### Test 3.3: Attendance Regularization
1. Log in as an **Employee** and navigate to **Attendance**.
2. Click the **Request Attendance Regularization** button at the top.
3. Pick a date from the *past*, enter `09:00 AM` for check-in and `06:00 PM` for check-out. Add a reason like "Missed punch" and submit.
4. Log in as an **HR User**, go to the **HR Dashboard**, and click **Attendance Regularizations** in the Quick Actions grid.
5. Click the green checkmark to approve the request.
6. **Expected Result**: Go to **Attendance Records** as HR and view that employee's attendance for that specific date. The check-in and check-out times should now reflect the 9AM-6PM times you just approved.

### Test 3.4: Leave Cancellation & Auto-Refund
1. Log in as an **Employee** and go to **Leaves -> Request Leave**. Submit a request for a 2-day leave.
2. Go to the **My Leaves** tab. You will see a red **Cancel** button next to your pending request.
3. *(Optional)* Log in as HR/Manager and Approve this leave. Check the employee's Leave Balance to note how many days they have left.
4. As the **Employee**, click the red **Cancel** button on that leave and provide a reason.
5. **Expected Result**: The leave status should instantly change to "Cancelled". If the leave was previously approved, check the Leave Balance page again—the 2 days should be refunded immediately.
