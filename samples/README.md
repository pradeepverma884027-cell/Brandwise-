# Brandwise Sample Assets & Verification Handbook

Welcome to the **Brandwise** sample assets library. This directory contains representative verification fixtures, clinical dossiers, legal waivers, advertising copy, and multilingual test lines designed to demonstrate and validate all platform compliance capabilities during evaluation.

---

## Directory Inventory

| Asset Name | Format | Size | Description & Primary Use Case |
|:---|:---:|:---:|:---|
| **`Study_CS-2026-88.pdf`** | PDF | 14.5 KB | 8-page randomized, double-blind clinical study dossier (Protocol CS-2026-88, N=120, 14 days). Table 2.1 contains quantitative dermatological endpoints (94.2% hydration, 68.0% acne reduction, 42.5% sebum reduction). Use for **Clinical PDF Ingestion** and **Discrepancy Analysis**. |
| **`LAB-AYUSH-904.pdf`** | PDF | 6.1 KB | 4-page independent bio-analytical assay certificate (Assay LAB-AYUSH-904, N=85, 7 days). Table 4.1 contains soothing efficacy (89.4%) and skin irritation index (0.02). Use for **Ayush / Traditional Medicine Adjudication**. |
| **`Brand_Design_Waiver_BW-2026-09.pdf`** | PDF | 1.9 KB | Signed legal design waiver (Ref: `WAIVER-BW-2026-09`) from corporate marketing counsel. Use in the **Counter-Evidence Adjudication Gateway** to dismiss visual aspect ratio drift allegations and restore +15 score points. |
| **`junk_corrupted.pdf`** | PDF / Junk | ~320 B | Corrupted binary file lacking valid cross-reference (`xref`) and `%%EOF` markers. Use to test **Adversarial Input Validation** and verify that corrupted uploads fail gracefully with HTTP 400 without crashing the server. |
| **`ad_copy_exaggerated.txt`** | Text | ~1.5 KB | Marketing copy containing unsubstantiated superlatives ("World's #1", "100% asar"), timeline compressions ("in just 3 days" vs 14 days), and exaggerated clinical metrics (99.8% vs 94.2%). Triggers 4+ discrepancy flags and score deductions. |
| **`ad_copy_honest.txt`** | Text | ~1.4 KB | Fully substantiated marketing copy matching Study CS-2026-88 endpoints, complete with mandatory influencer disclosure (`#ad`) and clinical citations. Demonstrates 100/100 compliance scoring. |
| **`hinglish_test_lines.txt`** | Text | ~3.8 KB | Benchmark test matrix for vernacular compliance: 5 violating lines, 5 harmless lines (0 false positives), spelling variants (`asar`/`asr`/`असर`), and code-mixed Latin-Devanagari phrases. |

---

## How to Test via the Web UI (Interactive Guide)

Ensure the server is running locally on port 8000 (e.g. `python server.py 8000`) and open `http://localhost:8000` in your browser.

### 1. Test Clinical PDF Ingestion & Verification
1. Navigate to the **"Clinical Evidence"** workspace or click the **"Upload Clinical Study"** button in the top navigation.
2. Drag and drop `samples/Study_CS-2026-88.pdf` into the drop zone (or click the quick sample link).
3. The platform extracts the study metadata (Protocol `CS-2026-88`, 120 subjects, 14-day duration) and tabular endpoints from Table 2.1 on Page 7.
4. Paste the contents of `samples/ad_copy_exaggerated.txt` into the **"Verify Marketing Copy"** box and click **"Analyze Copy"**.
   - **Observed Result:** Red discrepancy badges appear flagging **+5.6% hydration exaggeration**, **-11 days timeline compression**, and **+20.0% acne lesion reduction exaggeration** with exact citations (`Clinical Study CS-2026-88, Page 7, Table 2.1`).
5. Replace with `samples/ad_copy_honest.txt` and click **"Analyze Copy"**.
   - **Observed Result:** Green checkmarks appear; all claims marked **SUBSTANTIATED**; zero discrepancy flags.

### 2. Test Adversarial Uploads (Negative Validation)
1. In the Clinical Upload drop zone, upload `samples/junk_corrupted.pdf`.
2. **Observed Result:** The UI displays a clear, non-crashing error notification: `"Corrupted or invalid PDF payload"`. The server remains healthy and active.

### 3. Test Hinglish & Vernacular Compliance
1. Switch to the **"Hinglish Compliance"** tab.
2. Copy any line from Section 1 of `samples/hinglish_test_lines.txt` (e.g., `Yeh cream lagao aur 100% asar paao ek jhatke mein bina kisi side effect ke.`) and click **"Evaluate Copy"**.
   - **Observed Result:** Highlights `"100% asar"` and `"ek jhatke mein"`, displays a deduction, and provides a culturally resonant compliant rewrite.
3. Copy Line 2 of Section 2 (`Yeh lotion twacha ko dry hone se bachata hai aur fresh feel deta hai. #विज्ञापन`) and click **"Evaluate Copy"**.
   - **Observed Result:** Score = **100/100**, 0 false positives, green badge `"COMPLIANT"`.

### 4. Test Counter-Evidence Adjudication Gateway
1. Navigate to the **"Governance Submissions"** review queue.
2. Select an allegation flagged for visual distortion or unverified claim.
3. Click **"Adjudicate Counter-Evidence"**.
4. Select Evidence Type: **Legal Waiver Signoff**, enter Reference ID `WAIVER-BW-2026-09`, provide a brief justification, and attach `samples/Brand_Design_Waiver_BW-2026-09.pdf`.
5. Click **"Submit Adjudication"**.
   - **Observed Result:** Allegation is dismissed, status updates to `"ALLEGATION_REVERTED_AND_DISMISSED"`, and **+15 score points** are restored.

---

## How to Test via REST API (`curl` & PowerShell)

### 1. Test Clinical PDF Upload
```bash
# Upload Study_CS-2026-88.pdf (using application/pdf content type)
curl -X POST http://localhost:8000/api/clinical/upload \
  -H "Content-Type: application/pdf" \
  -H "X-Filename: Study_CS-2026-88.pdf" \
  --data-binary "@samples/Study_CS-2026-88.pdf"
```
**Expected Response:** HTTP 200, `{"status": "success", "study": {"study_id": "CS-2026-88", ...}}`

```bash
# Upload corrupted PDF fixture (Negative boundary test)
curl -X POST http://localhost:8000/api/clinical/upload \
  -H "Content-Type: application/pdf" \
  -H "X-Filename: junk_corrupted.pdf" \
  --data-binary "@samples/junk_corrupted.pdf"
```
**Expected Response:** HTTP 400 Bad Request, `{"status": "error", "message": "Corrupted or invalid PDF payload..."}`

### 2. Test Clinical Discrepancy Verification
```bash
# Test Exaggerated Copy
curl -X POST http://localhost:8000/api/clinical/verify-copy \
  -H "Content-Type: application/json" \
  -d '{"copy_text": "Provides 99% hydration in just 3 days!", "study_id": "CS-2026-88"}'
```
**Expected Response:** HTTP 200, `"has_discrepancies": true`, with items flagging `+4.8% exaggeration` and `-11 days premature claim`.

```bash
# Test Honest Copy
curl -X POST http://localhost:8000/api/clinical/verify-copy \
  -H "Content-Type: application/json" \
  -d '{"copy_text": "Clinically proven 94.2% hydration over 14 days. #ad", "study_id": "CS-2026-88"}'
```
**Expected Response:** HTTP 200, `"has_discrepancies": false`, `"discrepancies": []`

### 3. Test Hinglish Compliance Endpoint
```bash
# Test Prohibited Hinglish Superlative
curl -X POST http://localhost:8000/api/hinglish/check \
  -H "Content-Type: application/json" \
  -d '{"text": "Hamara chamatkari ayurvedic tel baalon ko jad se ugata hai hamesha ke liye."}'
```
**Expected Response:** HTTP 200, `"compliance_score" < 100`, violations include `chamatkari`, `jad se`, `hamesha ke liye`.

```bash
# Test Harmless Devanagari Copy (Zero False Positives)
curl -X POST http://localhost:8000/api/hinglish/check \
  -H "Content-Type: application/json" \
  -d '{"text": "Yeh lotion twacha ko dry hone se bachata hai aur fresh feel deta hai. #विज्ञापन"}'
```
**Expected Response:** HTTP 200, `"compliance_score": 100`, `"findings": []`, `"is_compliant": true`.

### 4. Test Counter-Evidence Adjudication
```bash
curl -X POST http://localhost:8000/api/adjudication/submit \
  -H "Content-Type: application/json" \
  -d '{
    "allegation_id": "allegation-vis-01",
    "allegation_category": "visual_drift",
    "counter_evidence": {
      "evidence_type": "legal_waiver_signoff",
      "reference_id": "WAIVER-BW-2026-09",
      "justification": "Signed brand identity exception waiver executed by corporate legal counsel.",
      "document_hash": "9A31EF98987356435BB54113679876FF87E8A63BF39A7ACCF5C62929801A8A3A"
    }
  }'
```
**Expected Response:** HTTP 200, `"status": "success"`, `"adjudication": "ALLEGATION_REVERTED_AND_DISMISSED"`, `"restored_score_delta": 15`.
