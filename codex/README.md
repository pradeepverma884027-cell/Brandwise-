# Brandwise – Pre-Publication Brand Governance Platform

<p align="center">
  <img src="https://img.shields.io/badge/Render-Live%20Backend-46E3B7?style=for-the-badge&logo=render&logoColor=black" alt="Render Live">
  <img src="https://img.shields.io/badge/GitHub%20Pages-Live%20Frontend-emerald?style=for-the-badge&logo=github" alt="GitHub Pages">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/Compliance-DPDP%20Act%202025-blue?style=for-the-badge" alt="DPDP 2025">
  <img src="https://img.shields.io/badge/Standards-ASCI%202025--26%20Code-orange?style=for-the-badge" alt="ASCI">
  <img src="https://img.shields.io/badge/Tests-406%20Passing%20(100%25)-success?style=for-the-badge" alt="Tests">
</p>

> **"A spell-checker for brand trust: it catches off-brand, unsupported, or non-compliant marketing claims before they go public, shows its working with statutory citations, and never overrides a human."**

Brandwise is an AI-powered pre-publication brand-governance and advertising-compliance platform designed for consumer goods, cosmetics, and healthcare brands. Operating as an automated pre-flight review layer between drafting and distribution, Brandwise guarantees that marketing communications strictly adhere to statutory advertising regulations (**ASCI Code 2025–26**, **Drugs and Magic Remedies Act 1954**, **CDSCO Cosmetics Rules 2020**, **AYUSH Guidelines**, and the **India DPDP Act 2025**) as well as internal brand guidelines.

---

## 🌐 Live Product & Evaluation Links

| Resource | Direct Link | Description |
|---|---|---|
| 🚀 **Live Render Application** | **[https://brandwise-6wl6.onrender.com](https://brandwise-6wl6.onrender.com)** | **Primary live cloud instance** running unified Python backend & SPA on Render. |
| 🛡️ **Public Verification Portal** | **[https://brandwise-6wl6.onrender.com/verify.html](https://brandwise-6wl6.onrender.com/verify.html)** | Standalone cryptographic verification portal for authenticating issued certificates. |
| ☁️ **Deploy to Render (1-Click Live Cloud Backend)** | **[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/pradeepverma884027-cell/Brandwise-)** | 1-Click live full-stack web service deployed on Render cloud. |
| 🌐 **GitHub Pages Mirror** | **[https://pradeepverma884027-cell.github.io/Brandwise-/](https://pradeepverma884027-cell.github.io/Brandwise-/)** | Frontend SPA mirror with client-side offline deterministic engine simulation. |
| 📦 **GitHub Repository** | **[github.com/pradeepverma884027-cell/Brandwise-](https://github.com/pradeepverma884027-cell/Brandwise-)** | Clean, public source code repository. |
| 📄 **Final 18-Page PRD Dossier** | **[`Brandwise_Final_Submission_PRD.pdf`](Brandwise_Final_Submission_PRD.pdf)** | Complete executive PRD addressing all hackathon evaluation criteria. |
| 🧪 **Comprehensive Testing Matrix** | **[`TESTING.md`](TESTING.md)** | Full test catalog: 406 Python tests + 144 Node assertions, zero database drift. |
| 🗺️ **Strategic Product Roadmap** | **[`ROADMAP.md`](ROADMAP.md)** | Strategic vision spanning v3.1 (OCR/multilingual) to v5.0 (enterprise SSO). |

---

## 🛠️ Technology Stack & Architecture

Brandwise runs with **zero mandatory external cloud dependencies** — all three core compliance features execute locally via deterministic heuristics, rule engines, and standard Python libraries:

- **Unified Production Backend (`server.py`)**: Lightweight, standalone Python HTTP daemon (`http.server.SimpleHTTPRequestHandler`) serving REST API endpoints and static SPA files on a single port.
- **Frontend SPA (`index.html`)**: React 18 single-page application with 5 dedicated workspaces: Content Review, Brand Approvals Queue, Clinical Evidence Studio, Visual Asset Inspector, and Hinglish Compliance.
- **Cryptographic Verification Portal (`verify.html`)**: Standalone public verification interface displaying SHA-256 audit digests and approval proofs.
- **Deterministic Governance Engine (`codex/backend/app/core/review_engine.py`)**: Regex boundary matching, phonetic n-grams, ASCI superlative filters, and WCAG 2.2 contrast analyzers.
- **Clinical Evidence Extractor (`codex/backend/app/core/clinical_extractor.py`)**: Pure Python multi-page PDF parser (`pypdf`) extracting structured clinical endpoints, p-values, and statistical discrepancy deltas.
- **Data Persistence**: Atomic file transactions (`write-tmp-rename` pattern) on lightweight JSON databases (`brand_submissions_db.json`, `supabase_users_db.json`) ensuring resilience against race conditions.

---

## 💻 Prerequisites & Foolproof Local Installation

### Prerequisites
- **Python**: Version `3.10`, `3.11`, or `3.12+` (tested on Python 3.12.7).
- **Git**: Any standard Git distribution.
- **Browser**: Any modern browser (Chrome, Edge, Firefox, Safari).

### Installation & Quickstart (Under 60 Seconds)

```bash
# 1. Clone the repository
git clone https://github.com/pradeepverma884027-cell/Brandwise-.git
cd Brandwise-

# 2. Install lean dependencies (pypdf for clinical PDF parsing, requests for testing)
pip install -r requirements.txt

# 3. Start the unified server (defaults to port 8000)
python server.py 8000

# 4. Open in your web browser:
#    Main Dashboard:       http://localhost:8000/
#    Public Verification:  http://localhost:8000/verify.html
#    Health Probe API:     http://localhost:8000/api/health
```

*Note: If port 8000 is occupied, the server automatically scans and binds to the next available port up to 15 attempts.*

---

## ⚙️ Environment Variables

Brandwise is **offline-first**; no API keys are required to run the full application or execute tests. Optional environment variables include:

| Variable | Type | Default | Description |
|---|---|---|---|
| `PORT` | Integer | `8000` (Local) / `10000` (Render) | HTTP port bound by `server.py`. |
| `ANTHROPIC_API_KEY` | String | *Empty (None)* | *(Optional)* Claude 3.5 Sonnet key for cloud LLM semantic review synthesis. |
| `OPENAI_API_KEY` | String | *Empty (None)* | *(Optional)* OpenAI key for semantic embeddings and evaluations. |
| `PYTHON_VERSION` | String | `3.12.10` | Python runtime version specified in `render.yaml`. |

---

## 🚶 The 5-Step Main User Journey

Follow this step-by-step walkthrough to experience the complete compliance lifecycle:

### Step 1: Health Check & System Readiness
- **Action**: Visit `http://localhost:8000/api/health` or observe the top waking indicator banner.
- **Expected Output**: HTTP 200 JSON confirmation with `status: "healthy"`, engine `Brandwise Governance Engine v3.0`, and confirmation of all 3 active improvements.

### Step 2: Submission Ingestion & Pre-Flight Review
- **Action**: Open the dashboard at `http://localhost:8000/`. Select the **Content Review** tab, choose **Instagram Caption**, and input sample marketing copy:
  > *"DermaCare SPF 50 gives 100% protection against all UV rays! Miracle cure for sun damage #skincare"*
- **Expected Output**: The pre-flight score drops to ~52. Interactive Evidence Cards flag:
  - `§4.2 Regulated Claims`: Prohibited superlative *"100% protection"* (requires absolute clinical defense).
  - `Drugs & Magic Remedies Act §3`: Prohibited term *"Miracle cure"*.
  - `ASCI Influencer Code`: Missing commercial disclosure tag (`#ad` or `#vigyapan`).
- Click **"Accept Fix"** on any card to apply an instant, inline tracked replacement without changing creative tone.

### Step 3: Clinical Evidence PDF Ingestion & Discrepancy Verification
- **Action**: In the **Clinical Evidence** panel, upload `samples/Study_CS-2026-88.pdf` (or use the built-in study selector) and enter copy claiming:
  > *"Clinically proven 99% skin hydration in just 7 days!"*
- **Expected Output**: The engine extracts the registered trial dossier (Cohort: 120, baseline hydration: 94.2% at Day 14, p < 0.001) and flags:
  - **Statistical Exaggeration Delta**: Claimed 99.0% vs Clinical 94.2% (+4.8% inflation).
  - **Timeline Compression**: Claimed 7 days vs Registered 14-day protocol.
  - **Canonical Citation**: `Clinical Study CS-2026-88, Page 7, Table 2`.

### Step 4: Interactive Counter-Evidence Adjudication
- **Action**: On a flagged design or clinical allegation, click **"Submit Counter-Evidence"**. Upload an authorized waiver (`samples/Brand_Design_Waiver_BW-2026-09.pdf`) or lab assay certificate (`samples/LAB-AYUSH-904.pdf`), provide Reference ID `BW-WVR-2026-09`, and justification text (>= 10 characters).
- **Expected Output**: The policy relevance engine validates document scope against the allegation category, issues status `"ALLEGATION_REVERTED_AND_DISMISSED"`, restores **+15 compliance score points**, and logs a SHA-256 document proof in the audit trail. Submitting an irrelevant document (e.g., design waiver for a clinical efficacy claim) is cleanly rejected with policy explanation.

### Step 5: Administrative Approval & Public Cryptographic Verification
- **Action**: Switch to the **Brand Approvals** tab. Sign in as Admin (`admin@dermacare.com` / password `1234`). Review the submission and click **"✓ Approve & Issue Certificate"**.
- **Expected Output**:
  - The submission is marked `APPROVED` and assigned a permanent certificate ID (e.g., `BW-CERT-45892-2026`).
  - Click **"📄 Release Audit Report (PDF)"** to download an official compliance certificate generated client-side via `jsPDF`, complete with corporate branding, immutable SHA-256 hash, and vector QR code.
  - Open `http://localhost:8000/verify.html?cert=BW-CERT-45892-2026` to verify cryptographic authenticity on the public registry.

---

## 📁 Sample Assets Directory (`samples/`)

The repository includes curated sample assets in `samples/` for end-to-end evaluation:

| File | Purpose | Test Flow |
|---|---|---|
| `samples/Study_CS-2026-88.pdf` | Registered 8-page dermatological clinical trial PDF with structured efficacy tables. | Test Clinical PDF Ingestion & discrepancy detection. |
| `samples/Brand_Design_Waiver_BW-2026-09.pdf` | Formal legal/brand exception waiver signed by VP of Marketing. | Test Adjudication Gateway dismissal for visual/contrast drift. |
| `samples/LAB-AYUSH-904.pdf` | Certified AYUSH laboratory assay report validating herbal purity. | Test Adjudication Gateway dismissal for AYUSH/traditional claims. |
| `samples/junk_corrupted.pdf` | Corrupted/non-PDF byte payload. | Test input validation (returns HTTP 400 without crashing). |
| `samples/ad_copy_exaggerated.txt` | Unsubstantiated ad copy claiming 99% efficacy in 7 days. | Triggers clinical exaggeration flag (+4.8% delta). |
| `samples/ad_copy_honest.txt` | Compliant ad copy matching clinical trial metrics exactly. | Clears clinical verification with 0 discrepancies. |
| `samples/hinglish_test_lines.txt` | 5 violating lines, 5 harmless lines, and spelling variants. | Tests Hinglish rule matrix and 0 false positives. |

---

## ⚠️ Declared Limitations & Edge Cases

In compliance with hackathon transparency guidelines, the following limitations are declared:

1. **Render Free-Tier Cold Starts**: On the Render free tier, inactive services sleep after 15 minutes. The initial HTTP request may experience a 30–50 second wake-up latency. The frontend features an active loading indicator that pings `/api/health` during spin-up.
2. **OCR on Scanned / Flattened Bitmap PDFs**: The local extractor uses pure-Python `pypdf` to parse layout-aware text streams and vector tables. Scanned bitmap PDFs (containing rasterized images with no underlying text layer) return `EXTRACTED_NO_TABLES` safely without crashing. Integrating local Tesseract/PaddleOCR or cloud vision APIs is scheduled for Roadmap v3.1.
3. **Render Ephemeral Disk Persistence**: Free-tier cloud instances lack persistent disk volumes; local JSON databases re-seed upon container restart. Production enterprise deployments should map to managed PostgreSQL or Supabase (see `ROADMAP.md`). Local concurrency is protected via atomic file write locks (`write-tmp-rename`).
4. **Local Heuristic vs. Vector Embeddings**: In offline mode, semantic matching is performed via deterministic tokenization, regex boundary checks, and phonetic n-gram analysis. Vector semantic similarity search requires activating `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`.
5. **Configurable Regulatory Disclosures**: Vernacular hashtags (`#vigyapan`, `#prayasit`, `#sahyog`, `#विज्ञापन`, `#प्रायोजित`) reflect current ASCI draft guidelines and can be customized in brand policy configuration.

---

## 🧪 Running Automated Test Suites

Brandwise includes a comprehensive test suite of 406 Python unit tests and 144 Node.js empirical checks:

```bash
# 1. Run Milestone 3 Comprehensive Journey Suite (5-step flow + 11 boundary cases)
python -m unittest codex/tests/test_r3_comprehensive_journey.py

# 2. Run Milestone 3 Hinglish Compliance Matrix (violating, harmless, spelling variants)
python -m unittest codex/tests/test_r3_hinglish_matrix.py

# 3. Run Milestone 2 Security & Adjudication Challenger Suites
python -m unittest codex/tests/test_challenger_r3_m2_security.py
python -m unittest codex/tests/test_challenger_r3_m2_r2_adjudication_regex.py

# 4. Run Full Python Test Suite Discovery (All 406 Tests)
python -m unittest discover codex/tests

# 5. Run Milestone 4 Offline GitHub Pages Simulator (144 Node.js assertions)
node codex/tests/test_challenger_imp3_m4_docs_offline.js

# 6. Verify Zero Database Drift (Physical JSON SHA-256 Invariance)
powershell -Command "Get-FileHash -Algorithm SHA256 brand_submissions_db.json, codex\brand_submissions_db.json"
```

*(All test suites execute with a 100% pass rate).*

---

## 🐳 Cloud Packaging & Container Deployment

### Deploy to Render (1-Click Live Cloud Backend)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/pradeepverma884027-cell/Brandwise-)

Brandwise is pre-configured for seamless zero-configuration deployment to Render via `render.yaml`:
1. Click the **Deploy to Render** button above or connect your repository fork to [Render Blueprints](https://dashboard.render.com/blueprints).
2. Render detects `render.yaml` automatically and configures the environment:
   - **Service Name**: `brandwise` (Web Service, Python environment)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python server.py 10000`
   - **Health Check Probe**: `/api/health`
   - **Environment Variables**:
     - `PORT`: `10000` (HTTP port bound by `server.py`)
     - `PYTHON_VERSION`: `3.12.10`
   - **Public Verification Registry**: Deployed at `https://<your-subdomain>.onrender.com/verify.html`

### Local Docker Execution
```bash
# Build the production container
docker build -t brandwise:latest .

# Run container on port 10000
docker run -p 10000:10000 -e PORT=10000 brandwise:latest

# Access at http://localhost:10000/
```

---

## 👥 Statement of Team Contributions

- **Shivank Atri (Sk) — Product Architect & Compliance Pipeline Lead (40% Share)**: Designed dual-tier deterministic + semantic review architecture, regulatory rule taxonomies, prompt engineering schemas, and user testing calibration.
- **Pradeep Kumar — Full-Stack Backend Contributor (30% Share)**: Built unified Python server (`server.py`), REST API endpoints, clinical PDF extraction engine, atomic JSON database synchronization, and automated test suites.
- **Riyanshi Jain & Kartik Parashar — Frontend & Design Systems (30% Share)**: Engineered React 18 single-page application (`index.html`), interactive Evidence Cards, tracked diffing engine, Brand Approvals Queue, and client-side vector PDF synthesis.

---

## ⚖️ Regulatory References

1. **ASCI Code 2025–26**: Advertising Standards Council of India Code for Self-Regulation.
2. **ASCI Influencer Guidelines**: Mandatory commercial disclosures for digital media.
3. **Drugs and Magic Remedies (Objectionable Advertisements) Act 1954**: Statutory prohibitions on miraculous cure claims.
4. **CDSCO Cosmetics Rules 2020**: Substantiation requirements for cosmetic and dermatological claims.
5. **India DPDP Act 2025**: Digital Personal Data Protection statutory rules on purpose limitation and zero-retention.
6. **W3C WCAG 2.2 AA**: Web Content Accessibility Guidelines for visual contrast ratios.

---

<p align="center">
  <b>Brandwise • Enterprise Pre-Publication Brand Governance Platform</b><br>
  Built with ❤️ for Hackathon Round 3 • October 2026
</p>
