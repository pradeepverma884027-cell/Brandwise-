"""
Unit and integration tests for Clinical Evidence REST API endpoints in Brandwise server.py.

Tests:
1. GET /api/clinical/studies -> returns 200, status="success", and studies list with CS-2026-88 and LAB-AYUSH-904
2. POST /api/clinical/upload -> uploads synthetic/fixture PDF, extracts endpoints, saves file, and updates catalog
3. POST /api/clinical/upload -> handles data URL schema, multipart/form-data, and rejects empty/corrupt files
4. POST /api/clinical/verify-copy -> evaluates copy ("99% hydration in 7 days") and returns discrepancies with citations
5. POST /api/clinical/verify-copy -> validates substantiated copy and target study filtering
6. GET /api/clinical/sample-pdf -> streams binary PDF fixture with Content-Type: application/pdf and %PDF- header
7. POST /api/submissions -> evaluates submissions with clinical evidence checks, attaches findings and adjusts compliance score
"""

import io
import os
import sys
import json
import base64
import unittest
from typing import Dict, Any, Tuple

# Configure paths
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODEX_ROOT = os.path.join(REPO_ROOT, "codex")
BACKEND_DIR = os.path.join(CODEX_ROOT, "backend")

for p in [REPO_ROOT, CODEX_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import server


class MockSocket:
    """Mock socket stream allowing in-memory testing of BaseHTTPRequestHandler without OS sockets."""
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
    def request(cls, method: str, path: str, headers: Dict[str, str] = None, body: bytes = None) -> Tuple[int, Dict[str, str], bytes]:
        headers = dict(headers or {})
        headers.setdefault("Host", "localhost:8000")
        if body is not None:
            headers["Content-Length"] = str(len(body))

        header_lines = [f"{method} {path} HTTP/1.1"]
        for k, v in headers.items():
            header_lines.append(f"{k}: {v}")
        header_bytes = "\r\n".join(header_lines).encode("utf-8") + b"\r\n\r\n"
        full_req = header_bytes + (body or b"")

        sock = MockSocket(full_req)
        # Process request through server handler
        handler = server.RobustVerificationHandler(sock, ("127.0.0.1", 54321), MockServer())

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
    def get(cls, path: str, headers: Dict[str, str] = None) -> Tuple[int, Dict[str, str], bytes]:
        return cls.request("GET", path, headers=headers)

    @classmethod
    def post(cls, path: str, json_data: dict = None, raw_body: bytes = None, headers: Dict[str, str] = None) -> Tuple[int, Dict[str, str], bytes]:
        headers = dict(headers or {})
        if raw_body is not None:
            body = raw_body
        elif json_data is not None:
            headers.setdefault("Content-Type", "application/json")
            body = json.dumps(json_data).encode("utf-8")
        else:
            body = b""
        return cls.request("POST", path, headers=headers, body=body)


class TestClinicalAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Locate sample PDF fixture
        cls.sample_pdf_path = os.path.join(CODEX_ROOT, "fixtures", "Study_CS-2026-88.pdf")
        if not os.path.exists(cls.sample_pdf_path):
            cls.sample_pdf_path = os.path.join(REPO_ROOT, "fixtures", "Study_CS-2026-88.pdf")

    # -------------------------------------------------------------------------
    # 1. GET /api/clinical/studies
    # -------------------------------------------------------------------------
    def test_get_clinical_studies_success(self):
        """GET /api/clinical/studies returns 200, status=success, and active studies."""
        status, headers, body = HTTPTestClient.get("/api/clinical/studies")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertIn("studies", data)
        studies = data["studies"]
        self.assertIsInstance(studies, list)
        self.assertGreaterEqual(len(studies), 2)

        study_ids = [s.get("study_id") for s in studies]
        self.assertIn("CS-2026-88", study_ids)
        self.assertIn("LAB-AYUSH-904", study_ids)

        # Check endpoints inside CS-2026-88
        cs88 = next(s for s in studies if s.get("study_id") == "CS-2026-88")
        endpoints = cs88.get("endpoints", {})
        self.assertIn("hydration_increase_percent", endpoints)
        hyd_val = endpoints["hydration_increase_percent"]
        if isinstance(hyd_val, dict):
            hyd_val = hyd_val.get("value")
        self.assertAlmostEqual(float(hyd_val), 94.2, places=1)

    def test_get_clinical_studies_codex_prefix_routing(self):
        """GET /codex/api/clinical/studies also routes successfully via clean_path."""
        status, headers, body = HTTPTestClient.get("/codex/api/clinical/studies")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertGreaterEqual(len(data.get("studies", [])), 2)

    # -------------------------------------------------------------------------
    # 2. POST /api/clinical/upload
    # -------------------------------------------------------------------------
    def test_post_clinical_upload_base64_json(self):
        """POST /api/clinical/upload accepts base64 JSON, extracts study, and saves file."""
        self.assertTrue(os.path.exists(self.sample_pdf_path), f"Sample PDF missing: {self.sample_pdf_path}")
        with open(self.sample_pdf_path, "rb") as f:
            pdf_bytes = f.read()

        b64_str = base64.b64encode(pdf_bytes).decode("utf-8")
        test_filename = "test_upload_cs2026_88.pdf"

        status, headers, body = HTTPTestClient.post(
            "/api/clinical/upload",
            json_data={
                "filename": test_filename,
                "file_data": b64_str
            }
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertIn("study", data)
        study = data["study"]
        self.assertEqual(study.get("study_id"), "CS-2026-88")
        self.assertIn("hydration_increase_percent", study.get("endpoints", {}))

        # Check file was saved in codex/uploads/clinical_evidence/
        expected_saved = os.path.join(CODEX_ROOT, "uploads", "clinical_evidence", test_filename)
        self.assertTrue(os.path.exists(expected_saved))

    def test_post_clinical_upload_data_url_prefix(self):
        """POST /api/clinical/upload correctly parses data:application/pdf;base64,... URIs."""
        with open(self.sample_pdf_path, "rb") as f:
            pdf_bytes = f.read()

        b64_str = "data:application/pdf;base64," + base64.b64encode(pdf_bytes).decode("utf-8")
        status, headers, body = HTTPTestClient.post(
            "/api/clinical/upload",
            json_data={
                "filename": "data_uri_study.pdf",
                "file_data": b64_str
            }
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data["study"].get("study_id"), "CS-2026-88")

    def test_post_clinical_upload_multipart_form(self):
        """POST /api/clinical/upload correctly parses multipart/form-data payload."""
        with open(self.sample_pdf_path, "rb") as f:
            pdf_bytes = f.read()

        boundary = "---------------------------BoundaryX99Test"
        multipart_body = (
            f"--{boundary}\r\n".encode("utf-8")
            + b'Content-Disposition: form-data; name="file"; filename="multipart_study.pdf"\r\n'
            + b'Content-Type: application/pdf\r\n\r\n'
            + pdf_bytes
            + b"\r\n"
            + f"--{boundary}--\r\n".encode("utf-8")
        )

        status, headers, body = HTTPTestClient.post(
            "/api/clinical/upload",
            raw_body=multipart_body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data["study"].get("study_id"), "CS-2026-88")

    def test_post_clinical_upload_empty_or_corrupt_fails(self):
        """POST /api/clinical/upload cleanly rejects empty or corrupt file payloads."""
        # Empty file_data
        status, _, body = HTTPTestClient.post(
            "/api/clinical/upload",
            json_data={"filename": "empty.pdf", "file_data": ""}
        )
        self.assertEqual(status, 400)

        # Corrupt non-PDF bytes
        corrupt_b64 = base64.b64encode(b"NOT_A_REAL_PDF_CORRUPT").decode("utf-8")
        status, _, body = HTTPTestClient.post(
            "/api/clinical/upload",
            json_data={"filename": "corrupt.pdf", "file_data": corrupt_b64}
        )
        self.assertEqual(status, 400)

    # -------------------------------------------------------------------------
    # 3. POST /api/clinical/verify-copy
    # -------------------------------------------------------------------------
    def test_post_clinical_verify_copy_discrepancy_detection(self):
        """POST /api/clinical/verify-copy detects over-claim and timeline compression with citations."""
        copy_text = "Experience our breakthrough serum: delivers 99% hydration in 7 days!"
        status, headers, body = HTTPTestClient.post(
            "/api/clinical/verify-copy",
            json_data={"copy_text": copy_text}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(data.get("has_discrepancies"))

        discrepancies = data.get("discrepancies", [])
        self.assertGreaterEqual(len(discrepancies), 2)

        # Find over-claim (statistical exaggeration)
        over_claim = next((d for d in discrepancies if d.get("type") in ("over_claim", "statistical_exaggeration")), None)
        self.assertIsNotNone(over_claim)
        self.assertIn("99", str(over_claim.get("claimed_value")))
        self.assertIn("94.2", str(over_claim.get("trial_value")))
        self.assertIn("Table 2.1", over_claim.get("citation", ""))

        # Find timeline compression
        timeline = next((d for d in discrepancies if d.get("type") == "timeline_compression"), None)
        self.assertIsNotNone(timeline)
        self.assertIn("7 days", str(timeline.get("claimed_value")))
        self.assertIn("14 days", str(timeline.get("trial_value")))

    def test_post_clinical_verify_copy_substantiated(self):
        """POST /api/clinical/verify-copy approves substantiated compliant copy."""
        compliant_copy = "Clinical study observed 94.2% skin hydration increase over 14 days."
        status, headers, body = HTTPTestClient.post(
            "/api/clinical/verify-copy",
            json_data={"copy_text": compliant_copy}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertFalse(data.get("has_discrepancies"))

        verified_claims = data.get("verified_claims", [])
        self.assertGreaterEqual(len(verified_claims), 1)
        self.assertEqual(verified_claims[0].get("status"), "SUBSTANTIATED")
        self.assertIn("Table 2.1", verified_claims[0].get("citation", ""))

    def test_post_clinical_verify_copy_with_specific_study_filter(self):
        """POST /api/clinical/verify-copy filters by target study_id."""
        ayush_copy = "Dermatological patch test confirms 89.4% soothing efficacy over 7 days."
        status, headers, body = HTTPTestClient.post(
            "/api/clinical/verify-copy",
            json_data={
                "copy_text": ayush_copy,
                "study_id": "LAB-AYUSH-904"
            }
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertFalse(data.get("has_discrepancies"))
        self.assertEqual(data.get("primary_study", {}).get("study_id"), "LAB-AYUSH-904")

    # -------------------------------------------------------------------------
    # 4. GET /api/clinical/sample-pdf
    # -------------------------------------------------------------------------
    def test_get_clinical_sample_pdf_stream(self):
        """GET /api/clinical/sample-pdf returns binary PDF stream with proper headers."""
        status, headers, body = HTTPTestClient.get("/api/clinical/sample-pdf")
        self.assertEqual(status, 200)

        # Check content-type header
        content_type = headers.get("content-type")
        self.assertIn("application/pdf", content_type)

        # Check content-disposition header
        content_disp = headers.get("content-disposition")
        self.assertIn("Study_CS-2026-88.pdf", content_disp)

        # Check valid PDF binary header
        self.assertTrue(body.startswith(b"%PDF-"), "Stream does not start with %PDF- header")
        self.assertGreater(len(body), 5000, "PDF stream unexpectedly small")

    # -------------------------------------------------------------------------
    # 5. POST /api/submissions Clinical Integration
    # -------------------------------------------------------------------------
    def test_post_submissions_includes_clinical_evidence_findings(self):
        """POST /api/submissions runs clinical check and includes findings + adjusted score."""
        submission_payload = {
            "brand_name": "DermaCare Clinical Hydrate",
            "channel": "instagram",
            "channel_name": "Instagram Caption",
            "content": "Guaranteed 99% hydration boost in 7 days! Clinically verified. #ad",
            "claims": "Clinical Study CS-2026-88 protocol",
            "submitted_by": "creator@dermacare.com",
            "submitted_by_name": "Sarah Jenkins"
        }

        status, headers, body = HTTPTestClient.post("/api/submissions", json_data=submission_payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")

        sub = data.get("submission", {})
        self.assertTrue(sub.get("has_clinical_discrepancies"))
        self.assertGreater(sub.get("clinical_discrepancies_count"), 0)

        findings = sub.get("findings", [])
        self.assertGreaterEqual(len(findings), 2)

        # Verify finding structure
        for f in findings:
            self.assertEqual(f.get("category"), "claim")
            self.assertEqual(f.get("rule_id"), "CLINICAL-EVIDENCE-01")
            self.assertIn("CS-2026-88", f.get("source_ref", ""))

        # Compliance score must be penalized due to discrepancies
        self.assertLess(sub.get("compliance_score"), 90)

    def test_post_submissions_compliant_copy_high_score(self):
        """POST /api/submissions with compliant copy has no findings and high score."""
        submission_payload = {
            "brand_name": "DermaCare Compliant Serum",
            "channel": "instagram",
            "channel_name": "Instagram Caption",
            "content": "Observed 94.2% hydration increase over 14 days in clinical trials. #ad #skincare",
            "claims": "Clinical Study CS-2026-88",
            "submitted_by": "creator@dermacare.com",
            "submitted_by_name": "Sarah Jenkins"
        }

        status, headers, body = HTTPTestClient.post("/api/submissions", json_data=submission_payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")

        sub = data.get("submission", {})
        self.assertFalse(sub.get("has_clinical_discrepancies"))
        self.assertEqual(sub.get("clinical_discrepancies_count"), 0)
        self.assertEqual(len(sub.get("findings", [])), 0)
        self.assertGreaterEqual(sub.get("compliance_score"), 90)


if __name__ == "__main__":
    unittest.main(verbosity=2)
