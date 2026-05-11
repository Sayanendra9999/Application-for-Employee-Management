# Recruitment Workflow — Task Tracker

## Phase 1: Models
- [x] Add `HiringRequest` model
- [x] Add `Offer` model
- [x] Enhance `Candidate` model (add source, avg_interview_rating, days_in_pipeline)
- [x] Enhance `JobPosting` model (add salary range, employment_type, location, hired_count)

## Phase 2: Forms
- [x] Add `HiringRequestForm`
- [x] Add `OfferForm`
- [x] Add `HiringRequestRejectForm`
- [x] Update `JobPostingForm` (salary range, employment_type, location)
- [x] Update `CandidateForm` (source, resume upload)

## Phase 3: Services
- [x] Add `get_pipeline_stats()` service
- [x] Add `get_recruitment_dashboard_stats()` service
- [x] Add `approve_hiring_request()` service
- [x] Add `convert_hiring_request_to_job()` service
- [x] Add `reject_hiring_request()` service
- [x] Add `extend_offer()` service
- [x] Add `respond_to_offer()` service
- [x] Add `withdraw_offer()` service
- [x] Add `save_resume_file()` service

## Phase 4: Routes
- [x] Add hiring request routes (list, add, approve, reject, convert)
- [x] Add pipeline route (Kanban view)
- [x] Add offer routes (extend, respond, withdraw)
- [x] Add edit job route
- [x] Add candidate detail route
- [x] Add resume download route
- [x] Update dashboard with recruitment stats
- [x] Update existing recruitment routes (services-based pipeline)

## Phase 5: Templates
- [x] Update `recruitment.html` with pipeline stats & hiring request badge
- [x] Create `pipeline.html` (Kanban view)
- [x] Create `hiring_requests.html` with approve/reject/convert actions
- [x] Create `hiring_request_form.html`
- [x] Create `offer_form.html`
- [x] Create `candidate_detail.html` (full profile + interview history + offer)
- [x] Update `job_detail.html` (pipeline, salary, offer actions, edit button)
- [x] Update `candidate_form.html` (source, resume upload)
- [x] Update `job_form.html` (salary range, employment type, location)
- [x] Update `dashboard.html` with recruitment badge

## Phase 6: Schema & Verification
- [x] Update `schema.sql` (hiring_requests, offers tables)
- [x] Test app startup — OK
- [x] Test DB table creation — OK
- [x] Verify all 18 recruitment routes registered — OK
