# Project: Brandwise Improvement 2 — Interactive Evidence-Based Adjudication & Visual Compliance Engine

## Architecture
Brandwise is a pre-publication brand governance and compliance platform for regulated industries.
This project implements Improvement 2 consisting of:
1. **Visual Asset Compliance Inspector** (`codex/backend/app/core/review_engine.py`):
   - Pure Python deterministic rules (zero cloud APIs, zero external model dependencies).
   - Logo geometry distortion: flags aspect ratio drift > 2% from expected brand ratio as severity "high".
   - Brand palette colour drift (ΔE): computes Euclidean RGB distance from approved brand palette (#0F172A, #0284C7, #10B981). Flags $15.0 \le d \le 65.0$ as severity "medium".
   - Disclaimer contrast ratio: WCAG 2.2 formula $(L_1 + 0.05)/(L_2 + 0.05)$, flags $< 4.5:1$ (WCAG AA failure) as severity "high".
   - Missing alt-text: flags missing or empty image alt-text as severity "medium" accessibility violation.
2. **Interactive Counter-Evidence Gateway & Adjudication Engine** (`codex/backend/app/core/review_engine.py`):
   - Adjudicates submitted counter-evidence against flagged allegations.
   - 6 canonical evidence types: clinical trial certificate, CDSCO Stage IV clearance, legal waiver sign-off, lab assay report, influencer contract exemption, AYUSH clinical registry.
   - Validates required reference ID and justification ($\ge 10$ characters).
   - Generates deterministic SHA-256 document hash.
   - Evaluates evidence: returns `ALLEGATION_REVERTED_AND_DISMISSED` (restoring +15 compliance score) or `REJECTED_INSUFFICIENT_EVIDENCE`.
   - Appends dismissal event with document hash to audit log.
3. **Backend Server Integration & Cryptographic Parity** (`server.py` & `codex/server.py`):
   - `POST /api/visual/inspect`: accepts asset metadata JSON, returns violation findings.
   - `POST /api/adjudication/submit`: accepts allegation and counter-evidence JSON, executes adjudication, logs to audit trail, returns verdict.
   - 100% SHA256 byte-for-byte mirror parity between `server.py` and `codex/server.py`.
4. **Frontend Single-Page Application (SPA)** (`codex/frontend/index.html`, `index.html`, `docs/index.html`):
   - Dedicated "🖼️ Visual Inspector" tab (`activeTab === 'visual'`) in sidebar with badge.
   - Asset submission panel with aspect ratio, detected colors, disclaimer colors, and alt-text controls.
   - 3 pre-loaded synthetic visual asset presets (Compliant, Logo Stretch, Palette Drift + Contrast Failure).
   - Color-coded finding cards with severity badges, suggested fixes, and "⚖️ Submit Counter-Evidence" button.
   - Counter-Evidence Submission Modal with dropdown, reference ID, justification, and document hash.
   - Seamless dual execution: local server API calls + GitHub Pages offline client-side fallback simulation.
   - UI updates card to "✅ Allegation Dismissed — Evidence Accepted" with timestamp and document hash, restores score (+15 points per dismissed allegation), appends audit trail.
   - 100% byte-for-byte tri-file parity across `codex/frontend/index.html`, `index.html`, and `docs/index.html`.
5. **Comprehensive Automated Test Suite** (`codex/tests/`):
   - `test_visual_compliance.py`: boundary tests for geometry (>2.0%), palette drift (15-65), contrast (<4.5:1), alt-text, API contracts.
   - `test_adjudication.py`: valid vs invalid counter-evidence, score restoration, audit log persistence, API contracts.
   - Runs cleanly via Python standard library `unittest` runner.
6. **Render Cloud Deployment & Production Resilience** (`render.yaml`, `Dockerfile`, `Procfile`, `requirements.txt`, `server.py`):
   - **Render Blueprint (`render.yaml`)**: Declares web service `brandwise`, Python 3.12 environment, free tier plan, buildCommand `pip install -r requirements.txt`, startCommand `python server.py 10000`, and health check `/api/health`.
   - **Containerization (`Dockerfile`)**: Standard Python 3.12 slim container with dependency caching, port 10000 exposure, and automated health checks.
   - **Process Configuration (`Procfile`)**: Process specification `web: python server.py $PORT` for dynamic platform port binding.
   - **Lean Dependencies (`requirements.txt`)**: Fast-installing dependency manifest (`pypdf>=5.0.0`, `requests>=2.31.0`) ensuring rapid cloud builds without bloat.
   - **Unified Server Resilience (`server.py` & `codex/server.py`)**:
     - Dynamic port evaluation: `PORT = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 8000))`
     - Socket binding: `0.0.0.0`
     - Cloud probe support: `do_HEAD` handler responding immediately with HTTP 200 on `/api/health` and `/`
     - Cryptographic parity: 100% SHA-256 byte-for-byte identity between `server.py` and `codex/server.py`.
   - **Live Cloud Documentation**: Step-by-step instructions and 1-click "Deploy to Render" button in `README.md` and `codex/README.md`.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | Logo Geometry Distortion Detection | Aspect ratio drift > 2% flagged as high severity logo_distortion | M1 | ORIGINAL_REQUEST R1 |
| F02 | Brand Palette Colour Drift (ΔE) | Euclidean RGB distance 15-65 to brand palette flagged as medium severity palette_drift | M1 | ORIGINAL_REQUEST R1 |
| F03 | Disclaimer Contrast Ratio | WCAG 2.2 contrast ratio < 4.5:1 flagged as high severity contrast_failure | M1 | ORIGINAL_REQUEST R1 |
| F04 | Missing Alt-Text Detection | Missing/empty alt-text flagged as medium severity accessibility violation | M1 | ORIGINAL_REQUEST R1 |
| F05 | Core Adjudication Engine | Adjudicate counter-evidence for 6 evidence types, min 10 char justification, SHA256 hash, +15 score delta | M1 | ORIGINAL_REQUEST R2 |
| F06 | Endpoint POST /api/visual/inspect | Expose inspect_visual_geometry_and_palette via HTTP REST endpoint | M2 | ORIGINAL_REQUEST R4 |
| F07 | Endpoint POST /api/adjudication/submit | Expose adjudicate_counter_evidence via HTTP REST endpoint with audit logging | M2 | ORIGINAL_REQUEST R4 |
| F08 | Server Mirror Parity | Ensure 100% SHA256 parity between server.py and codex/server.py | M2 | ORIGINAL_REQUEST R4, R6 |
| F09 | SPA Visual Inspector Tab | Dedicated "🖼️ Visual Inspector" tab in navigation bar with badge counter | M3 | ORIGINAL_REQUEST R3 |
| F10 | Visual Asset Panel & Presets | Input controls for metadata + 3 synthetic presets (compliant, logo stretch, drift+contrast) | M3 | ORIGINAL_REQUEST R3 |
| F11 | Visual Finding Cards & Action Buttons | Color-coded visual finding cards with "⚖️ Submit Counter-Evidence" button | M3 | ORIGINAL_REQUEST R2, R3 |
| F12 | Counter-Evidence Modal & Local Fallback | Interactive modal, client-side fallback simulation for GitHub Pages, UI dismissal update (+15 score) | M3 | ORIGINAL_REQUEST R2 |
| F13 | Tri-HTML Mirror Parity | Ensure byte-for-byte exact identity across codex/frontend/index.html, index.html, docs/index.html | M3 | ORIGINAL_REQUEST R6 |
| F14 | Visual Compliance Test Suite | Unit & API tests in codex/tests/test_visual_compliance.py | M4 | ORIGINAL_REQUEST R5 |
| F15 | Adjudication Test Suite | Unit & API tests in codex/tests/test_adjudication.py | M4 | ORIGINAL_REQUEST R5 |
| F16 | Full Verification & Git Deployment | Verify all tests pass, SHA256 mirror parity, commit and push to main | M4 | ORIGINAL_REQUEST R6 |
| F17 | Render Blueprint (render.yaml) | Web service specification for 1-click Render deployment | M5 | ORIGINAL_REQUEST Issue 4 |
| F18 | Containerization (Dockerfile) | Production Dockerfile for Render or container hosts | M5 | ORIGINAL_REQUEST Issue 4 |
| F19 | Process File (Procfile) | Procfile specifying web: python server.py $PORT | M5 | ORIGINAL_REQUEST Issue 4 |
| F20 | Lean Root requirements.txt | Fast-installing dependencies (pypdf, requests) for Render free tier | M5 | ORIGINAL_REQUEST Issue 4 |
| F21 | Server Port & HEAD Endpoint | Support PORT env/arg, 0.0.0.0 binding, and HTTP HEAD on /api/health | M5 | ORIGINAL_REQUEST Issue 4 |
| F22 | Server Mirror Parity | Maintain 100% SHA-256 parity between server.py and codex/server.py | M5 | ORIGINAL_REQUEST Issue 4 |
| F23 | Render Deployment Docs | Step-by-step deploy instructions & 1-click button in README.md | M5 | ORIGINAL_REQUEST Issue 4 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | `engine_core` | Visual Compliance Inspector & Counter-Evidence Adjudication Engine (`review_engine.py`) | none | DONE |
| M2 | `backend_api` | REST Endpoints (`/api/visual/inspect`, `/api/adjudication/submit`), Audit Logging & Server Parity (`server.py`, `codex/server.py`) | M1 | DONE |
| M3 | `frontend_spa` | Frontend Visual Inspector Tab, Preloaded Presets, Adjudication Modal & Tri-HTML Parity (`codex/frontend/index.html`, `index.html`, `docs/index.html`) | M2 | DONE |
| M4 | `testing_verification` | Comprehensive Test Suites (`test_visual_compliance.py`, `test_adjudication.py`), Parity Verification & Git Deploy | M1, M2, M3 | DONE |
| M5 | `render_backend_deploy` | Issue 4: render.yaml, Dockerfile, Procfile, requirements.txt, server.py HEAD/port binding, server parity & README docs | M1, M2, M3, M4 | DONE |

---

## Interface Contracts

### M1 `review_engine.py` ↔ `server.py`
```python
def inspect_visual_geometry_and_palette(self, asset_metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Input:
    {
        "asset_id": str (optional, default "asset-001"),
        "aspect_ratio": float,
        "expected_aspect_ratio": float (default 1.0),
        "detected_hex_colors": list[str],
        "disclaimer_fg": str,
        "disclaimer_bg": str,
        "alt_text": str | None
    }
    Output:
    {
        "is_compliant": bool,
        "violations": list[dict], # id, type, severity, message, source_ref, suggested_fix
        "aspect_ratio_drift": float | None,
        "contrast_ratio": float | None,
        "asset_id": str
    }
    """

def adjudicate_counter_evidence(self, allegation_id: str, allegation_category: str, counter_evidence: dict[str, Any]) -> dict[str, Any]:
    """
    Input:
    {
        "allegation_id": str,
        "allegation_category": str,
        "counter_evidence": {
            "evidence_type": str, # one of: clinical_trial_certificate, cdsco_stage4_clearance, legal_waiver_signoff, lab_assay_report, influencer_contract_exemption, ayush_clinical_registry
            "reference_id": str,
            "justification": str, # min 10 chars
            "document_hash": str | None
        }
    }
    Output (Success):
    {
        "success": True,
        "adjudication": "ALLEGATION_REVERTED_AND_DISMISSED",
        "allegation_id": str,
        "allegation_category": str,
        "reversal_timestamp": str (ISO 8601 UTC),
        "document_hash": str (SHA-256),
        "evidence_reference": str,
        "evidence_type": str,
        "restored_score_delta": 15,
        "audit_note": str,
        "status": "dismissed_with_evidence"
    }
    Output (Failure):
    {
        "success": False,
        "adjudication": "REJECTED_INSUFFICIENT_EVIDENCE",
        "message": str
    }
    """
```

### M2 Backend REST APIs ↔ Frontend SPA
```http
POST /api/visual/inspect
Content-Type: application/json
Body: <asset_metadata>
Response 200:
{
    "status": "success",
    "result": <inspect_visual_geometry_and_palette return object>
}

POST /api/adjudication/submit
Content-Type: application/json
Body:
{
    "allegation_id": str,
    "allegation_category": str,
    "counter_evidence": {
        "evidence_type": str,
        "reference_id": str,
        "justification": str,
        "document_hash": str | None
    }
}
Response 200:
{
    "status": "success",
    "adjudication": "ALLEGATION_REVERTED_AND_DISMISSED",
    "result": <adjudication return object>
}
```

---

## Code Layout
- `render.yaml` (Render Blueprint specification for web service deployment)
- `Dockerfile` (Production container configuration)
- `Procfile` (Procfile web process runner)
- `requirements.txt` (Root Python dependencies)
- `server.py` & `codex/server.py` (Production standalone HTTP server; MUST maintain 100% SHA256 mirror parity)
- `codex/frontend/index.html`, `index.html`, `docs/index.html` (React 18 SPA; MUST maintain 100% byte-for-byte tri-file parity)
- `codex/frontend/verify.html`, `verify.html`, `docs/verify.html` (Public verification portal; MUST maintain 100% byte-for-byte tri-file parity)
- `README.md` & `codex/README.md` (Project and deployment documentation)
- `codex/backend/app/core/review_engine.py` (Source of truth for visual inspection & adjudication engine)
- `codex/tests/` (Automated test suites)
