"""Seed the database with sample data for testing.

Usage:
    python seed_data.py
"""

from datetime import date, datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import (User, Module, UserModule, Employee, Leave, LeaveBalance,
                        Attendance, Project, ProjectMember, Task,
                        Milestone, Notification,
                        Expense, Invoice, SalaryRecord,
                        Department, Designation, LeavePolicy, AttendanceRule,
                        PerformanceReview, JobPosting, Candidate, Interview,
                        ProfileUpdateRequest, EmployeeExpense,
                        Shift, CompOff, ShiftSwapRequest)


def seed():
    app = create_app()
    with app.app_context():
        # Drop & recreate all tables
        db.drop_all()
        db.create_all()
        print("[OK] Tables created.")

        # ── Modules ──────────────────────────────────────────────────────
        modules = [
            Module(name='Admin', slug='admin', description='System administration & user management',
                   icon='fas fa-shield-halved'),
            Module(name='HR', slug='hr', description='Human resources, employees & attendance',
                   icon='fas fa-people-group'),
            Module(name='Project Management', slug='pm',
                   description='Projects, tasks & team collaboration',
                   icon='fas fa-diagram-project'),
            Module(name='Finance', slug='finance',
                   description='Salary, expenses, invoices & reports',
                   icon='fas fa-indian-rupee-sign'),
            Module(name='Employee', slug='employee',
                   description='Personal dashboard, tasks & leaves',
                   icon='fas fa-user-circle'),
        ]
        db.session.add_all(modules)
        db.session.flush()
        mod_map = {m.slug: m for m in modules}
        print("[OK] Modules created.")

        # ── Departments (Admin-managed) ──────────────────────────────────
        departments = [
            Department(name='Engineering', code='ENG',
                       description='Software development and technology'),
            Department(name='Human Resources', code='HR',
                       description='People management and recruitment'),
            Department(name='Finance', code='FIN',
                       description='Accounting, payroll and financial planning'),
            Department(name='Marketing', code='MKT',
                       description='Digital marketing and brand management'),
            Department(name='Operations', code='OPS',
                       description='Business operations and logistics'),
        ]
        db.session.add_all(departments)
        db.session.flush()
        dept_map = {d.code: d for d in departments}
        print("[OK] Departments created.")

        # ── Designations (Admin-managed) ─────────────────────────────────
        designations = [
            # Engineering
            Designation(title='Junior Developer', department_id=dept_map['ENG'].id, level=1),
            Designation(title='Software Developer', department_id=dept_map['ENG'].id, level=2),
            Designation(title='Senior Developer', department_id=dept_map['ENG'].id, level=3),
            Designation(title='Tech Lead', department_id=dept_map['ENG'].id, level=4),
            Designation(title='Engineering Manager', department_id=dept_map['ENG'].id, level=5),
            # HR
            Designation(title='HR Associate', department_id=dept_map['HR'].id, level=1),
            Designation(title='HR Executive', department_id=dept_map['HR'].id, level=2),
            Designation(title='Senior HR Executive', department_id=dept_map['HR'].id, level=3),
            Designation(title='HR Manager', department_id=dept_map['HR'].id, level=5),
            # Finance
            Designation(title='Junior Accountant', department_id=dept_map['FIN'].id, level=1),
            Designation(title='Accountant', department_id=dept_map['FIN'].id, level=2),
            Designation(title='Senior Accountant', department_id=dept_map['FIN'].id, level=3),
            Designation(title='Finance Manager', department_id=dept_map['FIN'].id, level=5),
            # Marketing
            Designation(title='Marketing Executive', department_id=dept_map['MKT'].id, level=2),
            Designation(title='Marketing Manager', department_id=dept_map['MKT'].id, level=5),
            # Operations
            Designation(title='Operations Associate', department_id=dept_map['OPS'].id, level=1),
            Designation(title='Operations Manager', department_id=dept_map['OPS'].id, level=5),
        ]
        db.session.add_all(designations)
        db.session.flush()
        desig_map = {(d.title, d.department_id): d for d in designations}
        print("[OK] Designations created.")

        # ── Leave Policies (Admin-managed) ───────────────────────────────
        leave_policies = [
            # Global policies (applicable to all designations by default)
            LeavePolicy(leave_type='Casual Leave', total_days=12,
                        carry_forward=False, description='For personal/family reasons'),
            LeavePolicy(leave_type='Sick Leave', total_days=10,
                        carry_forward=False, description='For health-related absences'),
            LeavePolicy(leave_type='Earned Leave', total_days=15,
                        carry_forward=True, max_carry_days=5,
                        monthly_accrual=True, encashment_allowed=True,
                        description='Accrued leave, can carry forward up to 5 days'),
        ]
        db.session.add_all(leave_policies)
        db.session.flush()
        print("[OK] Global leave policies created.")

        # Designation-specific leave policies (override global for certain roles)
        # Find some designations for role-based policies
        junior_dev = desig_map.get(('Junior Developer', dept_map['ENG'].id))
        tech_lead = desig_map.get(('Tech Lead', dept_map['ENG'].id))
        eng_mgr = desig_map.get(('Engineering Manager', dept_map['ENG'].id))
        hr_mgr = desig_map.get(('HR Manager', dept_map['HR'].id))

        role_policies = []
        if junior_dev:
            role_policies.append(LeavePolicy(
                leave_type='Casual Leave', designation_id=junior_dev.id,
                total_days=8, carry_forward=False, max_per_request=3,
                description='Junior level: 8 CL/year, max 3 per request'
            ))
        if tech_lead:
            role_policies.append(LeavePolicy(
                leave_type='Casual Leave', designation_id=tech_lead.id,
                total_days=15, carry_forward=True, max_carry_days=3,
                encashment_allowed=True,
                description='Lead level: 15 CL/year, carry-forward enabled'
            ))
        if hr_mgr:
            role_policies.append(LeavePolicy(
                leave_type='Earned Leave', designation_id=hr_mgr.id,
                total_days=20, carry_forward=True, max_carry_days=10,
                monthly_accrual=True, encashment_allowed=True,
                description='Manager level: 20 EL/year, carry-forward up to 10'
            ))
        if role_policies:
            db.session.add_all(role_policies)
            db.session.flush()
        print(f"[OK] {len(role_policies)} designation-specific leave policies created.")

        # ── Attendance Rules (Admin-managed) ─────────────────────────────
        att_rule = AttendanceRule(
            work_start='09:00', work_end='18:00',
            late_threshold_mins=15, half_day_hours=4.0, full_day_hours=8.0
        )
        db.session.add(att_rule)
        db.session.flush()
        print("[OK] General shift (Attendance Rules) configured.")

        # ── Shifts (Admin-managed) ────────────────────────────────────────
        shifts = [
            Shift(shift_name='Morning', start_time='06:00', end_time='14:00',
                  grace_period_mins=10, min_working_hours=8.0,
                  late_mark_after_mins=15, overtime_eligible=True),
            Shift(shift_name='Afternoon', start_time='14:00', end_time='22:00',
                  grace_period_mins=10, min_working_hours=8.0,
                  late_mark_after_mins=15, overtime_eligible=True),
            Shift(shift_name='Night', start_time='22:00', end_time='06:00',
                  grace_period_mins=15, min_working_hours=8.0,
                  late_mark_after_mins=20, overtime_eligible=True),
        ]
        db.session.add_all(shifts)
        db.session.flush()
        shift_map = {s.shift_name: s for s in shifts}
        print(f"[OK] {len(shifts)} shifts created (Morning, Afternoon, Night).")

        # ── Users ────────────────────────────────────────────────────────
        users_data = [
            {'username': 'admin', 'email': 'admin@company.com',
             'full_name': 'System Admin', 'phone': '+91 99999 00001',
             'password': 'admin123', 'is_admin': True,
             'modules': ['admin', 'hr', 'pm', 'finance', 'employee']},

            {'username': 'hr_manager', 'email': 'hr@company.com',
             'full_name': 'Priya Sharma', 'phone': '+91 99999 00002',
             'password': 'hr123', 'is_admin': False,
             'modules': ['hr', 'employee']},

            {'username': 'pm_lead', 'email': 'pm@company.com',
             'full_name': 'Rahul Verma', 'phone': '+91 99999 00003',
             'password': 'pm123', 'is_admin': False,
             'modules': ['pm', 'employee']},

            {'username': 'finance_head', 'email': 'finance@company.com',
             'full_name': 'Anita Gupta', 'phone': '+91 99999 00004',
             'password': 'fin123', 'is_admin': False,
             'modules': ['finance', 'employee']},

            {'username': 'john_doe', 'email': 'john@company.com',
             'full_name': 'John Doe', 'phone': '+91 99999 00005',
             'password': 'john123', 'is_admin': False,
             'modules': ['pm', 'employee']},

            {'username': 'jane_smith', 'email': 'jane@company.com',
             'full_name': 'Jane Smith', 'phone': '+91 99999 00006',
             'password': 'jane123', 'is_admin': False,
             'modules': ['finance', 'employee']},

            {'username': 'bob_wilson', 'email': 'bob@company.com',
             'full_name': 'Bob Wilson', 'phone': '+91 99999 00007',
             'password': 'bob123', 'is_admin': False,
             'modules': ['hr', 'employee']},

            {'username': 'pm_manager_1', 'email': 'vikram@company.com',
             'full_name': 'Vikram Patel', 'phone': '+91 99999 00008',
             'password': 'pm1_123', 'is_admin': False,
             'modules': ['pm', 'employee']},

            {'username': 'pm_manager_2', 'email': 'neha@company.com',
             'full_name': 'Neha Kapoor', 'phone': '+91 99999 00009',
             'password': 'pm2_123', 'is_admin': False,
             'modules': ['pm', 'employee']},
        ]

        user_objects = {}
        for ud in users_data:
            u = User(
                username=ud['username'],
                email=ud['email'],
                full_name=ud['full_name'],
                phone=ud['phone'],
                is_admin=ud['is_admin'],
                must_change_password=False   # Test accounts don't need forced reset
            )
            u.set_password(ud['password'])
            db.session.add(u)
            db.session.flush()
            user_objects[ud['username']] = u

            # Assign modules
            for mod_slug in ud['modules']:
                db.session.add(UserModule(user_id=u.id, module_id=mod_map[mod_slug].id))

        db.session.flush()
        print("[OK] Users created and modules assigned.")

        # ── Employee records (now linked to departments & designations) ──
        employees_data = [
            {'user': 'admin', 'code': 'EMP000', 'dept': 'HR',
             'designation': ('HR Manager', dept_map['HR'].id),
             'salary': 150000, 'doj': date(2020, 1, 1), 'pan': 'ADMIN1234Z'},
            {'user': 'hr_manager', 'code': 'EMP001', 'dept': 'HR',
             'designation': ('HR Manager', dept_map['HR'].id),
             'salary': 85000, 'doj': date(2022, 3, 15), 'pan': 'ABCPS1234A'},
            {'user': 'pm_lead', 'code': 'EMP002', 'dept': 'ENG',
             'designation': ('Tech Lead', dept_map['ENG'].id),
             'salary': 95000, 'doj': date(2021, 7, 1), 'pan': 'BCDPV5678B'},
            {'user': 'finance_head', 'code': 'EMP003', 'dept': 'FIN',
             'designation': ('Finance Manager', dept_map['FIN'].id),
             'salary': 90000, 'doj': date(2022, 1, 10), 'pan': 'CDEAG9012C'},
            {'user': 'john_doe', 'code': 'EMP004', 'dept': 'ENG',
             'designation': ('Software Developer', dept_map['ENG'].id),
             'salary': 70000, 'doj': date(2023, 6, 20), 'pan': 'DEFJD3456D'},
            {'user': 'jane_smith', 'code': 'EMP005', 'dept': 'FIN',
             'designation': ('Accountant', dept_map['FIN'].id),
             'salary': 65000, 'doj': date(2023, 9, 1), 'pan': 'EFGJS7890E'},
            {'user': 'bob_wilson', 'code': 'EMP006', 'dept': 'HR',
             'designation': ('HR Associate', dept_map['HR'].id),
             'salary': 55000, 'doj': date(2024, 1, 15), 'pan': 'FGHBW1234F'},
            {'user': 'pm_manager_1', 'code': 'EMP007', 'dept': 'ENG',
             'designation': ('Senior Developer', dept_map['ENG'].id),
             'salary': 88000, 'doj': date(2022, 5, 10), 'pan': 'GHIVP5678G'},
            {'user': 'pm_manager_2', 'code': 'EMP008', 'dept': 'ENG',
             'designation': ('Senior Developer', dept_map['ENG'].id),
             'salary': 86000, 'doj': date(2022, 8, 20), 'pan': 'HIJNK9012H'},
        ]

        emp_objects = {}
        for ed in employees_data:
            desig = desig_map.get(ed['designation'])
            emp = Employee(
                user_id=user_objects[ed['user']].id,
                emp_code=ed['code'],
                department_id=dept_map[ed['dept']].id,
                designation_id=desig.id if desig else None,
                salary=ed['salary'],
                date_of_joining=ed['doj'],
                bank_account=f"XXXX-XXXX-{ed['code'][-3:]}",
                pan_number=ed['pan']
            )
            db.session.add(emp)
            db.session.flush()
            emp_objects[ed['user']] = emp

        # Assign shifts to some employees
        emp_objects['john_doe'].shift_id = shift_map['Morning'].id
        emp_objects['jane_smith'].shift_id = shift_map['Afternoon'].id
        emp_objects['bob_wilson'].shift_id = shift_map['Night'].id

        print("[OK] Employee records created (with shift assignments).")

        # ── Leave Balances (initialized from policies) ───────────────────
        for emp_key, emp_obj in emp_objects.items():
            for policy in leave_policies:
                used = 0
                if emp_key == 'john_doe' and policy.leave_type == 'Casual Leave':
                    used = 3
                elif emp_key == 'jane_smith' and policy.leave_type == 'Sick Leave':
                    used = 2
                balance = LeaveBalance(
                    employee_id=emp_obj.id,
                    leave_type=policy.leave_type,
                    total_allocated=policy.total_days,
                    used=used,
                    year=2026
                )
                db.session.add(balance)
        db.session.flush()
        print("[OK] Leave balances initialized.")

        # ── Leave requests ───────────────────────────────────────────────
        leaves_data = [
            {'emp': 'john_doe', 'type': 'Casual Leave', 'start': date(2026, 4, 5),
             'end': date(2026, 4, 7), 'status': 'Approved', 'days': 3,
             'reason': 'Family function', 'approved_by': 'hr_manager'},
            {'emp': 'jane_smith', 'type': 'Sick Leave', 'start': date(2026, 4, 10),
             'end': date(2026, 4, 11), 'status': 'Approved', 'days': 2,
             'reason': 'Not feeling well', 'approved_by': 'hr_manager'},
            {'emp': 'pm_lead', 'type': 'Earned Leave', 'start': date(2026, 4, 20),
             'end': date(2026, 4, 25), 'status': 'Pending', 'days': 4,
             'reason': 'Vacation travel', 'approved_by': None},
            {'emp': 'bob_wilson', 'type': 'Casual Leave', 'start': date(2026, 4, 15),
             'end': date(2026, 4, 15), 'status': 'Pending', 'days': 1,
             'reason': 'Personal errand', 'approved_by': None},
            {'emp': 'hr_manager', 'type': 'Sick Leave', 'start': date(2026, 3, 28),
             'end': date(2026, 3, 29), 'status': 'Approved', 'days': 2,
             'reason': 'Doctor appointment', 'approved_by': 'admin'},
        ]

        for ld in leaves_data:
            leave = Leave(
                employee_id=emp_objects[ld['emp']].id,
                leave_type=ld['type'],
                start_date=ld['start'],
                end_date=ld['end'],
                total_days=ld['days'],
                status=ld['status'],
                reason=ld['reason'],
                approved_by=user_objects[ld['approved_by']].id if ld['approved_by'] else None
            )
            db.session.add(leave)

        print("[OK] Leave requests created.")

        # ── Attendance records ───────────────────────────────────────────
        today = date.today()
        for emp_key, emp_obj in emp_objects.items():
            for day_offset in range(15):
                d = today - timedelta(days=day_offset)
                if d.weekday() >= 5:  # skip weekends
                    continue
                status = 'Present'
                check_in = '09:00'
                check_out = '18:00'
                hours = 9.0
                if day_offset == 3:
                    status = 'Late'
                    check_in = '10:30'
                    hours = 7.5
                if day_offset == 7 and emp_key == 'john_doe':
                    status = 'Absent'
                    check_in = ''
                    check_out = ''
                    hours = 0.0
                if day_offset == 5 and emp_key == 'jane_smith':
                    status = 'Half-Day'
                    check_out = '13:00'
                    hours = 4.0

                att = Attendance(
                    employee_id=emp_obj.id,
                    date=d,
                    check_in=check_in,
                    check_out=check_out,
                    working_hours=hours,
                    status=status
                )
                db.session.add(att)

        print("[OK] Attendance records created.")

        # ── Projects ─────────────────────────────────────────────────────
        projects_data = [
            {'name': 'Enterprise Portal', 'desc': 'Internal business management platform',
             'start': date(2026, 1, 15), 'end': date(2026, 6, 30),
             'deadline': date(2026, 7, 15), 'estimated_hours': 500,
             'status': 'In Progress', 'created_by': 'admin', 'assigned_pm': 'pm_lead'},
            {'name': 'Mobile App v2', 'desc': 'Client-facing mobile application redesign',
             'start': date(2026, 3, 1), 'end': date(2026, 8, 31),
             'deadline': date(2026, 9, 15), 'estimated_hours': 300,
             'status': 'Not Started', 'created_by': 'admin', 'assigned_pm': 'pm_manager_1'},
            {'name': 'Data Analytics Dashboard', 'desc': 'Business intelligence and reporting tool',
             'start': date(2025, 10, 1), 'end': date(2026, 2, 28),
             'deadline': date(2026, 2, 28), 'estimated_hours': 200,
             'status': 'Completed', 'created_by': 'admin', 'assigned_pm': 'pm_manager_2'},
        ]

        project_objects = {}
        for pd_entry in projects_data:
            proj = Project(
                name=pd_entry['name'],
                description=pd_entry['desc'],
                start_date=pd_entry['start'],
                end_date=pd_entry['end'],
                deadline=pd_entry.get('deadline'),
                estimated_hours=pd_entry.get('estimated_hours', 0),
                status=pd_entry['status'],
                assigned_pm=user_objects[pd_entry['assigned_pm']].id if pd_entry.get('assigned_pm') else None,
                created_by=user_objects[pd_entry['created_by']].id
            )
            db.session.add(proj)
            db.session.flush()
            project_objects[pd_entry['name']] = proj

        print("[OK] Projects created.")

        # ── Project Members ──────────────────────────────────────────────
        members_data = [
            {'project': 'Enterprise Portal', 'user': 'john_doe', 'role': 'Team Lead'},
            {'project': 'Enterprise Portal', 'user': 'jane_smith', 'role': 'Tester'},
            {'project': 'Mobile App v2', 'user': 'john_doe', 'role': 'Developer'},
            {'project': 'Data Analytics Dashboard', 'user': 'finance_head', 'role': 'Designer'},
        ]

        for md in members_data:
            pm = ProjectMember(
                project_id=project_objects[md['project']].id,
                user_id=user_objects[md['user']].id,
                role=md['role']
            )
            db.session.add(pm)

        print("[OK] Project members assigned.")

        # ── Tasks ────────────────────────────────────────────────────────
        tasks_data = [
            {'project': 'Enterprise Portal', 'title': 'Design database schema',
             'desc': 'Create normalized schema for all modules',
             'assigned': 'pm_lead', 'priority': 'High', 'status': 'Done',
             'estimated_hours': 40, 'actual_hours': 35,
             'due': date(2026, 2, 1)},
            {'project': 'Enterprise Portal', 'title': 'Implement authentication',
             'desc': 'Flask-Login with session-based auth and RBAC',
             'assigned': 'john_doe', 'priority': 'Critical', 'status': 'Done',
             'estimated_hours': 60, 'actual_hours': 72,
             'due': date(2026, 2, 15)},
            {'project': 'Enterprise Portal', 'title': 'Build HR module',
             'desc': 'Employee CRUD, leaves, attendance views',
             'assigned': 'john_doe', 'priority': 'High', 'status': 'In Progress',
             'estimated_hours': 80, 'actual_hours': 0,
             'due': date(2026, 3, 15)},
            {'project': 'Enterprise Portal', 'title': 'Build Finance module',
             'desc': 'Expenses, invoices, salary records',
             'assigned': 'john_doe', 'priority': 'High', 'status': 'In Progress',
             'estimated_hours': 80, 'actual_hours': 0,
             'due': date(2026, 4, 1)},
            {'project': 'Enterprise Portal', 'title': 'Frontend polish',
             'desc': 'Responsive design, animations, dark sidebar',
             'assigned': 'john_doe', 'priority': 'Medium', 'status': 'Pending',
             'estimated_hours': 50, 'actual_hours': 0,
             'due': date(2026, 4, 30)},
            {'project': 'Mobile App v2', 'title': 'Wireframe design',
             'desc': 'Create UI/UX wireframes',
             'assigned': 'john_doe', 'priority': 'High', 'status': 'Pending',
             'estimated_hours': 30, 'actual_hours': 0,
             'due': date(2026, 4, 15)},
        ]

        for td in tasks_data:
            task = Task(
                project_id=project_objects[td['project']].id,
                title=td['title'],
                description=td['desc'],
                assigned_to=user_objects[td['assigned']].id if td['assigned'] else None,
                priority=td['priority'],
                status=td['status'],
                estimated_hours=td.get('estimated_hours', 0),
                actual_hours=td.get('actual_hours', 0),
                due_date=td['due']
            )
            db.session.add(task)

        print("[OK] Tasks created.")

        # ── Milestones ─────────────────────────────────────────────────
        milestones_data = [
            {'project': 'Enterprise Portal', 'title': 'Alpha Release',
             'desc': 'All core modules functional', 'deadline': date(2026, 3, 31),
             'status': 'Completed'},
            {'project': 'Enterprise Portal', 'title': 'Beta Release',
             'desc': 'Bug fixes, UI polish, testing', 'deadline': date(2026, 5, 31),
             'status': 'In Progress'},
            {'project': 'Enterprise Portal', 'title': 'Production Launch',
             'desc': 'Final deployment and go-live', 'deadline': date(2026, 7, 15),
             'status': 'Pending'},
            {'project': 'Mobile App v2', 'title': 'Design Approval',
             'desc': 'Wireframes and mockups signed off', 'deadline': date(2026, 4, 30),
             'status': 'Pending'},
            {'project': 'Data Analytics Dashboard', 'title': 'Final Delivery',
             'desc': 'Dashboard delivered and deployed', 'deadline': date(2026, 2, 28),
             'status': 'Completed'},
        ]

        for ms_d in milestones_data:
            ms = Milestone(
                project_id=project_objects[ms_d['project']].id,
                title=ms_d['title'],
                description=ms_d['desc'],
                deadline=ms_d['deadline'],
                status=ms_d['status']
            )
            db.session.add(ms)

        print("[OK] Milestones created.")

        # ── Notifications ──────────────────────────────────────────────
        notifs_data = [
            {'user': 'john_doe', 'title': 'Task Assigned',
             'message': 'You have been assigned "Build HR module" in Enterprise Portal.',
             'category': 'info', 'is_read': True},
            {'user': 'john_doe', 'title': 'Added to Project',
             'message': 'You have been added to project "Enterprise Portal" as Developer.',
             'category': 'info', 'is_read': True},
            {'user': 'pm_lead', 'title': 'Task Completed',
             'message': 'Task "Design database schema" has been marked as Done.',
             'category': 'success', 'is_read': False},
            {'user': 'pm_lead', 'title': 'Milestone Completed',
             'message': 'Milestone "Alpha Release" in Enterprise Portal is complete.',
             'category': 'success', 'is_read': False},
        ]

        for nd in notifs_data:
            n = Notification(
                user_id=user_objects[nd['user']].id,
                title=nd['title'],
                message=nd['message'],
                category=nd['category'],
                is_read=nd['is_read']
            )
            db.session.add(n)

        print("[OK] Notifications created.")

        # ── Expenses ─────────────────────────────────────────────────────
        expenses_data = [
            {'category': 'Software', 'amount': 15000, 'date': date(2026, 3, 5),
             'desc': 'JetBrains IDE license renewal', 'by': 'pm_lead', 'status': 'Approved'},
            {'category': 'Travel', 'amount': 25000, 'date': date(2026, 3, 12),
             'desc': 'Client meeting travel — Mumbai', 'by': 'pm_lead', 'status': 'Approved'},
            {'category': 'Office Supplies', 'amount': 8500, 'date': date(2026, 3, 20),
             'desc': 'Monitors and peripherals', 'by': 'hr_manager', 'status': 'Pending'},
            {'category': 'Marketing', 'amount': 35000, 'date': date(2026, 4, 1),
             'desc': 'Digital marketing campaign Q2', 'by': 'finance_head', 'status': 'Pending'},
        ]

        for ed in expenses_data:
            exp = Expense(
                category=ed['category'], amount=ed['amount'], date=ed['date'],
                description=ed['desc'], submitted_by=user_objects[ed['by']].id, status=ed['status']
            )
            db.session.add(exp)

        print("[OK] Expenses created.")

        # ── Invoices ─────────────────────────────────────────────────────
        invoices_data = [
            {'number': 'INV-2026-001', 'client': 'Acme Corp',
             'amount': 250000, 'issue': date(2026, 1, 15),
             'due': date(2026, 2, 15), 'status': 'Paid',
             'desc': 'Web development services — Phase 1'},
            {'number': 'INV-2026-002', 'client': 'TechStart Inc',
             'amount': 180000, 'issue': date(2026, 2, 1),
             'due': date(2026, 3, 1), 'status': 'Paid',
             'desc': 'Mobile app consulting'},
            {'number': 'INV-2026-003', 'client': 'GlobalTrade Ltd',
             'amount': 450000, 'issue': date(2026, 3, 10),
             'due': date(2026, 4, 10), 'status': 'Unpaid',
             'desc': 'Enterprise portal development'},
        ]

        for inv_d in invoices_data:
            inv = Invoice(
                invoice_number=inv_d['number'], client_name=inv_d['client'],
                amount=inv_d['amount'], issue_date=inv_d['issue'],
                due_date=inv_d['due'], status=inv_d['status'], description=inv_d['desc']
            )
            db.session.add(inv)

        print("[OK] Invoices created.")

        # ── Salary Records ──────────────────────────────────────────────
        months = ['January', 'February', 'March']
        for emp_key, emp_obj in emp_objects.items():
            for month in months:
                basic = emp_obj.salary * 0.60
                hra = emp_obj.salary * 0.25
                deductions = emp_obj.salary * 0.10
                net = basic + hra - deductions
                status = 'Paid' if month != 'March' else 'Processed'
                sal = SalaryRecord(
                    employee_id=emp_obj.id, month=month, year=2026,
                    basic=round(basic), hra=round(hra),
                    deductions=round(deductions), net_salary=round(net), status=status
                )
                db.session.add(sal)

        print("[OK] Salary records created.")

        # ── Performance Reviews (Batch 2) ────────────────────────────────
        perf_data = [
            {'emp': 'john_doe', 'period': 'Q1-2026', 'rating': 4,
             'strengths': 'Strong coding skills, good team player, quick learner',
             'improvements': 'Could improve code documentation and testing practices',
             'comments': 'Excellent progress in Q1. Recommend for senior developer consideration.'},
            {'emp': 'jane_smith', 'period': 'Q1-2026', 'rating': 5,
             'strengths': 'Exceptional attention to detail, accurate financial reporting',
             'improvements': 'Could take more initiative in process improvement',
             'comments': 'Outstanding performance. Key contributor to financial module.'},
            {'emp': 'bob_wilson', 'period': 'Q1-2026', 'rating': 3,
             'strengths': 'Good communication skills, reliable employee',
             'improvements': 'Needs to improve HR analytics skills and policy knowledge',
             'comments': 'Solid performer. Training recommended for HR analytics tools.'},
            {'emp': 'pm_lead', 'period': 'Annual-2025', 'rating': 5,
             'strengths': 'Excellent leadership, strong technical architecture skills',
             'improvements': 'Delegation skills could be improved',
             'comments': 'High performer. Promoted to Tech Lead based on 2025 annual review.'},
        ]
        for pd in perf_data:
            review = PerformanceReview(
                employee_id=emp_objects[pd['emp']].id,
                reviewer_id=user_objects['hr_manager'].id,
                review_period=pd['period'],
                rating=pd['rating'],
                strengths=pd['strengths'],
                improvements=pd['improvements'],
                comments=pd['comments'],
                status='Submitted'
            )
            db.session.add(review)
        print("[OK] Performance reviews created.")

        # ── Job Postings & Candidates (Batch 2) ─────────────────────────
        job1 = JobPosting(
            title='Senior Software Developer',
            department_id=dept_map['ENG'].id,
            description='Looking for an experienced developer to join the engineering team.',
            requirements='5+ years experience in Python/Flask, strong SQL skills, team leadership experience.',
            vacancies=2, status='Open', created_by=user_objects['hr_manager'].id
        )
        job2 = JobPosting(
            title='Marketing Executive',
            department_id=dept_map['MKT'].id,
            description='Drive digital marketing campaigns and brand visibility.',
            requirements='2+ years in digital marketing, SEO/SEM skills, content creation experience.',
            vacancies=1, status='Open', created_by=user_objects['hr_manager'].id
        )
        db.session.add_all([job1, job2])
        db.session.flush()

        candidates_data = [
            {'job': job1, 'name': 'Arjun Mehta', 'email': 'arjun.m@email.com',
             'phone': '+91 88888 11111', 'status': 'Interview',
             'notes': '7 years Python experience, ex-Google'},
            {'job': job1, 'name': 'Sneha Rao', 'email': 'sneha.r@email.com',
             'phone': '+91 88888 22222', 'status': 'Screening',
             'notes': '5 years Flask/Django, strong backend skills'},
            {'job': job1, 'name': 'Vikram Singh', 'email': 'vikram.s@email.com',
             'phone': '+91 88888 33333', 'status': 'Applied',
             'notes': '4 years fullstack, React + Python'},
            {'job': job2, 'name': 'Pooja Nair', 'email': 'pooja.n@email.com',
             'phone': '+91 88888 44444', 'status': 'Offer',
             'notes': '3 years digital marketing, strong analytics skills'},
            {'job': job2, 'name': 'Karan Joshi', 'email': 'karan.j@email.com',
             'phone': '+91 88888 55555', 'status': 'Rejected',
             'notes': 'Good profile but lacks required SEO experience'},
        ]
        candidate_objects = []
        for cd in candidates_data:
            c = Candidate(
                job_id=cd['job'].id, name=cd['name'], email=cd['email'],
                phone=cd['phone'], status=cd['status'], notes=cd['notes']
            )
            db.session.add(c)
            db.session.flush()
            candidate_objects.append(c)

        # Schedule interviews
        tomorrow = date.today() + timedelta(days=1)
        intv1 = Interview(
            candidate_id=candidate_objects[0].id,
            interviewer_id=user_objects['pm_lead'].id,
            scheduled_at=datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time()),
            duration_mins=60, interview_type='Technical', status='Scheduled'
        )
        intv2 = Interview(
            candidate_id=candidate_objects[0].id,
            interviewer_id=user_objects['hr_manager'].id,
            scheduled_at=datetime.combine(tomorrow, datetime.strptime('14:00', '%H:%M').time()),
            duration_mins=45, interview_type='HR', status='Scheduled'
        )
        db.session.add_all([intv1, intv2])
        print("[OK] Recruitment data created (jobs, candidates, interviews).")

        # ── Employee Expense Claims (Self-Service) ───────────────────────
        expense_claims = [
            {'emp': 'john_doe', 'category': 'Travel', 'amount': 3500,
             'date': date(2026, 4, 2), 'desc': 'Cab fare to client office',
             'status': 'Approved'},
            {'emp': 'john_doe', 'category': 'Software', 'amount': 1200,
             'date': date(2026, 4, 8), 'desc': 'Postman Pro license (monthly)',
             'status': 'Pending'},
            {'emp': 'jane_smith', 'category': 'Medical', 'amount': 5000,
             'date': date(2026, 3, 25), 'desc': 'Annual health checkup',
             'status': 'Approved'},
            {'emp': 'pm_lead', 'category': 'Travel', 'amount': 12000,
             'date': date(2026, 4, 5), 'desc': 'Flight to Bangalore for team meeting',
             'status': 'Pending'},
            {'emp': 'bob_wilson', 'category': 'Training', 'amount': 8000,
             'date': date(2026, 3, 15), 'desc': 'HR Analytics online course',
             'status': 'Rejected'},
        ]
        for ec in expense_claims:
            claim = EmployeeExpense(
                employee_id=emp_objects[ec['emp']].id,
                category=ec['category'],
                amount=ec['amount'],
                date=ec['date'],
                description=ec['desc'],
                status=ec['status']
            )
            db.session.add(claim)
        print("[OK] Employee expense claims created.")

        # ── Profile Update Requests ──────────────────────────────────────
        profile_requests = [
            {'emp': 'john_doe', 'field': 'bank_account', 'old': 'XXXX-XXXX-004',
             'new': 'SBI-1234567890', 'status': 'Pending'},
            {'emp': 'jane_smith', 'field': 'pan_number', 'old': 'EFGJS7890E',
             'new': 'EFGJS7890F', 'status': 'Approved',
             'reviewed_by': 'hr_manager'},
        ]
        for pr in profile_requests:
            req = ProfileUpdateRequest(
                employee_id=emp_objects[pr['emp']].id,
                field_name=pr['field'],
                old_value=pr['old'],
                new_value=pr['new'],
                status=pr['status'],
                reviewed_by=user_objects[pr['reviewed_by']].id if pr.get('reviewed_by') else None
            )
            db.session.add(req)
        print("[OK] Profile update requests created.")

        # ── Comp-Off Records ─────────────────────────────────────────────
        comp_offs_data = [
            {'emp': 'john_doe', 'date': date(2026, 4, 10), 'hours': 2.5, 'status': 'Earned'},
            {'emp': 'bob_wilson', 'date': date(2026, 4, 8), 'hours': 1.5, 'status': 'Earned'},
            {'emp': 'john_doe', 'date': date(2026, 3, 25), 'hours': 3.0, 'status': 'Used',
             'used_date': date(2026, 4, 1)},
        ]
        for co in comp_offs_data:
            comp = CompOff(
                employee_id=emp_objects[co['emp']].id,
                earned_date=co['date'],
                hours_extra=co['hours'],
                status=co['status'],
                used_date=co.get('used_date')
            )
            db.session.add(comp)
        print("[OK] Comp-off records created.")

        # ── Shift Swap Requests ──────────────────────────────────────────
        swap1 = ShiftSwapRequest(
            employee_id=emp_objects['bob_wilson'].id,
            current_shift_id=shift_map['Night'].id,
            requested_shift_id=shift_map['Morning'].id,
            reason='Night shift affecting health, requesting morning shift',
            status='Pending'
        )
        swap2 = ShiftSwapRequest(
            employee_id=emp_objects['john_doe'].id,
            current_shift_id=shift_map['Morning'].id,
            requested_shift_id=shift_map['Afternoon'].id,
            reason='Personal schedule change',
            status='Approved',
            reviewed_by=user_objects['hr_manager'].id
        )
        db.session.add_all([swap1, swap2])
        print("[OK] Shift swap requests created.")

        # ── Additional Employee Notifications ────────────────────────────
        emp_notifs = [
            {'user': 'john_doe', 'title': 'Leave Approved',
             'message': 'Your Casual Leave request (5-7 Apr) has been approved.',
             'category': 'success', 'is_read': True},
            {'user': 'john_doe', 'title': 'Expense Approved',
             'message': 'Your travel expense claim of ₹3,500 has been approved.',
             'category': 'success', 'is_read': False},
            {'user': 'john_doe', 'title': 'Profile Update Pending',
             'message': 'Your bank account update request is pending HR review.',
             'category': 'info', 'is_read': False},
            {'user': 'jane_smith', 'title': 'Payslip Available',
             'message': 'Your payslip for March 2026 is now available.',
             'category': 'info', 'is_read': False},
            {'user': 'pm_lead', 'title': 'Leave Request Submitted',
             'message': 'Your Earned Leave request (20-25 Apr) has been submitted.',
             'category': 'info', 'is_read': False},
            {'user': 'bob_wilson', 'title': 'Expense Rejected',
             'message': 'Your training expense claim of ₹8,000 was rejected.',
             'category': 'danger', 'is_read': False},
        ]
        for en in emp_notifs:
            n = Notification(
                user_id=user_objects[en['user']].id,
                title=en['title'],
                message=en['message'],
                category=en['category'],
                is_read=en['is_read']
            )
            db.session.add(n)
        print("[OK] Employee notifications created.")

        # ── Commit all ───────────────────────────────────────────────────
        db.session.commit()
        print("\n" + "=" * 60)
        print("  DATABASE SEEDED SUCCESSFULLY!")
        print("=" * 60)
        print("\nAdmin Configuration:")
        print(f"  Departments:   {len(departments)}")
        print(f"  Designations:  {len(designations)}")
        print(f"  Leave Policies: {len(leave_policies)} global + {len(role_policies)} role-specific")
        print(f"  Shifts:        {len(shifts)} (Morning, Afternoon, Night)")
        print(f"  Attendance:    {att_rule.work_start}-{att_rule.work_end} (General Shift)")
        print("\nTest Accounts:")
        print("-" * 60)
        print(f"  {'Username':<16} {'Password':<12} {'Role':<18} Modules")
        print("-" * 60)
        for ud in users_data:
            mods = ', '.join(ud['modules'])
            role = 'Admin' if ud['is_admin'] else 'User'
            print(f"  {ud['username']:<16} {ud['password']:<12} {role:<18} {mods}")
        print("-" * 60)
        print("\nRun the app:  python app.py")
        print("Open:         http://localhost:5000")
        print()


if __name__ == '__main__':
    seed()
