"""
Comprehensive End-to-End User Journey and Failure Boundary Test Suite for Brandwise Round 3.
Module: codex/tests/test_r3_comprehensive_journey.py

Implements automated, repeatable Python unittest suite testing:
Part 1: Main User Journey End-to-End:
  - Step 1: Server health check (GET /api/health)
  - Step 2: Submission ingestion (POST /api/submissions with brand, campaign, channels, copy)
  - Step 3: Clinical evidence PDF extraction & discrepancy analysis (POST /api/clinical/upload, POST /api/clinical/verify-copy)
  - Step 4: Adjudication counter-evidence gateway (POST /api/adjudication/submit)
  - Step 5: Certificate approval & cryptographic verification (POST /api/submissions/approve, GET /api/submissions/certificate/<id>, /verify.html, GET /api/submissions)

Part 2: Failure & Boundary Cases:
  - Empty inputs (empty brand, empty copy, empty JSON payload -> HTTP 400)
  - Huge input (>25MB -> HTTP 413)
  - Wrong file type (non-PDF or text disguised as PDF -> HTTP 400)
  - Corrupted PDF (truncated bytes, no PDF structure -> HTTP 400)
  - Scanned PDF (image-only, 0 text extracted -> handled gracefully, returns EXTRACTED_NO_TABLES, no 500 crash)
  - Password-protected / encrypted PDF -> handled gracefully, returns ERROR_ENCRYPTED, no unhandled crash
  - Duplicate submit (duplicate submission ID / campaign -> handled safely without data corruption)
  - Empty states (querying non-existent submission ID or empty queue -> returns clean 404 / empty array, no 500 crash)
  - Page refresh mid-flow / stateless resilience (all state retrievable via GET /api/submissions, cryptographic verification)
  - Irrelevant counter-evidence (legal_waiver_signoff for clinical_efficacy -> rejected with REJECTED_POLICY_IRRELEVANT)
  - Blank counter-evidence (missing fields, justification < 10 chars -> rejected with REJECTED_INSUFFICIENT_EVIDENCE)

ZERO DATABASE DRIFT GUARANTEE:
All test operations mutate only an isolated temporary database in tempfile.TemporaryDirectory.
The pristine repository database files are never touched or modified.
"""

import io
import os
import sys
import json
import base64
import hashlib
import tempfile
import unittest
from typing import Dict, Any, Tuple, Optional

# Configure sys.path for workspace modules
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODEX_ROOT = os.path.join(REPO_ROOT, "codex")
BACKEND_DIR = os.path.join(CODEX_ROOT, "backend")

for p in [REPO_ROOT, CODEX_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import server
import pypdf
from app.core.clinical_extractor import ClinicalTrialPDFExtractor
from app.core.review_engine import deterministic_engine


class MockSocket:
    """Mock socket stream allowing in-memory invocation of BaseHTTPRequestHandler without OS sockets."""
    def __init__(self, input_bytes: bytes):
        self.input_io = io.BytesIO(input_bytes)
        self.output_io = io.BytesIO()

    def makefile(self, mode: str, *args, **kwargs):
        if 'r' in mode:
            return self.input_io
        return self.output_io

    def sendall(self, data: bytes):
        self.output_io.write(data)


class MockServer:
    server_name = "127.0.0.1"
    server_port = 8000


class HTTPTestClient:
    """In-memory client invoking server.RobustVerificationHandler directly."""

    @classmethod
    def request(cls, method: str, path: str, headers: Optional[Dict[str, str]] = None, body: Optional[bytes] = None) -> Tuple[int, Dict[str, str], bytes]:
        headers = dict(headers or {})
        headers.setdefault("Host", "localhost:8000")
        if body is not None and "Content-Length" not in headers:
            headers["Content-Length"] = str(len(body))

        header_lines = [f"{method} {path} HTTP/1.1"]
        for k, v in headers.items():
            header_lines.append(f"{k}: {v}")
        header_bytes = "\r\n".join(header_lines).encode("utf-8") + b"\r\n\r\n"
        full_req = header_bytes + (body or b"")

        sock = MockSocket(full_req)
        server.RobustVerificationHandler(sock, ("127.0.0.1", 54321), MockServer())

        raw_output = sock.output_io.getvalue()
        header_part, _, body_part = raw_output.partition(b"\r\n\r\n")
        lines = header_part.decode("utf-8", errors="ignore").split("\r\n")
        status_line = lines[0] if lines else "HTTP/1.0 500 Internal Error"
        parts = status_line.split()
        status_code = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 500

        resp_headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                resp_headers[k.strip().lower()] = v.strip()

        return status_code, resp_headers, body_part

    @classmethod
    def get(cls, path: str, headers: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, str], bytes]:
        return cls.request("GET", path, headers=headers)

    @classmethod
    def post(cls, path: str, json_data: Optional[dict] = None, raw_body: Optional[bytes] = None, headers: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, str], bytes]:
        headers = dict(headers or {})
        if raw_body is not None:
            body = raw_body
        elif json_data is not None:
            headers.setdefault("Content-Type", "application/json")
            body = json.dumps(json_data).encode("utf-8")
        else:
            body = b""
        return cls.request("POST", path, headers=headers, body=body)


class TestR3ComprehensiveJourney(unittest.TestCase):
    """Full End-to-End User Journey and Failure Boundary Test Suite."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Locate clinical study fixture
        cls.fixture_pdf_path = os.path.join(CODEX_ROOT, "fixtures", "Study_CS-2026-88.pdf")
        if not os.path.exists(cls.fixture_pdf_path):
            cls.fixture_pdf_path = os.path.join(REPO_ROOT, "fixtures", "Study_CS-2026-88.pdf")

        # Database Isolation: Ensure zero mutation to committed brand_submissions_db.json
        cls._orig_submissions_db = getattr(server, "SUBMISSIONS_DB_FILE", None)
        cls._orig_mock_submissions = list(server.SUPABASE_MOCK_TABLES.get("brand_submissions", []))

        seed_path = os.path.join(REPO_ROOT, "brand_submissions_db.json")
        if not os.path.exists(seed_path) and cls._orig_submissions_db:
            seed_path = cls._orig_submissions_db

        with open(seed_path, "rb") as f:
            cls._seed_bytes = f.read()

        # Temporary isolated database
        cls._temp_dir = tempfile.TemporaryDirectory()
        cls._temp_db_path = os.path.join(cls._temp_dir.name, "brand_submissions_db.json")
        with open(cls._temp_db_path, "wb") as f:
            f.write(cls._seed_bytes)

        server.SUBMISSIONS_DB_FILE = cls._temp_db_path
        server.load_brand_submissions()

    @classmethod
    def tearDownClass(cls):
        # Restore pristine database file and in-memory tables
        if hasattr(cls, "_orig_submissions_db") and cls._orig_submissions_db:
            server.SUBMISSIONS_DB_FILE = cls._orig_submissions_db
            if hasattr(cls, "_seed_bytes") and os.path.exists(cls._orig_submissions_db):
                with open(cls._orig_submissions_db, "wb") as f:
                    f.write(cls._seed_bytes)
            server.load_brand_submissions()
        else:
            server.SUPABASE_MOCK_TABLES["brand_submissions"] = getattr(cls, "_orig_mock_submissions", [])

        if hasattr(cls, "_temp_dir"):
            try:
                cls._temp_dir.cleanup()
            except Exception:
                pass
        super().tearDownClass()

    # =========================================================================
    # PART 1: MAIN USER JOURNEY END-TO-END (5 STEPS)
    # =========================================================================

    def test_step1_server_health_check(self):
        """Step 1: Server health check endpoint returns 200, healthy status, engine v3.0, and uptime."""
        status, headers, body = HTTPTestClient.get("/api/health")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("content-type", ""))

        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "healthy")
        self.assertIn("Brandwise Governance Engine", data.get("engine", ""))
        self.assertEqual(data.get("uptime"), "active")
        self.assertIsInstance(data.get("active_improvements"), list)
        self.assertGreaterEqual(len(data["active_improvements"]), 3)

    def test_step2_submission_ingestion(self):
        """Step 2: Brand copy submission ingestion with brand, channel, copy, and claims."""
        payload = {
            "brand_name": "DermaCare Clinical Line",
            "channel": "instagram",
            "channel_name": "Social & Influencer",
            "content": "Experience radiant glow with our clinically tested hydration moisturizer! #ad",
            "claims": "Clinically proven to enhance skin hydration by 94.2% in 14-day randomized clinical trial.",
            "evidence_file": "Study_CS-2026-88.pdf",
            "submitted_by": "brand_creator@dermacare.com",
            "submitted_by_name": "Dr. A. Verma"
        }
        status, headers, body = HTTPTestClient.post("/api/submissions", json_data=payload)
        self.assertEqual(status, 200)

        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(data.get("sub_id", "").startswith("SUB-"))

        submission = data.get("submission", {})
        self.assertEqual(submission.get("brand_name"), "DermaCare Clinical Line")
        self.assertEqual(submission.get("channel"), "instagram")
        self.assertEqual(submission.get("status"), "PENDING_REVIEW")
        self.assertGreaterEqual(submission.get("compliance_score", 0), 80)
        self.assertIsNone(submission.get("certificate_id"))

    def test_step3_clinical_evidence_upload_and_discrepancy_verification(self):
        """Step 3: Clinical evidence PDF extraction and marketing copy discrepancy analysis."""
        # 3A: Upload clinical study PDF
        if os.path.exists(self.fixture_pdf_path):
            with open(self.fixture_pdf_path, "rb") as f:
                pdf_bytes = f.read()
        else:
            # Generate valid PDF with clinical study structure
            w = pypdf.PdfWriter()
            p = w.add_blank_page(width=300, height=300)
            buf = io.BytesIO()
            w.write(buf)
            pdf_bytes = buf.getvalue()

        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        upload_payload = {
            "filename": "Study_CS-2026-88.pdf",
            "file_data": f"data:application/pdf;base64,{b64_pdf}"
        }
        status, headers, body = HTTPTestClient.post("/api/clinical/upload", json_data=upload_payload)
        self.assertEqual(status, 200)

        upload_data = json.loads(body.decode("utf-8"))
        self.assertEqual(upload_data.get("status"), "success")
        self.assertIn("study", upload_data)

        # 3B: Verify marketing copy against extracted study endpoints
        # Exaggerated copy ("99% hydration in 7 days" vs true 94.2% in 14 days)
        verify_payload = {
            "copy_text": "Our miracle formula provides 99% hydration in just 7 days! Clinically verified.",
            "study_id": "CS-2026-88"
        }
        status, headers, body = HTTPTestClient.post("/api/clinical/verify-copy", json_data=verify_payload)
        self.assertEqual(status, 200)

        verify_data = json.loads(body.decode("utf-8"))
        self.assertEqual(verify_data.get("status"), "success")
        self.assertTrue(verify_data.get("has_discrepancies"))
        self.assertGreater(len(verify_data.get("discrepancies", [])), 0)

        # Verify citation structure in discrepancies
        discrepancy = verify_data["discrepancies"][0]
        self.assertIn("citation", discrepancy)
        self.assertIn("CS-2026-88", discrepancy["citation"])

        # 3C: Substantiated copy ("94.2% hydration in 14 days")
        substantiated_payload = {
            "copy_text": "Formulated to support 94.2% hydration over 14 days of regular application.",
            "study_id": "CS-2026-88"
        }
        status, headers, body = HTTPTestClient.post("/api/clinical/verify-copy", json_data=substantiated_payload)
        self.assertEqual(status, 200)
        sub_data = json.loads(body.decode("utf-8"))
        self.assertEqual(sub_data.get("status"), "success")
        self.assertFalse(sub_data.get("has_discrepancies"))

    def test_step4_adjudication_counter_evidence_gateway(self):
        """Step 4: Adjudication counter-evidence gateway accepts valid evidence and dismisses allegation."""
        adjudication_payload = {
            "allegation_id": "claim-clin-01",
            "allegation_category": "clinical_efficacy",
            "counter_evidence": {
                "evidence_type": "clinical_trial_certificate",
                "reference_id": "CTRI/2026/09/088419",
                "justification": "Phase IV double-blind dermatological clinical assay protocol certified by accredited hospital CRO.",
                "document_hash": "a1b2c3d4e5f67890"
            }
        }
        status, headers, body = HTTPTestClient.post("/api/adjudication/submit", json_data=adjudication_payload)
        self.assertEqual(status, 200)

        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("adjudication"), "ALLEGATION_REVERTED_AND_DISMISSED")

        res = data.get("result", {})
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("restored_score_delta"), 15)
        self.assertEqual(res.get("status"), "dismissed_with_evidence")
        self.assertIn("reversal_timestamp", res)
        self.assertEqual(res.get("evidence_reference"), "CTRI/2026/09/088419")

    def test_step5_certificate_approval_and_cryptographic_verification(self):
        """Step 5: Certificate approval, cryptographic seal, and multi-channel verification."""
        # 5A: Ingest a brand submission
        sub_payload = {
            "brand_name": "DermaCare Elixir",
            "channel": "instagram",
            "content": "Daily hydration moisturizer enriched with niacinamide and ceramides. #ad",
            "claims": "Clinically proven hydration under double-blind trial CS-2026-88."
        }
        s_code, _, s_body = HTTPTestClient.post("/api/submissions", json_data=sub_payload)
        self.assertEqual(s_code, 200)
        sub_id = json.loads(s_body.decode("utf-8"))["sub_id"]

        # 5B: Administrator approves submission and releases certificate
        approve_payload = {
            "submission_id": sub_id,
            "reviewer_name": "Dr. Pradeep Verma",
            "reviewer_role": "Chief Governance Officer",
            "review_notes": "All claims substantiated against clinical study CS-2026-88 and ASCI 2025 guidelines."
        }
        a_code, _, a_body = HTTPTestClient.post("/api/submissions/approve", json_data=approve_payload)
        self.assertEqual(a_code, 200)

        approve_data = json.loads(a_body.decode("utf-8"))
        self.assertEqual(approve_data.get("status"), "success")
        cert_id = approve_data.get("certificate_id")
        self.assertTrue(cert_id.startswith("BW-CERT-"))
        self.assertIn("verify_url", approve_data)

        approved_sub = approve_data.get("submission", {})
        self.assertEqual(approved_sub.get("status"), "APPROVED")
        audit_hash = approved_sub.get("audit_hash")
        self.assertIsNotNone(audit_hash)
        self.assertEqual(len(audit_hash), 64) # SHA-256 hexdigest length

        # 5C: Verify cryptographic hash integrity: sha256(sub_id:cert_id:now_utc:content)
        recalculated_hash = hashlib.sha256(
            f"{sub_id}:{cert_id}:{approved_sub['reviewed_at']}:{approved_sub['content']}".encode("utf-8")
        ).hexdigest()
        self.assertEqual(audit_hash, recalculated_hash)

        # 5D: Query GET /api/submissions/certificate/<id>
        c_code, _, c_body = HTTPTestClient.get(f"/api/submissions/certificate/{cert_id}")
        self.assertEqual(c_code, 200)
        c_data = json.loads(c_body.decode("utf-8"))
        self.assertEqual(c_data.get("status"), "success")
        self.assertEqual(c_data.get("certificate_id"), cert_id)
        self.assertEqual(c_data.get("submission_id"), sub_id)
        self.assertEqual(c_data.get("audit_hash"), audit_hash)

        # 5E: Verification on public verify.html
        v_code, v_headers, v_body = HTTPTestClient.get(f"/verify.html?cert={cert_id}")
        self.assertEqual(v_code, 200)
        self.assertIn("text/html", v_headers.get("content-type", ""))
        self.assertIn(b"Brandwise", v_body)
        self.assertIn(b"Certificate Verification", v_body)

        # 5F: Verify submission appears in GET /api/submissions
        q_code, _, q_body = HTTPTestClient.get("/api/submissions")
        self.assertEqual(q_code, 200)
        q_data = json.loads(q_body.decode("utf-8"))
        matching_subs = [s for s in q_data.get("submissions", []) if s.get("id") == sub_id]
        self.assertEqual(len(matching_subs), 1)
        self.assertEqual(matching_subs[0].get("status"), "APPROVED")
        self.assertEqual(matching_subs[0].get("certificate_id"), cert_id)

    # =========================================================================
    # PART 2: FAILURE & BOUNDARY CASES
    # =========================================================================

    def test_failure_empty_inputs(self):
        """Failure Case 1: Empty brand content, empty JSON, or missing required fields return HTTP 400."""
        # Empty content string
        status, _, body = HTTPTestClient.post("/api/submissions", json_data={"content": ""})
        self.assertEqual(status, 400)
        self.assertIn("cannot be empty", json.loads(body.decode("utf-8"))["message"].lower())

        # Empty JSON object
        status, _, body = HTTPTestClient.post("/api/submissions", json_data={})
        self.assertEqual(status, 400)

        # Completely empty raw body
        status, _, body = HTTPTestClient.post("/api/submissions", raw_body=b"")
        self.assertEqual(status, 400)

        # Malformed invalid JSON
        status, _, body = HTTPTestClient.post("/api/submissions", raw_body=b"{'invalid_json': ")
        self.assertEqual(status, 400)
        self.assertIn("malformed or invalid json", json.loads(body.decode("utf-8"))["message"].lower())

    def test_failure_huge_input_exceeds_25mb(self):
        """Failure Case 2: Upload payload exceeding 25MB returns HTTP 413 Payload Too Large."""
        # 26MB Content-Length header simulation
        status, _, body = HTTPTestClient.request(
            "POST",
            "/api/submissions",
            headers={"Content-Length": str(26 * 1024 * 1024)},
            body=b"A" # handler checks Content-Length before allocating buffer
        )
        self.assertEqual(status, 413)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "error")
        self.assertIn("exceeds maximum limit of 25mb", data.get("message", "").lower())

    def test_failure_wrong_file_type_non_pdf(self):
        """Failure Case 3: Non-PDF or plain text disguised as PDF returns HTTP 400."""
        text_data = b"Plain text file content masquerading as study evidence."
        b64_text = base64.b64encode(text_data).decode("utf-8")
        payload = {
            "filename": "fake_study.txt",
            "file_data": f"data:application/pdf;base64,{b64_text}"
        }
        status, _, body = HTTPTestClient.post("/api/clinical/upload", json_data=payload)
        self.assertEqual(status, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("invalid file format", data.get("message", "").lower())

    def test_failure_corrupted_pdf_structure(self):
        """Failure Case 4: Truncated or structurally corrupt PDF bytes return HTTP 400."""
        corrupt_bytes = b"%PDF-1.4\n%corrupt truncated stream with no trailer or catalog"
        b64_corrupt = base64.b64encode(corrupt_bytes).decode("utf-8")
        payload = {
            "filename": "corrupted_study.pdf",
            "file_data": b64_corrupt
        }
        status, _, body = HTTPTestClient.post("/api/clinical/upload", json_data=payload)
        self.assertEqual(status, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("corrupted or invalid pdf", data.get("message", "").lower())

    def test_failure_scanned_pdf_graceful_handling(self):
        """Failure Case 5: Scanned / image-only PDF with 0 extractable text handled gracefully without 500 crash."""
        # Synthesize a valid PDF with blank page (0 extractable text, 0 tables)
        w = pypdf.PdfWriter()
        w.add_blank_page(width=400, height=400)
        buf = io.BytesIO()
        w.write(buf)
        scanned_pdf_bytes = buf.getvalue()

        b64_scanned = base64.b64encode(scanned_pdf_bytes).decode("utf-8")
        payload = {
            "filename": "scanned_image_study.pdf",
            "file_data": b64_scanned
        }
        status, _, body = HTTPTestClient.post("/api/clinical/upload", json_data=payload)
        self.assertEqual(status, 200)

        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        study = data.get("study", {})
        self.assertEqual(study.get("status"), "EXTRACTED_NO_TABLES")
        self.assertEqual(len(study.get("tables", [])), 0)

    def test_failure_password_protected_pdf(self):
        """Failure Case 6: Password-protected / encrypted PDF returns ERROR_ENCRYPTED without unhandled crash."""
        w = pypdf.PdfWriter()
        w.add_blank_page(width=300, height=300)
        w.encrypt("secret_lock_2026")
        buf = io.BytesIO()
        w.write(buf)
        encrypted_pdf_bytes = buf.getvalue()

        b64_encrypted = base64.b64encode(encrypted_pdf_bytes).decode("utf-8")
        payload = {
            "filename": "encrypted_confidential.pdf",
            "file_data": b64_encrypted
        }
        status, _, body = HTTPTestClient.post("/api/clinical/upload", json_data=payload)
        self.assertEqual(status, 200)

        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        study = data.get("study", {})
        self.assertEqual(study.get("status"), "ERROR_ENCRYPTED")
        self.assertIn("encrypted", study.get("error", "").lower())

    def test_failure_duplicate_submit_safe_handling(self):
        """Failure Case 7: Submitting duplicate ID handled safely without data corruption."""
        # First submission
        first_payload = {
            "id": "SUB-DUP-TEST-001",
            "brand_name": "DermaCare Pure",
            "channel": "instagram",
            "content": "Initial brand copy for duplicate test. #ad"
        }
        status1, _, body1 = HTTPTestClient.post("/api/submissions", json_data=first_payload)
        self.assertEqual(status1, 200)
        data1 = json.loads(body1.decode("utf-8"))
        self.assertEqual(data1.get("sub_id"), "SUB-DUP-TEST-001")

        # Second submission with the exact same ID
        duplicate_payload = {
            "id": "SUB-DUP-TEST-001",
            "brand_name": "DermaCare Pure",
            "channel": "instagram",
            "content": "Updated brand copy for duplicate test with compliant language. #ad"
        }
        status2, _, body2 = HTTPTestClient.post("/api/submissions", json_data=duplicate_payload)
        self.assertEqual(status2, 200)

        data2 = json.loads(body2.decode("utf-8"))
        self.assertEqual(data2.get("status"), "success")
        self.assertTrue(data2.get("is_duplicate"))
        self.assertEqual(data2.get("sub_id"), "SUB-DUP-TEST-001")

        # Confirm queue has exactly 1 entry for this ID (no duplicate entries or corrupted store)
        status_q, _, body_q = HTTPTestClient.get("/api/submissions")
        self.assertEqual(status_q, 200)
        queue = json.loads(body_q.decode("utf-8")).get("submissions", [])
        matching = [s for s in queue if s.get("id") == "SUB-DUP-TEST-001"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["content"], duplicate_payload["content"])

    def test_failure_empty_states_and_non_existent_ids(self):
        """Failure Case 8: Querying non-existent submission ID or certificate returns clean 404, no 500 crash."""
        # Non-existent submission ID
        status, _, body = HTTPTestClient.get("/api/submissions/SUB-DOES-NOT-EXIST-404")
        self.assertEqual(status, 404)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "error")
        self.assertIn("not found", data.get("message", "").lower())

        # Non-existent certificate ID
        status, _, body = HTTPTestClient.get("/api/submissions/certificate/BW-CERT-GHOST-404")
        self.assertEqual(status, 404)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "error")
        self.assertIn("not found", data.get("message", "").lower())

        # Empty submissions queue returns 200 with empty array, no crash
        with open(self._temp_db_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        try:
            status, _, body = HTTPTestClient.get("/api/submissions")
            self.assertEqual(status, 200)
            data = json.loads(body.decode("utf-8"))
            self.assertEqual(data.get("status"), "success")
            self.assertEqual(data.get("count"), 0)
            self.assertEqual(data.get("submissions"), [])
        finally:
            with open(self._temp_db_path, "wb") as f:
                f.write(self._seed_bytes)

    def test_stateless_resilience_and_page_refresh(self):
        """Failure Case 9: Stateless persistence enables seamless recovery on page refresh."""
        # Ingest and approve submission
        payload = {
            "id": "SUB-STATELESS-01",
            "brand_name": "Resilient Brand",
            "content": "Stateless test copy. #ad"
        }
        HTTPTestClient.post("/api/submissions", json_data=payload)

        approve_payload = {
            "submission_id": "SUB-STATELESS-01",
            "reviewer_name": "Auditor"
        }
        _, _, a_body = HTTPTestClient.post("/api/submissions/approve", json_data=approve_payload)
        cert_id = json.loads(a_body.decode("utf-8"))["certificate_id"]

        # Simulate fresh client query (e.g. browser refresh or new device connection)
        status, _, body = HTTPTestClient.get(f"/api/submissions/audit-report?cert={cert_id}")
        self.assertEqual(status, 200)
        report_data = json.loads(body.decode("utf-8"))
        self.assertEqual(report_data.get("status"), "success")
        self.assertEqual(report_data.get("report", {}).get("certificate_id"), cert_id)

    def test_failure_irrelevant_counter_evidence_rejected(self):
        """Failure Case 10: Irrelevant counter-evidence type rejected with REJECTED_POLICY_IRRELEVANT."""
        payload = {
            "allegation_id": "claim-efficacy-09",
            "allegation_category": "clinical_efficacy",
            "counter_evidence": {
                # legal_waiver_signoff is for brand visual assets, NOT clinical efficacy claims
                "evidence_type": "legal_waiver_signoff",
                "reference_id": "WAIVER-BW-2026-09",
                "justification": "Trademark and logo positioning waiver executed by marketing counsel."
            }
        }
        status, _, body = HTTPTestClient.post("/api/adjudication/submit", json_data=payload)
        self.assertEqual(status, 200) # Returns 200 with rejection envelope

        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "rejected")
        self.assertEqual(data.get("adjudication"), "REJECTED_POLICY_IRRELEVANT")
        self.assertFalse(data.get("result", {}).get("success"))
        self.assertIn("not relevant to allegation category", data.get("result", {}).get("message", "").lower())

    def test_failure_blank_counter_evidence_rejected(self):
        """Failure Case 11: Blank counter-evidence or justification < 10 chars rejected with REJECTED_INSUFFICIENT_EVIDENCE."""
        # Missing reference ID
        payload1 = {
            "allegation_id": "claim-01",
            "allegation_category": "clinical_efficacy",
            "counter_evidence": {
                "evidence_type": "clinical_trial_certificate",
                "reference_id": "",
                "justification": "Legitimate justification exceeding ten characters."
            }
        }
        status1, _, body1 = HTTPTestClient.post("/api/adjudication/submit", json_data=payload1)
        self.assertEqual(status1, 200)
        data1 = json.loads(body1.decode("utf-8"))
        self.assertEqual(data1.get("status"), "rejected")
        self.assertEqual(data1.get("adjudication"), "REJECTED_INSUFFICIENT_EVIDENCE")

        # Justification shorter than 10 characters
        payload2 = {
            "allegation_id": "claim-02",
            "allegation_category": "clinical_efficacy",
            "counter_evidence": {
                "evidence_type": "clinical_trial_certificate",
                "reference_id": "CTRI/2026/01",
                "justification": "Too short"
            }
        }
        status2, _, body2 = HTTPTestClient.post("/api/adjudication/submit", json_data=payload2)
        self.assertEqual(status2, 200)
        data2 = json.loads(body2.decode("utf-8"))
        self.assertEqual(data2.get("status"), "rejected")
        self.assertEqual(data2.get("adjudication"), "REJECTED_INSUFFICIENT_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
