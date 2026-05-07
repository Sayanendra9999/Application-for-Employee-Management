# Enterprise Portal Application Workflow

*This presentation outlines the workflow of the Enterprise Portal application, breaking it down into key stages across different modules. Because your disk currently has no space left, I couldn't automatically generate the PPTX file and capture screenshots. However, the structure below serves as your presentation outline.*

---

## Slide 1: Welcome & Login
**Focus**: Unified authentication and role-based access.

- **Description**: The application uses a single secure login portal for all users—Admin, HR, PM, Finance, and Employees.
- **Workflow**: 
  - Users enter their credentials (`username` and `password`).
  - Upon successful authentication, Flask-Login creates a session.
  - The system checks the user's role and assigned modules to determine what they are allowed to see.
- **Suggested UI Photo**: `login.png` (The Sign In screen).

---

## Slide 2: Main Dashboard
**Focus**: Role-specific navigation and quick access.

- **Description**: The main landing page dynamically adjusts based on the logged-in user's permissions.
- **Workflow**:
  - Displays interactive module cards (HR, PM, Finance, etc.).
  - Users only see the cards for modules they have access to.
  - Acts as the central hub for navigating the enterprise system.
- **Suggested UI Photo**: `dashboard.png` (Dashboard with module cards).

---

## Slide 3: HR Module
**Focus**: Managing people, policies, and attendance.

- **Description**: The Human Resources module handles the core employee lifecycle.
- **Workflow**:
  - **Employee Management**: Create and manage employee profiles, assigning them to departments and designations.
  - **Attendance & Shifts**: Track check-ins/check-outs, configure shift timings, and handle shift swap requests.
  - **Leaves**: Define leave policies (Casual, Sick, Earned) and approve or reject employee leave requests.
- **Suggested UI Photo**: `hr_module.png` (HR Dashboard or Employee List).

---

## Slide 4: Project Management (PM) Module
**Focus**: Tracking project progress and team productivity.

- **Description**: The PM module allows teams to collaborate and manage deliverables.
- **Workflow**:
  - **Projects & Milestones**: Create projects with deadlines and break them into milestones.
  - **Tasks**: Assign tasks to team members with priority levels and estimated hours.
  - **Timesheets**: Employees log actual hours spent on tasks, automatically updating project progress.
- **Suggested UI Photo**: `pm_module.png` (Project list or Task board).

---

## Slide 5: Finance Module
**Focus**: Budgeting, expenses, and payroll.

- **Description**: The financial backbone of the enterprise portal.
- **Workflow**:
  - **Expenses**: Review and approve internal company expenses and employee reimbursement claims.
  - **Invoices**: Generate, track, and manage client invoices (Unpaid, Paid, Overdue).
  - **Salary Records**: Process monthly payroll based on base salary, HRA, and deductions.
- **Suggested UI Photo**: `finance_module.png` (Finance overview or Invoices table).

---

## Slide 6: Employee Space
**Focus**: Self-service tools for the workforce.

- **Description**: A dedicated portal where employees manage their day-to-day activities.
- **Workflow**:
  - **Daily Operations**: Quick check-in/check-out for attendance.
  - **Requests**: Submit leave applications, expense claims, and shift swap requests.
  - **Profile**: View personal details and request profile updates (e.g., updating bank account or PAN).
- **Suggested UI Photo**: `employee_module.png` (Employee dashboard with quick actions).

---

## Summary

The Enterprise Portal integrates HR, PM, Finance, and Employee Self-Service into a single, seamless platform. This unified approach eliminates silos, ensures data consistency across departments, and streamlines daily operations from task tracking to payroll generation.

> **Note on getting the PPTX file:**
> I have created a Python script at `d:\app_pm_updated\generate_ppt.py` that will automatically launch a browser, take screenshots of each stage, and embed them into a PowerPoint (`.pptx`) file. 
> 
> Due to your disk being full (Error: `[Errno 28] No space left on device`), I couldn't install the necessary dependencies (`playwright` and `python-pptx`) to run it. Once you free up some disk space, you can run the following commands to generate your PPT:
> 
> ```powershell
> pip install playwright python-pptx
> playwright install chromium
> python generate_ppt.py
> ```
