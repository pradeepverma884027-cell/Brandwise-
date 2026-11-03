# Brandwise Comprehensive Codebase Audit & Security Assessment Report
**Document**: AUDIT_REPORT.md  
**Milestone**: Hackathon Round 3 (Final Submission) — Task A  
**Author**: Teamwork Worker (Audit & Security Specialist)  
**Date**: November 2, 2026  
**Target Repository**: `https://github.com/pradeepverma884027-cell/Brandwise-`  
**Live Application**: `https://brandwise-6wl6.onrender.com` / `https://pradeepverma884027-cell.github.io/Brandwise-/`  
**Workspace Root**: `c:\Users\pradeep\Downloads\codex2`  

---

## Executive Summary

Brandwise is an AI-powered pre-publication brand-governance and advertising-compliance platform designed for regulated consumer goods, cosmetics, and healthcare brands. The platform serves as an automated pre-flight review layer between initial content drafting and public dissemination, verifying marketing copy against statutory regulations (ASCI Code 2025–26, Drugs and Magic Remedies Act 1954, CDSCO Cosmetics Rules 2020, AYUSH Advertising Guidelines, and India DPDP Act 2025) and approved internal brand standards.

This comprehensive audit represents the completed deliverable for **Milestone 1 (Task A)** of Hackathon Round 3. An exhaustive, line-by-line inspection of every file in the repository was executed to:
1. Catalog every file, its architectural role, and its current status.
2. Conduct an unsparing assessment of the **three promised Round 2 improvements** (Clinical Evidence PDF Ingestion, Hinglish/Hindi Compliance Engine, and Counter-Evidence Adjudication), documenting exactly what is real, what is mocked or hardcoded, and what is half-finished.
3. Catalog all runtime bugs, unhandled crashes, and missing error-handling paths.
4. Uncover and analyze critical security vulnerabilities, including an active path-traversal flaw in `server.py`, committed secrets and personal data (PII) in JSON files and student exam debris, unsafe unbounded file uploads, and frontend XSS surfaces.
5. Provide a rigorous architectural analysis of Render's free-tier ephemeral disk storage and define the smallest safe fix to prevent database corruption and data loss.

### Architectural Overview & Divergence
A primary discovery of this audit is an architectural divergence between two distinct backend implementations present in the repository:
1. **The Active Production Backend (`server.py` and `codex/server.py`)**:
   - A standalone Python server built directly on `http.server.SimpleHTTPRequestHandler`.
   - Executed by Render in production (`Procfile: web: python server.py $PORT`, `render.yaml: startCommand: python server.py 10000`, `Dockerfile: CMD ["python", "server.py", "10000"]`).
   - Maintains exact byte-for-byte SHA-256 parity (`24E2F9149C780EB9A7D9760E48BDF1D9373F722788C83D7430B5BEEAE91DF1C4`).
   - Serves static assets (`index.html`, `verify.html`) and provides 11 REST API endpoints for submissions, approvals, visual inspection, clinical PDF extraction, adjudication, and Hinglish checks.
   - Operates 100% offline with zero cloud runtime dependencies using local deterministic heuristics, with optional async sync to Supabase and optional Claude LLM evaluation.
2. **The Dormant FastAPI Backend (`codex/backend/app/`)**:
   - An asynchronous FastAPI framework application containing SQLAlchemy async models, Pydantic schemas, and Alembic migrations.
   - **Crucial finding**: This backend is **not** deployed or invoked in production. Its dependencies (`fastapi`, `sqlalchemy`, `uvicorn`, `pydantic-settings`) are omitted from the root `requirements.txt`. Several endpoints (`/insights/guideline-gaps`, `/insights/review-stats`) return static mock JSON, and authentication includes an unauthenticated superuser developer bypass.
   - However, its core deterministic rule engine files (`codex/backend/app/core/review_engine.py` and `codex/backend/app/core/clinical_extractor.py`) serve as the shared source of truth imported directly by `server.py`.

---

## 1. Exhaustive File-by-File Codebase Inventory

Every file in the repository has been inspected, categorized, and evaluated for implementation integrity:

| File Path | Size (Bytes) | Lines | Architectural Role | Status | Description & Audit Observations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `server.py` (Root) | 79,884 | 1,719 | Active Production Server | **REAL (Flawed)** | Standalone HTTP REST server; serves SPA, handles 11 endpoints. Contains critical path traversal in `translate_path` and master OTP bypasses. |
| `codex/server.py` | 79,884 | 1,719 | Active Production Server Mirror | **REAL (Flawed)** | 100% SHA-256 byte-for-byte identical mirror of `server.py`. |
| `codex/backend/app/core/review_engine.py` | 48,942 | 1,031 | Core Deterministic Review Engine | **REAL (Partial)** | Pure Python deterministic compliance engine. Real Latin Hinglish, visual geometry, and adjudication logic. Missing Devanagari Unicode regexes. |
| `codex/backend/app/core/clinical_extractor.py` | 38,660 | 840 | Clinical PDF Extraction Engine | **REAL (Partial)** | Pure Python `pypdf` layout parser; extracts tables, endpoints, and calculates statistical discrepancies. Lacks OCR for image-only scans. |
| `codex/backend/app/core/visual_checker.py` | 2,475 | 67 | Visual Helper Engine | **REAL** | Lightweight helper calculating WCAG 2.2 contrast ratio and validating missing image alt-text. |
| `codex/backend/app/core/llm_service.py` | 7,874 | 179 | External LLM Adapter | **REAL / MOCKED** | Optional Anthropic Claude adapter. Real client if `ANTHROPIC_API_KEY` present; otherwise invokes `_mock_semantic_evaluation` heuristic. |
| `codex/backend/app/core/security.py` | 1,885 | 55 | FastAPI Auth Security Helper | **REAL (Dormant)** | Passlib bcrypt hashing and python-jose JWT encoding/decoding. Part of dormant FastAPI app. |
| `codex/backend/app/core/config.py` | 2,233 | 68 | FastAPI Settings Model | **REAL (Dormant)** | Pydantic BaseSettings loading Postgres, Redis, MinIO, and JWT secrets. Hardcoded default secret key. |
| `codex/backend/app/core/dependencies.py` | 4,057 | 116 | FastAPI RBAC Dependencies | **MOCKED (Dormant)** | Auth dependency for FastAPI. Contains developer bypass (lines 24–36) returning mock superuser if credentials missing. |
| `codex/backend/app/core/database.py` | 1,180 | 41 | FastAPI Async DB Session | **REAL (Dormant)** | Async SQLAlchemy engine creation and async session generator. Part of dormant FastAPI app. |
| `codex/backend/app/core/middleware.py` | 1,605 | 52 | FastAPI Logging Middleware | **REAL (Dormant)** | Request timing and correlation ID middleware for Starlette/FastAPI. |
| `codex/backend/app/main.py` | 3,176 | 98 | FastAPI Application Root | **DORMANT** | FastAPI app definition with CORS and routers. Not invoked in production. |
| `codex/backend/app/api/routers.py` | 11,183 | 323 | FastAPI Route Handlers | **PARTIAL (Dormant)** | Routes for content submission and review. `/insights/guideline-gaps` and `/insights/review-stats` return hardcoded static JSON. |
| `codex/backend/app/models/*.py` (16 files) | ~32,000 | ~950 | SQLAlchemy ORM Models | **REAL (Dormant)** | ORM definitions for User, Tenant, Role, ContentSubmission, ReviewFinding, FactRecord, GuidelineDocument, etc. |
| `codex/backend/app/schemas/*.py` (16 files) | ~24,000 | ~780 | Pydantic Schemas | **REAL (Dormant)** | Pydantic request/response models for all entities. |
| `codex/backend/migrations/` | ~15,000 | ~350 | Alembic Database Migrations | **REAL (Dormant)** | Database migration scripts for PostgreSQL schema creation. |
| `index.html` (Root) | 417,020 | 7,503 | Single-Page Application (SPA) | **REAL (Flawed)** | React 18 SPA with 5 tabs (Review, Brand Upload, Submissions, Visual, Hinglish). 100% tri-mirror parity. Lacks cold-start indicator. |
| `codex/frontend/index.html` | 417,020 | 7,503 | SPA Mirror | **REAL (Flawed)** | 100% SHA-256 byte-for-byte identical to root `index.html`. |
| `docs/index.html` | 417,020 | 7,503 | GitHub Pages Mirror | **REAL (Flawed)** | 100% SHA-256 byte-for-byte identical to root `index.html`. Enables offline client fallback. |
| `verify.html` (Root) | 16,808 | 325 | Public Verification Portal | **REAL (Partial)** | Standalone certificate verification portal. Displays cryptographic audit hash. Gaps: no clinical citations or adjudication history. |
| `codex/frontend/verify.html` | 16,808 | 325 | Public Portal Mirror | **REAL (Partial)** | 100% SHA-256 byte-for-byte identical to root `verify.html`. |
| `docs/verify.html` | 16,808 | 325 | GitHub Pages Portal Mirror | **REAL (Partial)** | 100% SHA-256 byte-for-byte identical to root `verify.html`. |
| `brand_submissions_db.json` (Root) | 2,562 | 57 | Production Submissions Store | **REAL** | Seed database containing 3 initial brand submissions (SUB-9021, SUB-9022, SUB-9023). |
| `codex/brand_submissions_db.json` | 154,000 | 4,089 | Submissions Mirror Store | **BLOATED** | Bloated with repeated test run artifacts; needs reset to clean 3-submission seed data. |
| `supabase_users_db.json` (Root) | 713 | 29 | User Authentication Store | **REAL** | Contains 2 default users (`admin@dermacare.com`, `chief@dermacare.com`) with empty password hashes. |
| `codex/supabase_users_db.json` | 1,303 | 41 | User Store Mirror | **VULNERABLE** | Contains 3 users with active salted SHA-256 password hashes (`admin`, `chief`, `creator`) committed to git. |
| `codex/brandwise.db` | 0 | 0 | SQLite Database Placeholder | **INACTIVE** | 0-byte SQLite database file from local experiments. |
| `samples/Study_CS-2026-88.pdf` | 14,535 | N/A | Clinical Study PDF Fixture | **REAL** | 8-page clinical study PDF fixture with Table 2.1 (94.2% hydration, 14 days, N=120, p<0.001). |
| `samples/LAB-AYUSH-904.pdf` | 6,086 | N/A | AYUSH Lab Certificate Fixture | **REAL** | Independent AYUSH lab assay certificate fixture (88.5% soothing, 7 days, p<0.01). |
| `samples/Brand_Design_Waiver_BW-2026-09.pdf` | 1,913 | N/A | Legal Design Waiver Fixture | **REAL** | Signed legal waiver signoff fixture for visual aspect ratio drift. |
| `fixtures/*.pdf` | 22,534 | N/A | Test Fixtures Mirror | **REAL** | Identical copies of sample PDFs for test suite execution. |
| `codex/tests/test_*.py` (20 files) | ~390,000 | 8,245 | Automated Python Test Suite | **REAL** | 345 unit and integration tests passing 100% in 3.7 seconds. Comprehensive coverage across core engines. |
| `codex/tests/test_*.js` (8 files) | ~180,000 | 4,120 | Node.js Test Suite | **REAL** | 8 JavaScript test suites executing client-side Babel JSX compilation, jsPDF stability, and localStorage F5 resilience. |
| `render.yaml` | 315 | 16 | Render Cloud Blueprint | **REAL** | Web service declaration: Python 3.12, free plan, `python server.py 10000`, `/api/health`. |
| `Procfile` | 29 | 1 | Process Configuration | **REAL** | Declares `web: python server.py $PORT` for cloud port binding. |
| `Dockerfile` | 699 | 24 | Container Specification | **REAL** | Multi-stage Python 3.12-slim Dockerfile with health checks. |
| `requirements.txt` (Root) | 149 | 4 | Production Dependencies | **REAL** | Minimal dependencies: `pypdf>=5.0.0` and `requests>=2.31.0`. |
| `codex/backend/requirements.txt` | 1,420 | 42 | Dormant FastAPI Dependencies | **DORMANT** | Exhaustive dependencies for FastAPI, SQLAlchemy, Alembic, Celery, etc. |
| `README.md` (Root) | 14,645 | 320 | Platform Documentation | **OUTDATED** | References Round 2 improvements as "planned", lacks 5-step journey and declared limitations. |
| `PROJECT.md` | 12,886 | 197 | Project Scope Baseline | **OUTDATED** | Described Improvement 2 from previous milestone; requires synchronization with Round 3 scope. |
| `.gitignore` | 112 | 13 | Git Ignore Configuration | **DEFECTIVE** | Omits `__pycache__/`, `*.pyc`, `*.db`. Bytecode `.pyc` files are actively tracked in git index. |
| `claude_chat.json` (Root) | 33,129 | 1 | Student Chat Export Debris | **EXPOSED PII** | Full conversation export containing personal name "Pradeep", user UUID, and university exam questions. |
| `aktu_bcs501_2024_25.pdf` | 189,002 | N/A | Student Exam Paper Debris | **DEBRIS** | AKTU university semester 5 exam paper on DBMS (BCS501). |
| `ryzen_*.html`, `cleaned_*.txt`, `scratch_*.py` | ~850,000 | ~15,000 | Student Exam Processing Scripts | **DEBRIS** | 22 personal scraping and extraction scripts/files completely unrelated to Brandwise. |

---

## 2. Assessment of the Three Promised Round 2 Improvements

The platform promised three core technological improvements in Round 2. Here is the unsparing breakdown of what is genuinely implemented, what is mocked or hardcoded, and what remains half-finished or defective.

```
+---------------------------------------------------------------------------------------+
|                                ROUND 2/3 IMPROVEMENTS STATUS                           |
+------------------------------------+------------------+-------------------------------+
| Feature                            | Status           | Integrity Verdict             |
+------------------------------------+------------------+-------------------------------+
| 1. Clinical Evidence PDF Ingestion | 85% Real         | Functional local pypdf parser |
|                                    | 15% Gap          | Missing OCR; verify.html gap  |
+------------------------------------+------------------+-------------------------------+
| 2. Hinglish / Hindi Engine         | 70% Real (Latin) | High-quality Latin Hinglish   |
|                                    | 30% Defective    | ZERO Devanagari; #ad bug      |
+------------------------------------+------------------+-------------------------------+
| 3. Counter-Evidence Adjudication   | 80% Real         | Real SHA-256 & +15 delta      |
|                                    | 20% Gap          | Policy-agnostic; no file POST |
+------------------------------------+------------------+-------------------------------+
```

### 2.1 Improvement 1: Clinical Evidence PDF Ingestion & Claim Substantiation

#### What is REAL
1. **Multi-Page Layout-Aware PDF Parser**:
   `ClinicalTrialPDFExtractor.extract_from_pdf` (`codex/backend/app/core/clinical_extractor.py`, lines 42–146) genuinely reads multi-page binary PDF files via `pypdf.PdfReader`. It extracts page text using layout mode (`extract_text(extraction_mode="layout")`) to preserve spatial column alignment.
2. **Clinical Study Metadata Extraction**:
   Regex heuristics extract Study ID (`CS-2026-88`, `LAB-AYUSH-904`), Title, Sponsor, Clinical Methodology (e.g. "double-blind, randomized, placebo-controlled"), Cohort Size ($N=120$), Protocol Duration ($14$ days), and Statistical Significance ($p < 0.001$).
3. **Structured Table & Quantitative Endpoint Extraction**:
   Scans table declarations (`Table 1`, `Table 2.1`, `Table 4.1`) and maps extracted numbers to 8 standardized dermatological endpoints:
   - `hydration_increase_percent` (Stratum Corneum Hydration)
   - `acne_lesion_reduction_percent` (Inflammatory Acne Lesion count)
   - `sebum_reduction_percent` (Casual Sebum Excretion)
   - `tewl_reduction_percent` (Transepidermal Water Loss)
   - `soothing_efficacy_percent` (Erythema / Skin Soothing)
   - `skin_irritation_index` (Patch test dermal irritation)
   - `wrinkle_reduction_percent` (Fine line depth reduction)
   - `elasticity_improvement_percent` (Cutometer skin firmness)
4. **Automated Mathematical Discrepancy Engine**:
   `evaluate_clinical_discrepancies` (lines 504–825) performs genuine calculations:
   - **Statistical Exaggeration**: Compares claimed percentage against registered endpoint value. If marketing copy claims $99\%$ hydration when trial verified $94.2\%$, it calculates $+4.8\%$ exaggeration delta and flags high-severity finding `CLINICAL-EVIDENCE-01`.
   - **Timeline Compression**: Flags promises faster than protocol duration (e.g. "results in 7 days" against a 14-day study) with a calculated delta ($-7$ days).
   - **Absolute / Magic Cure Claims**: Flags ungrounded claims asserting "100% cure", "permanent", or unverified conditions (`rosacea`, `eczema`).
   - **Commercial Shielding**: Ignores sales discounts (e.g. "50% off with code GLOW50") so they never trigger clinical exaggeration flags.
5. **REST API Endpoints**:
   `server.py` implements functional endpoints: `POST /api/clinical/upload` (accepts multipart, application/pdf, or base64 JSON), `POST /api/clinical/verify-copy`, `GET /api/clinical/studies`, and `GET /api/clinical/sample-pdf`.

#### What is HARDCODED or MOCKED
1. **Fallback Catalog**: If no PDF has been uploaded or extracted endpoints are empty, the engine falls back to `DEFAULT_CLINICAL_STUDIES` (`CS-2026-88` and `LAB-AYUSH-904`).
2. **Table Header Assumption**: Table extraction relies on finding the text pattern `Table \d+(\.\d+)?`. Tables lacking explicit text headers fall back to prose regex extraction.

#### What is HALF-FINISHED / GAPS
1. **Scanned / Image-Only PDFs**: The engine relies entirely on `pypdf` text extraction. It has no OCR capability (e.g., Tesseract). If a user uploads a scanned image-only PDF with zero text characters, the extractor returns `EXTRACTED_NO_TABLES` with 0 endpoints.
2. **Public Certificate Display (`verify.html`)**: While `server.py` attaches 1-indexed citations (`Clinical Study CS-2026-88, Page 7, Table 2.1`) to submission findings, the public verification portal `verify.html` does **not** dynamically render clinical citations or an evidence table. It only renders static text: `"Regulated clinical claims grounded against approved Fact Register #FR-402"`.
3. **Hardcoded PDF Certificate Citation (`index.html`)**: In `generatePdfCertificate` (`index.html`, line 3650), the certificate PDF generator hardcodes:
   `doc.text("• Verified against Study #CS-2026-88, Page 7, Table 2.1 (N=120, p < 0.01)", 20, 114)`
   rather than dynamically reading the active study citation from `subItem.clinical_citation` or `selectedStudy.source_citation`.

---

### 2.2 Improvement 2: Multilingual & Code-Mixed (Hinglish / Hindi) Compliance Engine

#### What is REAL
1. **Latin-Script Hinglish Superlative Rules**:
   `review_engine.py` (lines 290–372) implements 9 compiled regex rules for Latin Hinglish under the Drugs and Magic Remedies Act 1954 §3 and ASCI Code:
   - `100% asar` / `100% asardaar` (Absolute efficacy)
   - `chamatkari` / `chamatkar` (Magic remedy)
   - `jad se khatam` / `jadd se khatam` (Absolute eradication)
   - `hamesha ke liye` (Permanent cure)
   - `shat pratishat` (100% guarantee)
   - `ek jhatke mein` (Instantaneous cure)
   - `ramban ilaj` (Infallible remedy under AYUSH Guidelines §3.1)
   - `pakka ilaj` (Guaranteed medical cure)
   - `bilkul theek` / `bilkul thik` (Absolute cure under CDSCO Cosmetics Rules)
2. **Colorist & Complexion Modification Rules**:
   `review_engine.py` (lines 374–429) implements 6 rules under the ASCI Skin Lightening & Cosmetic Guidelines 2024:
   - `gora rang` / `gore rang`
   - `rang gora` / `rang ko gora`
   - `fairness guarantee`
   - `ek hafte mein gora`
   - `rang nikhare` / `rangat nikhare`
   - `gorapan`
3. **Commercial Disclosure Enforcement**:
   Detects promotional purchase triggers (`buy now`, `discount`, `khareedo`, `order karein`, `link bio mein`) and flags the absence of required commercial disclosures.
4. **Culturally Resonant Compliant Rewrites**:
   Every rule provides a contextually appropriate vernacular suggested rewrite (e.g., replaces `"100% asar"` with `"visible results ke liye regular use karein"`, replaces `"jad se khatam"` with `"acne ko kam karne mein madad kare"`).
5. **Interactive UI**:
   `index.html` has a dedicated Hinglish tab with an animated radial score gauge, 3 pre-loaded test presets, and 1-click `[✨ Apply Fix]` string replacement in the editor.

#### What is HARDCODED or MOCKED
- Clinical trial references inside Hinglish evaluations default to `CS-2026-88` if no specific study catalog is supplied.

#### What is HALF-FINISHED / CRITICAL DEFECTS
1. **ZERO Devanagari Script Detection**:
   `codex/backend/app/core/review_engine.py` contains **zero Devanagari Unicode characters** (`\u0900-\u097F`).
   - If a creator writes claims in Devanagari Hindi (e.g. `"चमत्कारी"`, `"गोरा रंग"`, `"रामबाण इलाज"`, `"१००% असर"`, `"जड़ से खत्म"`), the engine detects **zero violations** and awards a 100% clean score! The engine is completely blind to native Hindi text.
2. **ASCI Hindi Disclosure False Positive Bug**:
   In `review_engine.py` line 436:
   ```python
   VERNACULAR_DISCLOSURE_PATTERN = re.compile(
       r"(#vigyapan|#prayasit|#sahyog|#ad|#sponsored)\b",
       re.IGNORECASE
   )
   ```
   If an ethical Indian creator writes the official Hindi disclosure hashtag in Devanagari script (`#विज्ञापन` or `#प्रायोजित`), the engine fails to match it and issues a **high-severity false positive violation** (`HINGLISH-DISCLOSURE-04`) demanding they add a disclosure!
3. **Phonetic Spelling Variant Gaps**:
   - `re.compile(r"\b(100%\s*asar(?:daar)?)\b")` matches `asar` and `asardaar`, but fails to match the common phonetic variant `100% asr`.
   - `chamatkar(?:i|ik)?` fails to match colloquial variant `chmatkari`.

---

### 2.3 Improvement 3: Interactive Evidence-Based Adjudication Gateway

#### What is REAL
1. **Canonical Evidence Categories**:
   `review_engine.py` (lines 797–809) validates counter-evidence against 6 canonical regulatory categories:
   - `clinical_trial_certificate` (Independent CRO / CTRI clinical study report)
   - `cdsco_stage4_clearance` (CDSCO government clearance)
   - `legal_waiver_signoff` (Corporate Legal Counsel brand guideline exemption)
   - `lab_assay_report` (NABL / ISO 17025 accredited laboratory assay)
   - `influencer_contract_exemption` (Executed contract with disclosure rider)
   - `ayush_clinical_registry` (AYUSH clearance)
2. **Mandatory Input Validation**:
   Rejects submissions with empty reference IDs or justifications shorter than 10 characters with specific error messages.
3. **Cryptographic SHA-256 Digest**:
   Computes a deterministic SHA-256 hash across `allegation_id:evidence_type:ref_id:justification`.
4. **Score Restoration & Audit Trail**:
   - Returns `"adjudication": "ALLEGATION_REVERTED_AND_DISMISSED"` and `"restored_score_delta": 15`.
   - Appends audit record to `SUPABASE_MOCK_TABLES["audit_logs"]` capturing timestamp, actor `"Compliance Adjudication Engine"`, action `"ALLEGATION_DISMISSED"`, and document hash.
   - Frontend SPA dynamically updates finding card to green dismissed state and restores +15 compliance score points.

#### What is HARDCODED or MOCKED
1. **Policy-Agnostic Adjudication (No Cross-Validation)**:
   The adjudication engine evaluates **syntactic validity only**. It does **not** verify whether the submitted `evidence_type` is legally or technically relevant to the `allegation_category`.
   - *Demonstrated vulnerability*: If an allegation is flagged for `logo_distortion` (aspect ratio drift), submitting an `ayush_clinical_registry` certificate with reference `AYUSH-123` and justification `This is an approved herbal medicine` is accepted and dismisses the visual logo violation!
   - Similarly, uploading a `legal_waiver_signoff` is accepted to dismiss an unverified medical cancer cure claim.
2. **Mock Adjudicator**: All adjudication is executed via synchronous rule heuristics; there is no human review workflow or real third-party registry lookup.

#### What is HALF-FINISHED / GAPS
1. **JSON Metadata Only (No File Upload)**:
   `POST /api/adjudication/submit` only accepts JSON metadata (`evidence_type`, `reference_id`, `justification`, optional `document_hash`). There is no multipart file upload handler to attach a physical PDF waiver or lab certificate to the allegation.
2. **Certificate Portal Omission**:
   Adjudication reversals and dismissed allegations are not rendered on the public verification portal `verify.html`.

---

## 3. Comprehensive Catalog of Bugs, Crashes & Error-Handling Defects

An audit of the runtime and API handlers revealed several bugs that can trigger server crashes or degraded user experiences:

### Bug 1: Unhandled `AttributeError` Crashes on Malformed Types (HTTP 500)
- **Location**: `server.py` lines 790, 866, 885, 1140, 1195, 1340.
- **Mechanism**: POST request handlers extract fields and immediately call `.strip()` without verifying that the value is a string:
  ```python
  content = data.get("content", "").strip()
  submission_id = data.get("submission_id", "").strip()
  ```
  If a client submits an integer, boolean, or nested dictionary/list (e.g. `{"content": 12345}` or `{"submission_id": 9021}`), calling `.strip()` raises `AttributeError: 'int' object has no attribute 'strip'`.
- **Impact**: The exception is caught by the generic `except Exception as e:` block and returns `HTTP 500 Internal Server Error` instead of a clean `HTTP 400 Bad Request`.

### Bug 2: Missing `json.JSONDecodeError` Handling on Ingestion Endpoints (HTTP 500)
- **Location**: `server.py` lines 787, 863, 882, 1137, 1192, 1308.
- **Mechanism**: The endpoints `/api/submissions`, `/api/submissions/approve`, `/api/submissions/reject`, `/api/auth/register`, `/api/auth/login`, and `/api/auth/send-otp` do not specifically catch `json.JSONDecodeError`. Sending invalid JSON payloads triggers an unhandled decode error that returns `HTTP 500`.
- *(Note: In contrast, `/api/visual/inspect`, `/api/adjudication/submit`, and `/api/hinglish/check` properly catch `json.JSONDecodeError` and return HTTP 400).*

### Bug 3: Random ID Collision Risk and Database Bloat
- **Location**: `server.py` line 849.
- **Mechanism**:
  ```python
  sub_id = f"SUB-{random.randint(9024, 9999)}"
  ```
  Generates an ID from a tiny pool of only 975 numbers without checking whether `sub_id` is already assigned in `submissions`. Under repeated submissions, collisions occur. Furthermore, identical duplicate submissions are prepended without deduplication, causing `codex/brand_submissions_db.json` to balloon to over 4,000 lines.

### Bug 4: Concurrency Race Conditions on JSON Database Files
- **Location**: `server.py` lines 180–230 (`load_brand_submissions`, `save_brand_submissions`, `load_supabase_users`, `save_supabase_users`).
- **Mechanism**: While `CLINICAL_STUDIES_CATALOG` uses `threading.RLock()`, file operations on `SUBMISSIONS_DB_FILE` and `USERS_DB_FILE` have no thread locks or file locks. Simultaneous submissions from multiple users will interleave writes and overwrite each other's data.

### Bug 5: Frontend Error-Fallback Masking in `handlePdfUpload`
- **Location**: `index.html` lines 2881–2898.
- **Mechanism**: When `POST /api/clinical/upload` returns `HTTP 400` rejecting an invalid or corrupted PDF, the frontend `catch (netErr)` block intercepts the error and fabricates a fake extracted study from `DEFAULT_CLINICAL_FIXTURES[0]`:
  ```javascript
  const extractedStudy = {
    ...fallbackTemplate,
    study_id: "CS-2026-88",
    title: fallbackTemplate.title + " (Local Extracted)"
  };
  setClinicalStudies(prev => [extractedStudy, ...prev]);
  triggerNotification(`✓ Ingested ${file.name} locally (Offline mode active)`);
  ```
- **Impact**: Server rejection of invalid files is masked; the user is falsely told the upload succeeded and endpoints from Study CS-2026-88 are loaded.

### Bug 6: Frontend Review Tab Textarea Decoupling
- **Location**: `index.html` lines 1783–1792 (`handleRunReview`).
- **Mechanism**: When the user clicks "Run Review" in the main `activeTab === 'review'`, `handleRunReview()` completely ignores what the user typed in the textarea! It triggers a 1100ms timeout and resets findings back to the hardcoded sample findings for the selected channel.

### Bug 7: Missing Empty State in Main Review Tab
- **Location**: `index.html` line 4625.
- **Mechanism**: When `findings.length === 0`, the findings container renders completely empty (blank whitespace with no feedback message or illustration), unlike the Submissions and Hinglish tabs which provide polished empty state cards.

### Bug 8: Unbounded Client-Side PDF Reading
- **Location**: `index.html` lines 2828–2846.
- **Mechanism**: The dropzone handler does not check `file.size` before calling `reader.readAsDataURL(file)`. Uploading a 100MB+ file will lock the browser main thread and exhaust client memory.

---

## 4. Security Vulnerability Assessment

### 4.1 Critical Path Traversal in `server.py` (`translate_path`)

- **Vulnerability**: Path Traversal / Arbitrary File Read
- **Severity**: **CRITICAL (CVSS 8.6)**
- **Location**: `server.py` lines 1664–1668 (`RobustVerificationHandler.translate_path`):
  ```python
  # Default fallback to frontend dir
  rel = clean_path.lstrip("/")
  candidate = os.path.join(FRONTEND_DIR, rel)
  if os.path.exists(candidate):
      return candidate
  ```
- **Exploit Proof of Concept**:
  `clean_path.lstrip("/")` strips leading slashes but fails to sanitize directory traversal sequences (`../`).
  When an attacker requests:
  `GET /../supabase_users_db.json HTTP/1.1`
  1. `clean_path` becomes `../supabase_users_db.json`.
  2. `candidate` resolves to `os.path.join(FRONTEND_DIR, "../supabase_users_db.json")`, which evaluates to `c:\Users\pradeep\Downloads\codex2\supabase_users_db.json`.
  3. `os.path.exists(candidate)` evaluates to `True`.
  4. The server returns the path directly, bypassing Python's `SimpleHTTPRequestHandler.translate_path` traversal protection!
  5. The server streams sensitive user accounts, password hashes, or server source code (`GET /../server.py`) directly to the attacker.
- **Remediation**:
  Resolve candidate paths using `os.path.abspath` and verify that `os.path.commonpath([FRONTEND_DIR, os.path.abspath(candidate)]) == FRONTEND_DIR`.

---

### 4.2 Exposed Secrets, Credentials & Personal Data (PII)

1. **Exposed Student Chat Export (`claude_chat.json`)**:
   - Location: Workspace root (`claude_chat.json`, 33,129 bytes).
   - Findings: Full export of a personal Claude conversation created by `"Pradeep"` (`"full_name": "Pradeep"`, user UUID `9b062f42-716f-45f5-bdd5-1bea34f030b3`). Discusses AKTU university exam questions for DBMS (BCS501).
   - Associated debris files: `aktu_bcs501_2024_25.pdf` (189 KB), `ryzen_*.html`, `cleaned_*.txt`, `extracted_*.txt`, `scratch_*.py`.
   - Violation: India DPDP Act 2025 and repository privacy violation.
2. **Committed Salted Password Hashes (`codex/supabase_users_db.json`)**:
   - Location: `codex/supabase_users_db.json` lines 10, 36.
   - Active SHA-256 password hashes committed to git:
     - `admin@dermacare.com`: `af5fd0d7d9fc7be5a4c1ce965081b68399d997bffed2458ec518d3eaa6594bd5`
     - `creator@dermacare.com`: `50cfaea4b84c09455ab2d9b4a50f3f9d0e2548fa39cda72f5d5d7d0a7cc6eac8`
   - Salt used: Static salt `"brandwise_supabase_salt_2026"` hardcoded in `server.py` line 186.
3. **Hardcoded Master Bypass OTPs**:
   - Location: `server.py` line 1349:
     ```python
     elif otp in ("884192", "123456"):
         is_valid = True
     ```
   - Any client submitting `884192` or `123456` instantly bypasses authentication for any user account.
4. **OTP Reflected in API Response**:
   - Location: `server.py` line 1327 (`POST /api/auth/send-otp`):
     ```python
     "otp": otp, # sent for simulator convenience
     ```
   - The generated OTP is reflected in plaintext in the response JSON, negating the security of two-factor authentication.
5. **Hardcoded Demo Secret Keys**:
   - `server.py` line 153: `SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.brandwise-demo-anon-key"`
   - `codex/backend/app/core/config.py` line 14: `SECRET_KEY = "change-this-secret-key-to-a-random-32-char-string"`

---

### 4.3 Unsafe File Uploads & Denial-of-Service (DoS)

- **Vulnerability**: Memory Exhaustion DoS & Unchecked Uploads
- **Severity**: **HIGH**
- **Location**: `server.py` lines 902–959 (`/api/clinical/upload`):
  1. **Unbounded Payload Read**:
     `content_length = int(self.headers.get('Content-Length', 0))`
     `body = self.rfile.read(content_length)`
     The server reads the entire body into memory without checking an upper limit. A client sending a 500MB payload will crash Render's 512MB RAM instance.
  2. **Missing Magic Byte Validation**:
     The server does not check whether the uploaded payload starts with `%PDF-` before parsing. Non-PDF payloads trigger unhandled exceptions returning `HTTP 500`.
  3. **Cross-Platform Basename Traversal**:
     `safe_filename = os.path.basename(filename) or f"study_{int(time.time())}.pdf"`
     On Linux hosts (such as Render), `os.path.basename` does not treat Windows backslashes (`\`) as directory separators. A filename like `..\..\evil.pdf` will not be stripped properly by `os.path.basename` on Linux.

---

### 4.4 Frontend DOM XSS & HTML Escaping Analysis

- **Framework**: React 18.3.1 (`ReactDOM.createRoot`).
- **XSS Sink Audit**:
  - `dangerouslySetInnerHTML`: **0 occurrences** across all HTML files.
  - `eval()`: **0 occurrences** across all HTML files.
  - `document.write()`: **0 occurrences** across all HTML files.
  - React JSX automatically escapes all interpolated variables (`{variable}`), neutralizing reflected and stored XSS via brand copy, clinical tables, and user justifications.
- **`verify.html` Audit**:
  All dynamic URL query parameters (brand name, certificate ID, timestamp, signer) are rendered strictly via `.textContent = ...`, preventing DOM XSS injection.
- **Security Deficiencies**:
  - **Missing Subresource Integrity (SRI)**: Third-party CDN scripts (React, Tailwind, Babel, jsPDF) lack `integrity` attributes.
  - **Missing Content Security Policy (CSP)**: Neither `index.html` nor `server.py` defines a CSP header.

---

## 5. Render Ephemeral Disk Persistence Analysis & Smallest Safe Fix

### 5.1 Architecture & Failure Modes on Render Free Tier
Render's free tier operates on an ephemeral file system with automatic spin-down after 15 minutes of inactivity. When a service spins down or restarts during a deployment:
1. **Disk Resets**: Any files written to disk during runtime (e.g. `brand_submissions_db.json`, `supabase_users_db.json`, `uploads/clinical_evidence/*.pdf`) are permanently wiped.
2. **0-Byte Truncation Risk**: In `server.py`, persistence writes use:
   ```python
   with open(SUBMISSIONS_DB_FILE, "w", encoding="utf-8") as f:
       json.dump(submissions_list, f, indent=2)
   ```
   Opening with `"w"` immediately truncates the file to 0 bytes before writing. If the Render container restarts or receives a SIGTERM mid-write, the database file is permanently corrupted to 0 bytes.

### 5.2 The Smallest Safe Fix

To guarantee persistence resilience without introducing heavy infrastructure dependencies, the following three-part fix is specified:

```
+---------------------------------------------------------------------------------------+
|                             SMALLEST SAFE PERSISTENCE ARCHITECTURE                    |
+---------------------------------------------------------------------------------------+
|                                                                                       |
|   1. ATOMIC WRITE PATTERN:                                                            |
|      Write to <file>.tmp -> flush() -> os.fsync() -> atomic os.replace(<file>.tmp)   |
|      (Zero risk of 0-byte corrupted files during mid-write container termination)    |
|                                                                                       |
|   2. SEED FALLBACK RESTORATION:                                                       |
|      If JSON DB is missing or 0 bytes on boot, automatically re-seed from clean       |
|      in-memory seed templates (SUB-9021, SUB-9022, SUB-9023)                         |
|                                                                                       |
|   3. BROWSER LOCALSTORAGE + OPTIONAL REMOTE SUPABASE SYNC:                            |
|      Frontend caches workspace in localStorage ('bw_cached_submissions');             |
|      Backend auto-syncs to remote Supabase PostgreSQL when SUPABASE_URL is configured |
|                                                                                       |
+---------------------------------------------------------------------------------------+
```

1. **Atomic File Write-Temp-Rename Pattern**:
   Replace direct `"w"` open calls with a helper function:
   ```python
   def atomic_save_json(filepath: str, data: Any):
       tmp_path = filepath + ".tmp"
       with open(tmp_path, "w", encoding="utf-8") as f:
           json.dump(data, f, indent=2)
           f.flush()
           os.fsync(f.fileno())
       os.replace(tmp_path, filepath)
   ```
   `os.replace` is atomic on POSIX filesystems and atomic on Windows within the same volume. The original file remains completely intact until the new file is fully written and synced to disk.
2. **Database Seeding on Boot**:
   If `brand_submissions_db.json` is missing, empty, or unparseable on server boot, automatically initialize it with the clean default 3 seed submissions.
3. **Thread Safety**:
   Wrap all read/write database operations in a dedicated `threading.RLock()` (`DB_LOCK`) to prevent race conditions during concurrent user submissions.
4. **Client-Side Cache Re-Hydration**:
   The frontend already caches submissions in browser `localStorage` under `bw_cached_submissions`. On boot after a cold restart, if the server returns an empty list, the client can prompt to restore cached submissions.

---

## 6. Actionable Remediation Roadmap for Subsequent Milestones

| Task / Milestone | Target File(s) | Specific Action Items |
| :--- | :--- | :--- |
| **Task C (M2)** | `server.py`, `codex/server.py` | Fix `translate_path` directory traversal vulnerability.<br>Add 25MB file upload limit and `%PDF-` validation.<br>Remove master OTP bypasses (`884192`, `123456`) and stop reflecting OTP in response.<br>Implement `atomic_save_json` pattern with thread locks.<br>Sanitize all input `.strip()` calls with `str(val or "").strip()`.<br>Catch `json.JSONDecodeError` returning clean HTTP 400. |
| **Task C (M2)** | `review_engine.py` | Add Devanagari Unicode regex patterns (`\u0900-\u097F`) for all 9 superlative rules.<br>Add Devanagari disclosure hashtags `#विज्ञापन`, `#प्रायोजित`, `#सहयोग` to eliminate false positives.<br>Support spelling variants (`100% asr`, `chmatkari`).<br>Add policy relevance validation to `adjudicate_counter_evidence`. |
| **Task C (M2)** | `index.html` (Tri-mirror) | Add Render cold-start waking indicator pinging `/api/health`.<br>Connect Review tab textarea to real review validation.<br>Add empty state card when `findings.length === 0`.<br>Prevent `handlePdfUpload` catch block from creating fake successful studies on 400 rejection.<br>Make PDF certificate citations dynamic. |
| **Task C (M2)** | Repository Root | Delete `claude_chat.json` and 22 student exam debris files.<br>Reset `codex/brand_submissions_db.json` back to 3 clean seed submissions.<br>Sanitize active password hashes in `codex/supabase_users_db.json`.<br>Remove `__pycache__` and `*.pyc` from git tracking and update `.gitignore`. |
| **Task B (M3)** | `codex/tests/`, `TESTING.md` | Create dedicated test matrix for 5 violating Hinglish lines, 5 harmless lines, spelling variants, and mixed Devanagari text.<br>Test all 8 failure modes (empty, huge, wrong file, corrupt/scanned PDF, duplicate submit, refresh, empty states, irrelevant counter-evidence).<br>Author comprehensive `TESTING.md`. |
| **Task D (M4)** | `README.md`, `samples/`, `ROADMAP.md` | Populate `samples/` with junk PDF, exaggerated ad copy, honest ad copy, and Hinglish test lines.<br>Overhaul `README.md` with complete 5-step journey, local setup, and declared limitations.<br>Author `ROADMAP.md` (near, mid, long term) and final submission PDF outline. |
| **Task E (M5)** | Rubric Evaluation | Score platform before and after fixes using the 100-point rubric with one-line justifications.<br>Document all declared limitations transparently.<br>Perform clean local git commits without rewriting history. |

---
*Report compiled and certified for Milestone 1 (Task A) by Teamwork Worker.*
