# Batch 2 Plan — Remaining HR Features

## Overview

Batch 1 (completed) covers: Employee Management, Attendance System, Leave Management, and Admin Configuration tables.

Batch 2 covers the remaining 4 HR features. **All database models are already created** (stubs in `models.py`), so Batch 2 only needs routes, forms, services, and templates.

---

## Features to Implement

### 1. Performance Management

**Models (already exist):** `PerformanceReview`

**What to build:**
- Create/submit performance reviews (Manager → Employee)
- Review period selection (Q1-2026, Annual-2025, etc.)
- Rating scale (1-5 stars)
- Strengths, improvements, comments text fields
- Status workflow: Draft → Submitted → Acknowledged
- Employee can view their reviews (read-only)
- HR summary: all reviews filterable by period/department

**Routes needed:**
- `GET /hr/performance` — Review list with filters
- `GET/POST /hr/performance/add` — Create review
- `GET /hr/performance/<id>` — View review detail
- `GET/POST /hr/performance/<id>/edit` — Edit draft review

**Templates needed:**
- `hr/performance.html` — Reviews list
- `hr/performance_form.html` — Create/edit
- `hr/performance_detail.html` — View review

---

### 2. Recruitment Module

**Models (already exist):** `JobPosting`, `Candidate`, `Interview`

**What to build:**
- Create job postings linked to Admin departments + designations
- Add candidates with contact info and resume notes
- Pipeline tracking: Applied → Screening → Interview → Offer → Hired/Rejected
- Schedule interviews with interviewer assignment
- Interview feedback and rating
- Pipeline statistics on recruitment dashboard

**Routes needed:**
- `GET /hr/recruitment` — Jobs list
- `GET/POST /hr/recruitment/jobs/add` — Create job posting
- `GET /hr/recruitment/jobs/<id>` — Job detail with candidates
- `GET/POST /hr/recruitment/candidates/add` — Add candidate
- `GET/POST /hr/recruitment/candidates/<id>/edit` — Update candidate status
- `GET/POST /hr/recruitment/interviews/add` — Schedule interview
- `POST /hr/recruitment/interviews/<id>/feedback` — Submit feedback

**Templates needed:**
- `hr/recruitment.html` — Jobs overview
- `hr/job_form.html` — Create/edit job posting
- `hr/job_detail.html` — Job + candidates pipeline
- `hr/candidate_form.html` — Add/edit candidate
- `hr/interview_form.html` — Schedule/feedback

---

### 3. Payroll Input (HR → Finance bridge)

**Models (already exist):** `PayrollInput`

**What to build:**
- Generate monthly payroll input per employee
- Auto-pull from attendance summary (present days, absent days, late count)
- Auto-pull leave days taken that month
- HR manually adds: bonus, overtime hours, deduction notes
- Status workflow: Draft → Submitted (to Finance)
- Finance team can view submitted payroll inputs (read-only from their module)
- **Does NOT calculate salary** — that's Finance's job

**Routes needed:**
- `GET /hr/payroll` — Monthly payroll input list
- `GET/POST /hr/payroll/generate` — Generate inputs for a month
- `GET/POST /hr/payroll/<id>/edit` — Edit draft input
- `POST /hr/payroll/submit` — Bulk submit to Finance

**Templates needed:**
- `hr/payroll_input.html` — Monthly list
- `hr/payroll_form.html` — Edit payroll input

**Integration:**
- Services function `generate_payroll_inputs(year, month)` — auto-creates PayrollInput rows from attendance and leave data

---

### 4. Document Management

**Models (already exist):** `EmployeeDocument`

**What to build:**
- Upload documents per employee (ID proof, offer letter, resume, certificates)
- Document categorization (dropdown of types)
- View/download documents
- Delete documents
- 5MB max file size (already in config)

**Routes needed:**
- `GET /hr/documents` — All documents or per-employee
- `GET/POST /hr/documents/upload` — Upload form
- `GET /hr/documents/<id>/download` — Download file
- `POST /hr/documents/<id>/delete` — Delete document

**Templates needed:**
- `hr/documents.html` — Document list with filters
- `hr/document_upload.html` — Upload form

**Config needed:**
- Add `UPLOAD_FOLDER` to config.py
- Create `static/uploads/documents/` directory
- Add file validation (allowed extensions)

---

## Estimated Effort

| Feature | Routes | Templates | Complexity |
|---|---|---|---|
| Performance | 4 | 3 | Medium |
| Recruitment | 7 | 5 | High |
| Payroll Input | 4 | 2 | Medium |
| Documents | 4 | 2 | Low |
| **Total** | **19** | **12** | — |

---

## Dependencies

- All models already exist in `models.py` ✅
- Admin config (departments, designations) already available ✅
- Services layer pattern already established ✅
- Seed data will need additions for sample performance reviews, job postings, candidates

---

## Execution Order

Recommended implementation order:
1. **Payroll Input** — Simple, builds on existing attendance/leave services
2. **Documents** — Simple file upload CRUD
3. **Performance** — Medium complexity, standalone
4. **Recruitment** — Most complex, pipeline tracking with multiple entities
