# Brandwise Strategic Product Roadmap (v3.1 – v5.0+)

**Document Version:** 3.0.0  
**Target Platform:** Brandwise AI Pre-Publication Brand Governance & Compliance Platform  
**Target Horizons:** Near-Term (v3.1–v3.2), Mid-Term (v4.0), and Long-Term Enterprise (v5.0+)  
**Repository:** `https://github.com/pradeepverma884027-cell/Brandwise-`  
**Live Production Application:** `https://brandwise-6wl6.onrender.com`  

---

## Strategic Vision & Product Philosophy

Brandwise operates as an automated pre-flight brand-governance and advertising-compliance review copilot for regulated consumer goods, cosmetics, and healthcare brands. In Round 3, Brandwise delivered a hardened, offline-first deterministic engine capable of parsing multi-page clinical trial PDFs, verifying marketing copy against quantitative trial endpoints, evaluating multilingual Hinglish and native Devanagari copy with zero false positives, adjudicating counter-evidence documents, and sealing compliance certificates with immutable SHA-256 cryptographic proofs.

This roadmap outlines the strategic architectural trajectory to scale Brandwise from a hardened offline-first pre-screening engine into a globally unified, multi-modal, and continuous compliance intelligence platform for regulated enterprise brands.

```
+----------------------------------------------------------------------------------------------------+
|                                    BRANDWISE EVOLUTION ROADMAP                                     |
+------------------------------+----------------------------------+----------------------------------+
|    Near-Term (v3.1 - v3.2)   |         Mid-Term (v4.0)          |    Long-Term Enterprise (v5.0)   |
|   Vernacular & OCR Depth     |     Multi-Modal & Registries     |      Enterprise & Ecosystem      |
+------------------------------+----------------------------------+----------------------------------+
| • Local OCR Engine (Paddle)  | • Video / Audio Frame Governance | • Multi-Tenant Enterprise SSO    |
| • PDF Table Visual Bounding  | • Whisper.cpp Local Audio Review | • Role-Based Access (SAML/Okta)  |
| • Regional Indian Languages  | • CTRI & ClinicalTrials Registry | • Blockchain Audit Anchoring     |
|   (Tamil, Telugu, Bengali)   | • ASCI Automated Complaint Tool  | • Social Ad Library Monitoring   |
| • Offline PWA Desktop Client | • Competitor Campaign Auditing   | • Global Regulatory Connectors   |
+------------------------------+----------------------------------+----------------------------------+
```

---

## 1. Near-Term Horizon (v3.1 – v3.2): Vernacular Depth & Local Vision

**Target Delivery:** Q1 – Q2 2027  
**Focus:** Enhancing offline data extraction, deep visual document inspection, and expanding regional language coverage across the Indian subcontinent.

### 1.1 Local Offline OCR Engine Integration (`v3.1`)
- **Current Limitation:** Scanned or image-only clinical PDF dossiers (containing rasterized scans of physical lab certificates or hospital records) currently parse as 0 extractable text characters (`EXTRACTED_NO_TABLES`).
- **Target Implementation:**
  - Embed a lightweight, CPU-optimized local optical character recognition (OCR) engine (`PaddleOCR` or `Tesseract 5.x`) directly into the backend processing pipeline.
  - Enable automatic layout-aware image thresholding, binarization, and deskewing for scanned hospital test certificates, AYUSH lab reports, and CDSCO stage certificates.
  - **Zero Data Leakage:** OCR executes 100% locally on the host container without streaming sensitive proprietary clinical formulations to external cloud vision APIs, preserving the platform's strict offline-first security perimeter.

### 1.2 Automated PDF Table Structure Visualization (`v3.1`)
- **Target Implementation:**
  - Build an interactive visual PDF document inspector in the frontend Single Page Application (SPA).
  - Overlay color-coded bounding boxes around detected clinical tables (e.g., Table 2.1 on Page 7) and primary efficacy endpoint cells.
  - Provide an interactive side-by-side comparison modal: when an evaluator clicks a flagged clinical claim in the marketing review queue, the UI automatically opens the corresponding PDF page, highlights the source cell, and displays the statistical delta tooltip.

### 1.3 Expanded Regional Indian Language Rule Engines (`v3.2`)
- **Target Implementation:**
  - Expand beyond Hindi and Latin Hinglish to cover the top 5 high-growth vernacular advertising markets in India:
    1. **Tamil (தமிழ்):** Statutory disclaimers (`#விளம்பரம்`), prohibited medical superlatives (*அற்புதமான*, *நிரந்தர தீர்வு*), and cosmetic fairness claims under Tamil Nadu consumer protection standards.
    2. **Telugu (తెలుగు):** Statutory disclosures (`#ప్రకటన`), AYUSH efficacy claims (*అద్భుతమైన*, *శాశ్వత నివారణ*), and local influencer commercial rules.
    3. **Bengali (বাংলা):** Commercial disclosures (`#বিজ্ঞাপন`), traditional medicine claims (*চমৎকার*, *স্থায়ী নিরাময়*), and West Bengal consumer forum regulations.
    4. **Marathi (मराठी):** Vernacular disclosures (`#जाहिरात`) and cosmetics rules.
    5. **Gujarati (ગુજરાતી):** Commercial disclaimers (`#જાહેરાત`) and commercial CTA monitoring.
  - Implement language-specific phonetic lemmatizers and code-switching tokenizers to eliminate false positives on benign colloquial expressions.

---

## 2. Mid-Term Horizon (v4.0): Multi-Modal Governance & Public Registries

**Target Delivery:** Q3 – Q4 2027  
**Focus:** Expanding from static text/PDF governance to dynamic video/audio content and automated public clinical trial registry integration.

### 2.1 Real-Time Multi-Modal Video & Audio Frame Governance
- **Target Implementation:**
  - **Short-Form Video Analysis:** Native ingestion pipeline for video creatives (Instagram Reels, YouTube Shorts, TikTok, Facebook Video Ads).
  - **Local Speech-to-Text Transcription:** Integrate quantized `Whisper.cpp` (executing locally on CPU/GPU) to extract and transcribe spoken dialogue, voiceovers, and influencer claims in real time.
  - **On-Screen Super / Disclaimer Auditing:**
    - Computer vision models to detect on-screen disclaimers ("supers") across video frames.
    - Measure compliance with ASCI Video Advertising Guidelines: minimum font height (equivalent to 12 pixels per 720p frame), contrast ratio against moving backgrounds (>4.5:1), and minimum on-screen dwell time (3 seconds for up to 10 words, 5 seconds for longer text).
  - Generate synchronized video timeline markers highlighting the exact second where an unsubstantiated claim or missing hashtag occurs.

### 2.2 Automated Counter-Evidence Registry Cross-Referencing
- **Target Implementation:**
  - Direct API connectors to national and international public clinical trial registries:
    - **CTRI (Clinical Trials Registry - India)**: Automated verification of registration numbers (`CTRI/YYYY/MM/NNNNNN`), ethics committee approvals, and registered trial phases.
    - **ClinicalTrials.gov (NIH/NLM)**: Cross-referencing NCT numbers (`NCTXXXXXXXX`) to verify primary outcome measures, trial duration, and cohort size against uploaded PDF claims.
  - Automated revocation or warning when counter-evidence cites a clinical trial that has been terminated, suspended, or flagged for data integrity issues.

### 2.3 ASCI Automated Regulatory Complaint Connector
- **Target Implementation:**
  - Enable corporate legal teams to monitor competitor campaigns and assemble formal complaint dossiers.
  - One-click export of structured, evidence-backed complaint packages formatted according to the **Advertising Standards Council of India (ASCI) Consumer Complaints Council (CCC)** submission schema.
  - Includes full forensic timeline, discrepancy deltas, missing disclosure captures, and cryptographic SHA-256 audit proof certificates ready for filing.

---

## 3. Long-Term Enterprise Horizon (v5.0+): Enterprise Infrastructure & Ecosystem

**Target Delivery:** 2028 and Beyond  
**Focus:** Enterprise scalability, identity federation, cryptographic blockchain anchoring, and continuous real-time market surveillance.

### 3.1 Multi-Tenant Enterprise SSO & Fine-Grained RBAC
- **Target Implementation:**
  - Enterprise identity federation supporting **SAML 2.0**, **Okta**, **Azure Active Directory (Entra ID)**, and **Google Workspace**.
  - Hierarchical Role-Based Access Control (RBAC):
    - *Content Creator / Agency:* Drafts copy, pre-screens submissions, views suggested fixes.
    - *Clinical / Regulatory Specialist:* Uploads and certifies clinical trial study dossiers, validates endpoints.
    - *Corporate Legal Counsel:* Adjudicates counter-evidence, signs legal design waivers.
    - *Chief Governance Officer (CGO):* Approves public certificates, executes cryptographic release seals.
  - Multi-tenant data segregation with client-managed encryption keys (CMEK) and strict tenant boundary isolation.

### 3.2 Cryptographic Regulatory Audit Trail Blockchain Anchoring
- **Target Implementation:**
  - Anchor Brandwise SHA-256 compliance certificate proofs onto high-throughput public/consortium blockchains (e.g., Ethereum Layer 2 / Polygon / Hedera Hashgraph).
  - Provides immutable, publicly verifiable, timestamped proof that a specific advertising asset was certified compliant prior to public broadcast.
  - Protects brands against retroactive regulatory penalty disputes, class-action advertising lawsuits, and distributor liability claims.

### 3.3 Continuous Social Media Ad Library Surveillance
- **Target Implementation:**
  - Automated continuous crawler integrating with public ad transparency libraries:
    - **Meta Ad Library** (Facebook & Instagram)
    - **Google Ads Transparency Center** (YouTube & Google Search)
    - **TikTok Creative Center**
  - Continuous parity verification: Automatically compares active live ads in the market against approved internal Brandwise certificates.
  - Real-time Slack/Teams alerts when an agency or influencer publishes modified, unapproved, or non-compliant creative variants in live production campaigns.

---

## Strategic Roadmap Summary Matrix

| Milestone | Release | Core Capabilities | Regulatory Impact | Technical Architecture |
|:---|:---:|:---|:---|:---|
| **v3.0 (Current)** | R3 Final | Deterministic rule engine, 8-endpoint clinical PDF parser, Hinglish/Devanagari NLP, counter-evidence gateway, SHA-256 certificate sealing | ASCI Code 2025–26, DMRA 1954, CDSCO 2020, AYUSH guidelines | Pure Python offline-first backend, React SPA, Render cloud deployment |
| **v3.1** | Near-Term | Local OCR engine (PaddleOCR/Tesseract), visual PDF bounding box and table structure inspector | Scanned hospital lab certs, physical prescription audits | CPU-bound local computer vision, zero external cloud leaks |
| **v3.2** | Near-Term | Expanded regional Indian languages (Tamil, Telugu, Bengali, Marathi, Gujarati) | Multi-state vernacular advertising compliance across Tier 2/3 markets | Vernacular phonetic tokenizers, localized statutory disclosure rules |
| **v4.0** | Mid-Term | Multi-modal video/audio frame governance (Whisper.cpp), CTRI registry connector, ASCI CCC complaint export | Real-time influencer video/Reels compliance, registered trial validation | Quantized speech-to-text models, public registry API adapters |
| **v5.0 Enterprise** | Long-Term | Multi-tenant enterprise SSO (SAML/Okta), blockchain audit anchoring, continuous Meta/Google Ad Library monitoring | Enterprise brand protection, immutable legal defense in litigation | Multi-tenant cloud/hybrid architecture, Ethereum/Polygon L2 anchor |

---

*Brandwise Product Strategy & Engineering Council — Certified for Hackathon Round 3 Deliverables.*
