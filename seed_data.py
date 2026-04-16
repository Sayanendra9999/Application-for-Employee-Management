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
                        Department, Designation, LeavePolicy, AttendanceRule)


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
            LeavePolicy(leave_type='Casual Leave', total_days=12,
                        carry_forward=False, description='For personal/family reasons'),
            LeavePolicy(leave_type='Sick Leave', total_days=10,
                        carry_forward=False, description='For health-related absences'),
            LeavePolicy(leave_type='Earned Leave', total_days=15,
                        carry_forward=True, max_carry_days=5,
                        description='Accrued leave, can carry forward up to 5 days'),
        ]
        db.session.add_all(leave_policies)
        db.session.flush()
        print("[OK] Leave policies created.")

        # ── Attendance Rules (Admin-managed) ─────────────────────────────
        att_rule = AttendanceRule(
            work_start='09:00', work_end='18:00',
            late_threshold_mins=15, half_day_hours=4.0, full_day_hours=8.0
        )
        db.session.add(att_rule)
        db.session.flush()
        print("[OK] Attendance rules configured.")

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

        print("[OK] Employee records created.")

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
             'deadline': date(2026, 7, 15),
             'status': 'In Progress', 'created_by': 'pm_lead'},
            {'name': 'Mobile App v2', 'desc': 'Client-facing mobile application redesign',
             'start': date(2026, 3, 1), 'end': date(2026, 8, 31),
             'deadline': date(2026, 9, 15),
             'status': 'Not Started', 'created_by': 'pm_lead'},
            {'name': 'Data Analytics Dashboard', 'desc': 'Business intelligence and reporting tool',
             'start': date(2025, 10, 1), 'end': date(2026, 2, 28),
             'deadline': date(2026, 2, 28),
             'status': 'Completed', 'created_by': 'admin'},
        ]

        project_objects = {}
        for pd_entry in projects_data:
            proj = Project(
                name=pd_entry['name'],
                description=pd_entry['desc'],
                start_date=pd_entry['start'],
                end_date=pd_entry['end'],
                deadline=pd_entry.get('deadline'),
                status=pd_entry['status'],
                created_by=user_objects[pd_entry['created_by']].id
            )
            db.session.add(proj)
            db.session.flush()
            project_objects[pd_entry['name']] = proj

        print("[OK] Projects created.")

        # ── Project Members ──────────────────────────────────────────────
        members_data = [
            {'project': 'Enterprise Portal', 'user': 'pm_lead', 'role': 'Lead'},
            {'project': 'Enterprise Portal', 'user': 'john_doe', 'role': 'Developer'},
            {'project': 'Enterprise Portal', 'user': 'jane_smith', 'role': 'Tester'},
            {'project': 'Mobile App v2', 'user': 'pm_lead', 'role': 'Lead'},
            {'project': 'Mobile App v2', 'user': 'john_doe', 'role': 'Developer'},
            {'project': 'Data Analytics Dashboard', 'user': 'pm_lead', 'role': 'Lead'},
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
             'due': date(2026, 2, 1)},
            {'project': 'Enterprise Portal', 'title': 'Implement authentication',
             'desc': 'Flask-Login with session-based auth and RBAC',
             'assigned': 'john_doe', 'priority': 'Critical', 'status': 'Done',
             'due': date(2026, 2, 15)},
            {'project': 'Enterprise Portal', 'title': 'Build HR module',
             'desc': 'Employee CRUD, leaves, attendance views',
             'assigned': 'john_doe', 'priority': 'High', 'status': 'In Progress',
             'due': date(2026, 3, 15)},
            {'project': 'Enterprise Portal', 'title': 'Build Finance module',
             'desc': 'Expenses, invoices, salary records',
             'assigned': 'john_doe', 'priority': 'High', 'status': 'In Progress',
             'due': date(2026, 4, 1)},
            {'project': 'Enterprise Portal', 'title': 'Frontend polish',
             'desc': 'Responsive design, animations, dark sidebar',
             'assigned': 'john_doe', 'priority': 'Medium', 'status': 'Pending',
             'due': date(2026, 4, 30)},
            {'project': 'Mobile App v2', 'title': 'Wireframe design',
             'desc': 'Create UI/UX wireframes',
             'assigned': 'john_doe', 'priority': 'High', 'status': 'Pending',
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

        # ── Commit all ───────────────────────────────────────────────────
        db.session.commit()
        print("\n" + "=" * 60)
        print("  DATABASE SEEDED SUCCESSFULLY!")
        print("=" * 60)
        print("\nAdmin Configuration:")
        print(f"  Departments:   {len(departments)}")
        print(f"  Designations:  {len(designations)}")
        print(f"  Leave Policies: {len(leave_policies)}")
        print(f"  Attendance:    {att_rule.work_start}-{att_rule.work_end}, late>{att_rule.late_threshold_mins}min")
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
