# Project: Brandwise — Hackathon Round 3 (Final) Platform Hardening & Delivery

## Architecture
Brandwise is an AI-powered pre-publication brand-governance and advertising-compliance platform designed for regulated consumer goods, cosmetics, and healthcare brands. Operating as an automated pre-flight review layer between initial content drafting and public dissemination, Brandwise ensures that marketing communications conform strictly to statutory regulations (ASCI Code 2025–26, Drugs and Magic Remedies Act 1954, CDSCO Cosmetics Rules 2020, AYUSH Advertising Guidelines, and India DPDP Act 2025) and approved internal brand standards.

The Hackathon Round 3 architecture executes Tasks A through E in strict sequential order:
1. **Task A (Milestone 1)**: Codebase Audit & Security Assessment Report (`AUDIT_REPORT.md`).
2. **Task C (Milestone 2)**: Core Engine Hardening, Bug Fixes, Sanitization, Cold Start & Claims Honesty.
3. **Task B (Milestone 3)**: Local Execution & Comprehensive Testing Suite (`TESTING.md`, repeatable test runners).
4. **Task D (Milestone 4)**: Documentation, Packaging & Sample Assets (`README.md`, `samples/`, `ROADMAP.md`, `FINAL_SUBMISSION_OUTLINE.md`).
5. **Task E (Milestone 5)**: Hackathon Evaluation Report, Scoring (Before/After 100-pt rubric), Limitations & Git Operations.

### Core Architectural Components
1. **Unified Production Server (`server.py` & `codex/server.py`)**:
   - Standalone Python server built on `http.server.SimpleHTTPRequestHandler`.
   - Dynamic port binding (`PORT` environment variable fallback, `0.0.0.0` binding).
   - Serves frontend SPA and handles 11 core REST endpoints for content submission, governance review, clinical PDF ingestion, adjudication, Hinglish evaluation, and visual inspection.
   - 100% SHA-256 byte-for-byte parity maintained between `server.py` and `codex/server.py`.
2. **Deterministic Governance & Compliance Engine (`codex/backend/app/core/review_engine.py`)**:
   - Pure Python deterministic rules executing 100% offline with zero cloud runtime dependencies.
   - Multilingual Hinglish/Hindi engine supporting both Latin Hinglish and native Devanagari script (`\u0900-\u097F`).
   - ASCI influencer disclosure enforcement with support for `#vigyapan`, `#prayasit`, `#sahyog`, `#विज्ञापन`, `#प्रायोजित`.
   - Visual inspection: logo aspect ratio drift (>2%), Euclidean RGB color palette drift (15.0–65.0), and WCAG 2.2 contrast ratio (<4.5:1).
   - Interactive Counter-Evidence Adjudication Gateway enforcing policy relevance across 6 canonical evidence categories, generating SHA-256 document hashes, and restoring +15 compliance score points.
3. **Clinical Evidence PDF Ingestion Engine (`codex/backend/app/core/clinical_extractor.py`)**:
   - Multi-page layout-aware PDF parser using pure Python `pypdf`.
   - Extracts study metadata, structured tables, and 8 standardized dermatological efficacy endpoints.
   - Automated mathematical calculation of statistical exaggeration deltas and timeline compression against registered clinical protocols.
   - Generates 1-indexed canonical citations (`Clinical Study <ID>, Page <P>, Table <T>`).
4. **Frontend Tri-Mirror Single-Page Application (`index.html`, `codex/frontend/index.html`, `docs/index.html`)**:
   - React 18 SPA with 5 dedicated workspaces: Text Review, Brand Upload, Governance Submissions, Visual Asset Inspector, and Hinglish Compliance.
   - Interactive evidence cards, 1-click suggested fix replacements, counter-evidence adjudication modal, and dynamic score gauges.
   - Render cold-start waking indicator pinging `/api/health`.
   - Dual execution: live backend connectivity + offline GitHub Pages client fallback simulation.
   - 100% byte-for-byte tri-mirror parity maintained across all three mirror locations.
5. **Public Cryptographic Verification Portal (`verify.html`, `codex/frontend/verify.html`, `docs/verify.html`)**:
   - Standalone certificate verification portal displaying immutable SHA-256 audit proof hashes and authorized governance signatures.
   - 100% byte-for-byte tri-mirror parity maintained across all three mirror locations.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | Comprehensive Codebase Audit | Catalog real, mocked, and half-finished status across all 3 promised features | M1 | ORIGINAL_REQUEST Task A |
| F02 | Security Vulnerability Audit | Catalog path traversal, secrets/PII, upload limits, XSS, and unhandled crashes | M1 | ORIGINAL_REQUEST Task A |
| F03 | Render Ephemeral Disk Analysis | Analyze JSON storage model and specify smallest safe atomic persistence fix | M1 | ORIGINAL_REQUEST Task A |
| F04 | Path Traversal Remediation | Fix translate_path vulnerability in server.py (prevent /../ reading) | M2 | ORIGINAL_REQUEST Task C |
| F05 | Devanagari & Hinglish Expansion | Add native Devanagari script rules, spelling variants (asr/असर), fix #विज्ञापन false positive | M2 | ORIGINAL_REQUEST Task C |
| F06 | Adjudication Policy Relevance | Enforce evidence-type to allegation-category policy relevance matching | M2 | ORIGINAL_REQUEST Task C |
| F07 | Upload Safety & Input Validation | Add file size (25MB) and type validation in server.py and frontend | M2 | ORIGINAL_REQUEST Task C |
| F08 | Ephemeral Disk Safe Persistence | Implement atomic file writes (write-tmp-rename) and initial JSON seeding | M2 | ORIGINAL_REQUEST Task C |
| F09 | Repository Sanitization | Remove __pycache__, configure .gitignore, sanitize JSON user data, flag secrets | M2 | ORIGINAL_REQUEST Task C |
| F10 | Render Cold-Start UI Indicator | Add waking-up / loading status banner in index.html during backend spin-up | M2 | ORIGINAL_REQUEST Task C |
| F11 | Mirror Parity Maintenance | Ensure 100% SHA-256 byte-for-byte parity across server and HTML mirrors | M2 | ORIGINAL_REQUEST Task C |
| F12 | Local Execution Verification | Verify dependencies install cleanly and server runs locally on PORT | M3 | ORIGINAL_REQUEST Task B |
| F13 | Main User Journey E2E Testing | Verify end-to-end flow from review to adjudication and certificate generation | M3 | ORIGINAL_REQUEST Task B |
| F14 | Adversarial Failure Cases Testing | Test empty/huge input, corrupted/scanned/password-protected PDF, duplicate submit, empty states | M3 | ORIGINAL_REQUEST Task B |
| F15 | Hinglish Compliance Matrix Testing | Test 5 violating lines, 5 harmless lines, spelling variants, and mixed scripts | M3 | ORIGINAL_REQUEST Task B |
| F16 | Repeatable Test Suite & TESTING.md | Automate test execution into test runner scripts and create TESTING.md table | M3 | ORIGINAL_REQUEST Task B |
| F17 | Comprehensive Stranger README.md | Complete guide: overview, stack, install, run, 5-step journey, known limits | M4 | ORIGINAL_REQUEST Task D |
| F18 | Samples Directory Assets | Populate samples/ with study PDF, junk file, ad copies, and Hinglish test lines | M4 | ORIGINAL_REQUEST Task D |
| F19 | Strategic Product Roadmap | Create ROADMAP.md with near-term, mid-term, and long-term milestones | M4 | ORIGINAL_REQUEST Task D |
| F20 | Final Submission PDF Outline | Create structured outline for final hackathon submission document | M4 | ORIGINAL_REQUEST Task D |
| F21 | Hackathon Rubric Scoring | Score out of 100 before and after fixes with one-line justifications per category | M5 | ORIGINAL_REQUEST Task E |
| F22 | Clean Local Git Commits | Stage and commit changes with clear, descriptive commit messages locally | M5 | ORIGINAL_REQUEST Task E |
| F23 | Deployment & Push Guide | Provide step-by-step instructions for remote git push and Render cloud deploy | M5 | ORIGINAL_REQUEST Task E |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | `task_a_audit` | Task A: Complete Codebase Audit & Security Assessment (`AUDIT_REPORT.md`) | none | **DONE** |
| M2 | `task_c_fixes` | Task C: Core Engine Hardening, Bug Fixes, Sanitization, Cold Start & Claims Honesty | M1 | PLANNED |
| M3 | `task_b_testing` | Task B: Local Execution & Comprehensive Testing Suite (`TESTING.md`, runners) | M2 | PLANNED |
| M4 | `task_d_packaging` | Task D: Documentation, Packaging, Samples & PDF Outline (`README.md`, `samples/`, `ROADMAP.md`) | M3 | PLANNED |
| M5 | `task_e_scoring` | Task E: Hackathon Evaluation, Scoring, Declared Limits & Git Commits | M4 | PLANNED |

---

## Interface Contracts

### 1. Adjudication Gateway (`review_engine.py`)
```python
def adjudicate_counter_evidence(
    self,
    allegation_id: str,
    allegation_category: str,
    counter_evidence: dict[str, Any]
) -> dict[str, Any]:
    """
    Evaluates submitted counter-evidence with policy relevance checking.
    Relevance Matrix:
      - visual / logo_distortion / palette_drift / contrast_failure -> legal_waiver_signoff
      - clinical_claim / unverified_clinical_metric -> clinical_trial_certificate, lab_assay_report, cdsco_stage4_clearance
      - ayush_claim / traditional_medicine -> ayush_clinical_registry
      - disclosure / commercial_disclosure -> influencer_contract_exemption
    Input:
      allegation_id: str
      allegation_category: str
      counter_evidence: {
          "evidence_type": str, # one of 6 canonical types
          "reference_id": str,  # non-empty
          "justification": str, # min 10 chars
          "document_hash": str | None
      }
    Returns on Success:
      {
          "success": True,
          "adjudication": "ALLEGATION_REVERTED_AND_DISMISSED",
          "allegation_id": str,
          "allegation_category": str,
          "reversal_timestamp": str,
          "document_hash": str,
          "evidence_reference": str,
          "evidence_type": str,
          "restored_score_delta": 15,
          "audit_note": str,
          "status": "dismissed_with_evidence"
      }
    Returns on Failure:
      {
          "success": False,
          "adjudication": "REJECTED_INSUFFICIENT_EVIDENCE",
          "message": str
      }
    """
```

### 2. Clinical Trial Extractor (`clinical_extractor.py`)
```python
def extract_from_pdf(file_path_or_bytes: Union[str, bytes, BinaryIO, Path]) -> dict[str, Any]:
    """
    Parses multi-page clinical trial PDF and returns structured dossier:
    {
        "study_id": str,
        "title": str,
        "sponsor": str,
        "total_pages": int,
        "cohort_size": int,
        "methodology": str,
        "p_value": str,
        "duration_days": int,
        "endpoints": dict[str, dict],
        "tables": list[dict],
        "source_citation": str,
        "status": "EXTRACTED_VALID" | "EXTRACTED_NO_TABLES" | "ERROR_ENCRYPTED"
    }
    Raises ValueError on empty or corrupted PDF input.
    """
```

### 3. Server Endpoints (`server.py`)
- `GET /api/health` -> `{"status": "healthy", "timestamp": "...", "version": "3.0"}`
- `POST /api/submissions` -> `{"status": "success", "submission": {...}}`
- `POST /api/submissions/approve` -> `{"status": "success", "certificate_id": "BW-CERT-XXXXX-2026", ...}`
- `POST /api/submissions/reject` -> `{"status": "success", "submission_id": "SUB-XXXX", ...}`
- `POST /api/clinical/upload` -> `{"status": "success", "study": {...}}`
- `POST /api/clinical/verify-copy` -> `{"status": "success", "findings": [...], "score": int}`
- `POST /api/hinglish/check` -> `{"status": "success", "score": int, "violations": [...], "compliant_rewrite": str}`
- `POST /api/visual/inspect` -> `{"status": "success", "result": {...}}`
- `POST /api/adjudication/submit` -> `{"status": "success", "result": {...}}`

---

## Code Layout
- `server.py` ≡ `codex/server.py` (Unified HTTP REST backend server; MUST maintain 100% SHA-256 byte parity)
- `codex/backend/app/core/review_engine.py` (Deterministic rule, Hinglish, visual, and adjudication engine)
- `codex/backend/app/core/clinical_extractor.py` (PDF clinical trial ingestion & discrepancy analysis)
- `codex/backend/app/core/visual_checker.py` (WCAG contrast & alt-text helper)
- `codex/backend/app/core/llm_service.py` (Anthropic Claude adapter with heuristic mock fallback)
- `index.html` ≡ `codex/frontend/index.html` ≡ `docs/index.html` (React 18 SPA; MUST maintain 100% byte parity)
- `verify.html` ≡ `codex/frontend/verify.html` ≡ `docs/verify.html` (Public cryptographic verification portal; MUST maintain 100% byte parity)
- `brand_submissions_db.json` (Seed brand submissions database)
- `supabase_users_db.json` (Seed user database)
- `codex/tests/` (Automated Python and JavaScript test suites)
- `samples/` (Verification sample assets: clinical PDF, waiver, lab report, junk file, ad copies, test lines)
- `AUDIT_REPORT.md` (Task A codebase audit & security assessment report)
- `TESTING.md` (Task B test matrix and execution results)
- `README.md` (Task D stranger setup and 5-step journey guide)
- `ROADMAP.md` (Task D product roadmap)
- `render.yaml`, `Dockerfile`, `Procfile`, `requirements.txt` (Packaging and deployment configurations)
