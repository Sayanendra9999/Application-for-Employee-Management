# HR Module — Batch 2 Walkthrough

## Overview

Batch 2 completes the HR module by adding **4 remaining features**: Performance Management, Recruitment, Payroll Input, and Document Management. Combined with Batch 1, the HR module now has **34 routes**, **13 forms**, and a full **services layer**.

---

## Change Summary

| Metric | Batch 1 | Batch 2 | Total |
|---|---|---|---|
| **Routes** | 15 | 19 | **34** |
| **Forms** | 6 | 7 | **13** |
| **Templates** | 9 | 12 | **21** |
| **Service Functions** | 12 | 4 | **16** |
| **Database Models** | 7 new | 0 new (stubs existed) | **7** |
| **Seed Records** | Core data | +4 reviews, 2 jobs, 5 candidates, 2 interviews | — |

---

## Features Implemented (Batch 2)

### 1. Performance Management — NEW

| Feature | Details |
|---|---|
| **Create reviews** | Manager/HR submits review for an employee |
| **Review periods** | Auto-generated (Q1-Q4, Annual) for current and previous year |
| **Rating scale** | 1–5 stars with visual star display |
| **Structured feedback** | Strengths, improvements, comments (separate fields) |
| **Status workflow** | Draft → Submitted → Acknowledged |
| **Filters** | By review period and department |

**Routes (4):**
- `GET /hr/performance` — List with period/dept filters
- `GET/POST /hr/performance/add` — Create review
- `GET /hr/performance/<id>` — Detail view with 3-column layout
- `GET/POST /hr/performance/<id>/edit` — Edit review

**Templates (3):** `performance.html`, `performance_form.html`, `performance_detail.html`

---

### 2. Recruitment Module — NEW

| Feature | Details |
|---|---|
| **Job postings** | Create postings linked to Admin departments/designations |
| **Pipeline stats** | Visual counters: Applied → Screening → Interview → Offer → Hired/Rejected |
| **Candidate management** | Add candidates with contact info, notes, status tracking |
| **Interview scheduling** | Assign interviewer, date, time, duration, type (Technical/HR/Managerial) |
| **Interview feedback** | Rating (1–5) and detailed assessment after interview |
| **Auto-status update** | Scheduling interview auto-updates candidate status |

**Routes (7):**
- `GET /hr/recruitment` — Jobs list with pipeline stats
- `GET/POST /hr/recruitment/jobs/add` — Create job posting
- `GET /hr/recruitment/jobs/<id>` — Job detail with candidates + inline interviews
- `GET/POST /hr/recruitment/jobs/<id>/candidates/add` — Add candidate
- `GET/POST /hr/recruitment/candidates/<id>/edit` — Edit candidate status
- `GET/POST /hr/recruitment/candidates/<id>/interview` — Schedule interview
- `GET/POST /hr/recruitment/interviews/<id>/feedback` — Submit feedback

**Templates (5):** `recruitment.html`, `job_form.html`, `job_detail.html`, `candidate_form.html`, `interview_form.html`, `interview_feedback.html`

**How the pipeline works:**
```
HR creates Job Posting (Open)
    ↓
HR adds Candidate (status: Applied)
    ↓
HR moves to Screening → schedules Interview → system auto-sets "Interview"
    ↓
Interviewer submits feedback + rating
    ↓
HR moves to Offer → Hired (or Rejected)
```

---

### 3. Payroll Input (HR → Finance Bridge) — NEW

| Feature | Details |
|---|---|
| **Auto-generate** | One-click generates payroll inputs for all employees for a month |
| **Attendance pull** | Working days, present days auto-calculated from attendance records |
| **Leave pull** | Approved leaves in the month auto-counted |
| **HR adjustments** | Overtime hours, bonus, deduction notes (editable by HR) |
| **Bulk submit** | Submit all Draft inputs to Finance in one click |
| **Status workflow** | Draft → Submitted (locked, visible to Finance) |
| **Duplicate prevention** | Won't re-create if input already exists for employee+month+year |

**Routes (4):**
- `GET /hr/payroll` — Monthly list with filters
- `GET/POST /hr/payroll/generate` — Generate inputs for a month
- `GET/POST /hr/payroll/<id>/edit` — Edit draft (overtime, bonus, deductions)
- `POST /hr/payroll/submit` — Bulk submit to Finance

**Templates (3):** `payroll_input.html`, `payroll_generate.html`, `payroll_form.html`

**How it bridges HR → Finance:**
```
HR generates payroll for April 2026
    ↓
System auto-pulls: working days, present days, leaves from attendance/leave data
    ↓
HR edits: adds overtime (3h), bonus (₹5000), notes ("Late deduction ₹500")
    ↓
HR clicks "Submit All to Finance" → Status changes to Submitted → Locked
    ↓
Finance module can read submitted payroll inputs (salary calculation is Finance's job)
```

---

### 4. Document Management — NEW

| Feature | Details |
|---|---|
| **Upload** | Upload files per employee (max 5MB) |
| **Categories** | ID Proof, PAN Card, Aadhar, Offer Letter, Resume, Certificate, Relieving Letter, Other |
| **Allowed formats** | PDF, DOC, DOCX, JPG, JPEG, PNG, TXT, XLSX, XLS |
| **Safe storage** | Files renamed with UUID to prevent conflicts |
| **Download** | Original filename preserved on download |
| **Delete** | Removes file from disk + database record |
| **Employee filter** | View documents for all or specific employee |

**Routes (4):**
- `GET /hr/documents` — Document list with employee filter
- `GET/POST /hr/documents/upload` — Upload form
- `GET /hr/documents/<id>/download` — Download file
- `POST /hr/documents/<id>/delete` — Delete document

**Templates (2):** `documents.html`, `document_upload.html`

---

## Services Added (Batch 2)

| Service | Purpose |
|---|---|
| `generate_payroll_inputs(year, month)` | Auto-creates PayrollInput rows from attendance/leave data |
| `allowed_file(filename, extensions)` | Validates file extension for uploads |
| `generate_safe_filename(name, emp_code)` | Creates unique filename with UUID |
| `get_review_periods()` | Generates review period dropdown options |

---

## Config Changes

```python
# Added to config.py
UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads', 'documents')
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'txt', 'xlsx', 'xls'}
```

---

## Files Modified/Created (Batch 2 Only)

| File | Status | Details |
|---|---|---|
| `config.py` | **Modified** | Added UPLOAD_FOLDER, MAX_CONTENT_LENGTH, ALLOWED_EXTENSIONS |
| `app/models.py` | **Modified** | Added department/designation relationships to JobPosting, renamed PerformanceReview.employee_rel → employee |
| `app/hr/routes.py` | **Modified** | Added 19 new routes (was 15, now 34). Updated attendance check-in route for employee search filtering. |
| `app/hr/forms.py` | **Modified** | Added 7 new forms (was 6, now 13) |
| `app/hr/services.py` | **Modified** | Added 4 service functions |
| `app/templates/hr/dashboard.html` | **Modified** | Added 4 Batch 2 quick links |
| `app/templates/hr/performance.html` | **New** | Reviews list with star ratings |
| `app/templates/hr/performance_form.html` | **New** | Create/edit review |
| `app/templates/hr/performance_detail.html` | **New** | Review detail with 3-column layout |
| `app/templates/hr/recruitment.html` | **New** | Jobs list with pipeline stats |
| `app/templates/hr/job_form.html` | **New** | Create job posting |
| `app/templates/hr/job_detail.html` | **New** | Job detail with candidates + inline interviews |
| `app/templates/hr/candidate_form.html` | **New** | Add/edit candidate |
| `app/templates/hr/interview_form.html` | **New** | Schedule interview |
| `app/templates/hr/interview_feedback.html` | **New** | Submit feedback |
| `app/templates/hr/payroll_input.html` | **New** | Monthly payroll list with bulk submit |
| `app/templates/hr/payroll_generate.html` | **New** | Generate payroll inputs form |
| `app/templates/hr/payroll_form.html` | **New** | Edit individual payroll with auto-calculated data |
| `app/templates/hr/documents.html` | **New** | Document list with download/delete |
| `app/templates/hr/document_upload.html` | **New** | Upload form |
| `app/templates/hr/attendance_checkin.html` | **Modified** | Added employee search filter and clear button |
| `seed_data.py` | **Modified** | Added performance reviews, job postings, candidates, interviews |

**Total new files: 12** · **Modified files: 8**

---

## HR Module — Complete Feature Matrix

| Feature | Batch | Routes | Status |
|---|---|---|---|
| Employee Management | 1 | 5 | ✅ Complete |
| Attendance System | 1 | 3 | ✅ Complete |
| Leave Management | 1 | 3 | ✅ Complete |
| Dashboard | 1 | 1 | ✅ Complete |
| API (designations) | 1 | 1 | ✅ Complete |
| Employee Leave Validation | 1 | 2 | ✅ Complete |
| Performance Management | **2** | 4 | ✅ Complete |
| Recruitment Pipeline | **2** | 7 | ✅ Complete |
| Payroll Input | **2** | 4 | ✅ Complete |
| Document Management | **2** | 4 | ✅ Complete |
| **Total** | — | **34** | **All Complete** |
