# Recruitment Portal — End-to-End Hiring Workflow Upgrade

Transform the existing basic recruitment module (job list + candidate CRUD) into a **complete hiring workflow system**: Job Request → Screening → Interview → Offer → Hired → Onboarding.

## What Already Exists

| Layer | What's There | Status |
|---|---|---|
| **Models** | `JobPosting`, `Candidate`, `Interview` | ✅ Complete |
| **Forms** | `JobPostingForm`, `CandidateForm`, `InterviewForm`, `InterviewFeedbackForm` | ✅ Complete |
| **Routes** | CRUD for jobs, candidates, interviews, feedback | ✅ Complete |
| **Templates** | `recruitment.html`, `job_detail.html`, `job_form.html`, `candidate_form.html`, `interview_form.html`, `interview_feedback.html` | ✅ Complete |
| **Services** | None for recruitment (all inline in routes) | ❌ Missing |
| **Workflow** | No pipeline stages, no offer letter, no Hired→User conversion, no link to onboarding | ❌ Missing |

## What's Missing for End-to-End Pipeline

1. **Job Request workflow** — Department head / PM raises a "hiring request" that HR approves before it becomes a posting
2. **Offer Management** — Generate offer details (salary, designation, joining date), candidate accepts/rejects
3. **Hired → User Conversion** — When a candidate is "Hired", auto-create a User + Employee record (like Admin's `add_user`) and push to HR onboarding queue
4. **Pipeline Kanban view** — Visual drag-friendly pipeline showing candidates across stages
5. **Recruitment services** — Business logic moved from routes into `services.py`
6. **Dashboard integration** — Recruitment stats on HR dashboard
7. **Resume upload** — Candidate's resume file (already has `resume_file` column, but no upload UI)

---

## User Review Required

> [!IMPORTANT]
> **Hired → Auto User Creation**: When a candidate is marked "Hired", the system will auto-create a `User` + `Employee` record with a temporary password (same flow as Admin's `add_user`). The hired person immediately appears in HR's "Unassigned Employees" onboarding queue. HR then completes the profile (department, designation, salary, bank, PAN) using the existing `complete_profile` flow. **Is this acceptable, or do you want Admin to manually create the user?**

> [!IMPORTANT]
> **Job Request → Job Posting approval**: Currently, HR directly creates job postings. The plan adds an optional "Hiring Request" model where a PM or department lead submits a request, and HR approves it to become a posting. **Do you want this approval step, or keep the current direct-creation by HR?**

> [!WARNING]
> **Resume uploads**: The `Candidate` model already has a `resume_file` column but no upload route/UI exists. This plan adds resume upload on the candidate form. Files will go to `static/uploads/resumes/`. **Is the existing `UPLOAD_FOLDER` config appropriate, or do you want a separate folder?**

## Open Questions

1. **Offer letter details** — Should the offer just capture salary/designation/joining date in a database row, or do you also want a downloadable PDF offer letter generated?
2. **Email notifications** — Should the system send emails when an interview is scheduled or an offer is extended? (The app currently has no email integration.)
3. **Candidate portal** — Should candidates be able to view their application status, or is everything managed by HR internally?

---

## Proposed Changes

### Models — [models.py](file:///c:/JGpc/app_at_present/app/models.py)

#### [MODIFY] [models.py](file:///c:/JGpc/app_at_present/app/models.py)

**1. Add `HiringRequest` model** (optional, per user preference):
```python
class HiringRequest(db.Model):
    __tablename__ = 'hiring_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    designation_id = db.Column(db.Integer, db.ForeignKey('designations.id'), nullable=True)
    justification = db.Column(db.Text, default='')
    vacancies = db.Column(db.Integer, default=1)
    priority = db.Column(db.String(20), default='Normal')   # Low, Normal, High, Urgent
    budget_min = db.Column(db.Float, nullable=True)
    budget_max = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='Pending')    # Pending, Approved, Rejected, Converted
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    job_posting_id = db.Column(db.Integer, db.ForeignKey('job_postings.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    requester = db.relationship('User', foreign_keys=[requested_by])
    approver = db.relationship('User', foreign_keys=[approved_by])
    department = db.relationship('Department')
    designation = db.relationship('Designation')
    job_posting = db.relationship('JobPosting', backref='hiring_request')
```

**2. Add `Offer` model**:
```python
class Offer(db.Model):
    __tablename__ = 'offers'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    offered_salary = db.Column(db.Float, nullable=False)
    offered_designation_id = db.Column(db.Integer, db.ForeignKey('designations.id'), nullable=True)
    joining_date = db.Column(db.Date, nullable=True)
    offer_notes = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='Pending')    # Pending, Accepted, Rejected, Withdrawn
    offered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    responded_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    candidate = db.relationship('Candidate', backref=db.backref('offer', uselist=False))
    designation = db.relationship('Designation')
    offerer = db.relationship('User', foreign_keys=[offered_by])
```

**3. Enhance existing `Candidate` model** — add `source` and `hired_user_id`:
```python
# Add to Candidate:
source = db.Column(db.String(50), default='Direct')     # Direct, Referral, LinkedIn, Job Portal, Agency
hired_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Links to created user after hire
```

**4. Enhance `JobPosting`** — add `salary_min`, `salary_max`, `employment_type`, `location`:
```python
# Add to JobPosting:
salary_min = db.Column(db.Float, nullable=True)
salary_max = db.Column(db.Float, nullable=True)
employment_type = db.Column(db.String(30), default='Full-Time')  # Full-Time, Part-Time, Contract, Intern
location = db.Column(db.String(100), default='')
```

---

### Forms — [forms.py](file:///c:/JGpc/app_at_present/app/hr/forms.py)

#### [MODIFY] [forms.py](file:///c:/JGpc/app_at_present/app/hr/forms.py)

**1. Add `HiringRequestForm`**:
```python
class HiringRequestForm(FlaskForm):
    title = StringField('Position Title', validators=[DataRequired(), Length(3, 150)])
    department_id = SelectField('Department', coerce=int, validators=[DataRequired()])
    designation_id = SelectField('Designation', coerce=int, validators=[Optional()])
    justification = TextAreaField('Justification', validators=[DataRequired(), Length(10, 3000)])
    vacancies = IntegerField('Vacancies', validators=[DataRequired(), NumberRange(1, 50)], default=1)
    priority = SelectField('Priority', choices=[
        ('Low', 'Low'), ('Normal', 'Normal'), ('High', 'High'), ('Urgent', 'Urgent')
    ], default='Normal')
    budget_min = FloatField('Budget Min (₹)', validators=[Optional()])
    budget_max = FloatField('Budget Max (₹)', validators=[Optional()])
    submit = SubmitField('Submit Request')
```

**2. Add `OfferForm`**:
```python
class OfferForm(FlaskForm):
    offered_salary = FloatField('Offered Salary (₹/month)', validators=[DataRequired()])
    offered_designation_id = SelectField('Designation', coerce=int, validators=[Optional()])
    joining_date = DateField('Proposed Joining Date', validators=[Optional()])
    offer_notes = TextAreaField('Offer Notes / Terms', validators=[Optional(), Length(0, 2000)])
    submit = SubmitField('Extend Offer')
```

**3. Update `JobPostingForm`** — add new fields:
```python
# Add to existing form:
salary_min = FloatField('Salary Range Min (₹)', validators=[Optional()])
salary_max = FloatField('Salary Range Max (₹)', validators=[Optional()])
employment_type = SelectField('Employment Type', choices=[
    ('Full-Time', 'Full-Time'), ('Part-Time', 'Part-Time'),
    ('Contract', 'Contract'), ('Intern', 'Intern')
], default='Full-Time')
location = StringField('Location', validators=[Optional(), Length(0, 100)])
```

**4. Update `CandidateForm`** — add `source` and `resume` file upload:
```python
# Add to existing form:
source = SelectField('Source', choices=[
    ('Direct', 'Direct Application'), ('Referral', 'Employee Referral'),
    ('LinkedIn', 'LinkedIn'), ('Job Portal', 'Job Portal'), ('Agency', 'Recruitment Agency')
], default='Direct')
resume = FileField('Resume', validators=[
    Optional(),
    FileAllowed(['pdf', 'doc', 'docx'], 'Only PDF and DOC files allowed.')
])
```

---

### Services — [services.py](file:///c:/JGpc/app_at_present/app/hr/services.py)

#### [MODIFY] [services.py](file:///c:/JGpc/app_at_present/app/hr/services.py)

Add a new `RECRUITMENT SERVICES` section with:

```python
# ===========================================================================
# RECRUITMENT SERVICES
# ===========================================================================
def get_pipeline_stats(job_id=None):
    """Get candidate pipeline statistics, optionally for a specific job."""

def convert_hired_to_employee(candidate_id, hr_user_id):
    """When candidate reaches 'Hired' status:
    1. Create a User with temp password
    2. Create an Employee record (unassigned)
    3. Assign 'employee' module
    4. Initialize leave balances
    5. Link candidate.hired_user_id
    Returns (success, message, user_info)
    """

def approve_hiring_request(request_id, approver_id):
    """Approve a hiring request and optionally convert to a job posting."""

def reject_hiring_request(request_id, approver_id, reason=''):
    """Reject a hiring request."""

def extend_offer(candidate_id, salary, designation_id, joining_date, notes, offered_by):
    """Create an offer for a candidate. Auto-updates candidate status to 'Offer'."""

def respond_to_offer(offer_id, action):  # action: 'accept' or 'reject'
    """Candidate accepts or rejects. If accepted, candidate status → 'Hired'."""
```

---

### Routes — [routes.py](file:///c:/JGpc/app_at_present/app/hr/routes.py)

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/hr/routes.py)

**New routes** to add in the RECRUITMENT section:

| Route | Method | Purpose |
|---|---|---|
| `/recruitment/pipeline` | GET | Kanban-style pipeline view |
| `/recruitment/hiring-requests` | GET | List all hiring requests |
| `/recruitment/hiring-requests/add` | GET, POST | Submit a hiring request |
| `/recruitment/hiring-requests/<id>/approve` | POST | Approve → creates job posting |
| `/recruitment/hiring-requests/<id>/reject` | POST | Reject a request |
| `/recruitment/jobs/<job_id>/edit` | GET, POST | Edit an existing job posting |
| `/recruitment/candidates/<id>/offer` | GET, POST | Extend an offer |
| `/recruitment/offers/<id>/respond` | POST | Accept / reject offer |
| `/recruitment/candidates/<id>/hire` | POST | Convert hired candidate to employee |

**Modify existing routes**:
- `recruitment()` — add pipeline stats, hiring request counts, active offers count
- `add_candidate()` — handle resume file upload
- `job_detail()` — show offer details and "Convert to Employee" button for Hired candidates

---

### Templates

#### [MODIFY] [recruitment.html](file:///c:/JGpc/app_at_present/app/templates/hr/recruitment.html)
- Add tabbed view: **Job Postings** | **Pipeline** | **Hiring Requests**
- Add richer pipeline stats with visual progress bars
- Add hiring request count badge and link

#### [NEW] `pipeline.html`
- Kanban board with columns: Applied → Screening → Interview → Offer → Hired
- Each candidate card shows name, job title, days in stage, interview rating
- Click card to open candidate detail

#### [NEW] `hiring_requests.html`
- Table listing all hiring requests with status badges
- Approve/Reject action buttons

#### [NEW] `hiring_request_form.html`
- Form for submitting a new hiring request

#### [NEW] `offer_form.html`
- Form for extending an offer to a candidate (salary, designation, joining date)

#### [NEW] `candidate_detail.html`
- Full candidate profile view: personal info, resume download, interview history with feedback, offer status, timeline of status changes
- "Convert to Employee" button when status is Hired

#### [MODIFY] [job_detail.html](file:///c:/JGpc/app_at_present/app/templates/hr/job_detail.html)
- Add "Edit Job" button
- Show offer status per candidate
- Show "Convert to Employee" button for Hired candidates
- Show salary range and employment type

#### [MODIFY] [candidate_form.html](file:///c:/JGpc/app_at_present/app/templates/hr/candidate_form.html)
- Add source field and resume upload

#### [MODIFY] [job_form.html](file:///c:/JGpc/app_at_present/app/templates/hr/job_form.html)
- Add salary range, employment type, location fields

#### [MODIFY] [dashboard.html](file:///c:/JGpc/app_at_present/app/templates/hr/dashboard.html)
- Add recruitment stats card: open positions, active candidates, pending offers, recent hires

---

### Schema — [schema.sql](file:///c:/JGpc/app_at_present/schema.sql)

#### [MODIFY] [schema.sql](file:///c:/JGpc/app_at_present/schema.sql)

Add new table DDLs for `hiring_requests` and `offers`, plus `ALTER` columns on `candidates` and `job_postings`.

---

### Dashboard Route

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/hr/routes.py) (dashboard function)

Add to the dashboard context:
- `open_positions` — count of open job postings
- `active_candidates` — count of candidates not in Hired/Rejected
- `pending_offers` — count of offers with status=Pending
- `recent_hires` — last 5 candidates with status=Hired

---

## Verification Plan

### Automated Tests
- Run the Flask app: `python app.py` — verify no import errors
- Check DB migrations: tables created correctly via SQLAlchemy `create_all`
- Hit all new routes in browser to verify no 500 errors

### Manual Verification
1. Create a Hiring Request → Approve → verify it creates a Job Posting
2. Add a Candidate to the job → Upload resume → Schedule interview → Submit feedback
3. Extend Offer → Accept Offer → candidate status moves to "Hired"
4. Click "Convert to Employee" → verify User + Employee created → appears in HR onboarding queue
5. Complete profile in HR onboarding → verify end-to-end flow
6. Check Pipeline Kanban view renders correctly with candidate cards
7. Verify dashboard stats are accurate
