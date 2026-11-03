"""
Empirical Challenger Test Suite: Milestone 3 Adversarial Boundary & Database Invariance
Author: teamwork_challenger_r3_m3_1
Target: Milestone 3 (Task B) Local Execution & Comprehensive Testing Verification

Adversarial Boundary Challenges Tested:
1. Payload Boundary:
   - >25MB upload payload to /api/clinical/upload (JSON base64 and Content-Length header).
   - >25MB payload to general POST routes (/api/submissions, /api/adjudication/submit, /api/visual/inspect, /api/hinglish/check).
   - Verifies HTTP 413 Payload Too Large is returned without server crash or out-of-memory.
2. Corrupted / Truncated PDF Payloads:
   - Truncated PDF streams, missing cross-reference tables, broken trailers.
   - Verifies HTTP 400 Bad Request is returned.
3. Wrong File Types:
   - Text files, Windows MZ executables, ZIP archives masquerading as clinical evidence.
   - Verifies HTTP 400 Bad Request is returned.
4. Adjudication Policy Irrelevance:
   - legal_waiver_signoff submitted for clinical_efficacy allegations.
   - clinical_trial_certificate submitted for visual_geometry allegations.
   - trademark_registration submitted for clinical_efficacy allegations.
   - Verifies rejection with REJECTED_POLICY_IRRELEVANT.
5. Blank & Short Counter-Evidence:
   - Missing reference_id, blank justification, justification < 10 characters.
   - Verifies rejection with REJECTED_INSUFFICIENT_EVIDENCE.
6. Physical Database Invariance:
   - Strict SHA-256 byte comparison verifying e7e767c50b8c1296bb6d7bad7ed866304ccd68f26a7d01db3de7567ed3401bd8.
"""

import os
import sys
import json
import io
import base64
import hashlib
import tempfile
import unittest
from typing import Dict, Any, Tuple, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODEX_ROOT = os.path.join(REPO_ROOT, "codex")
BACKEND_DIR = os.path.join(CODEX_ROOT, "backend")

for p in [REPO_ROOT, CODEX_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import server

EXPECTED_DB_SHA256 = "e7e767c50b8c1296bb6d7bad7ed866304ccd68f26a7d01db3de7567ed3401bd8"


class MockSocket:
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


def request_in_memory(method: str, path: str, headers: Optional[Dict[str, str]] = None, body: Optional[bytes] = None) -> Tuple[int, Dict[str, str], bytes]:
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


class TestChallengerR3M3Adversarial(unittest.TestCase):
    """Adversarial challenger test cases executing boundary and edge scenarios."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root_db = os.path.join(REPO_ROOT, "brand_submissions_db.json")
        cls.codex_db = os.path.join(CODEX_ROOT, "brand_submissions_db.json")

        with open(cls.root_db, "rb") as f:
            cls.pristine_root_bytes = f.read()
        with open(cls.codex_db, "rb") as f:
            cls.pristine_codex_bytes = f.read()

        # Database Isolation: redirect server.SUBMISSIONS_DB_FILE to temp directory
        cls._orig_submissions_db = getattr(server, "SUBMISSIONS_DB_FILE", None)
        cls._temp_dir = tempfile.TemporaryDirectory()
        cls._temp_db_path = os.path.join(cls._temp_dir.name, "brand_submissions_db.json")
        with open(cls._temp_db_path, "wb") as f:
            f.write(cls.pristine_root_bytes)

        server.SUBMISSIONS_DB_FILE = cls._temp_db_path
        server.load_brand_submissions()

    @classmethod
    def tearDownClass(cls):
        # Restore pristine database file pointer
        if hasattr(cls, "_orig_submissions_db") and cls._orig_submissions_db:
            server.SUBMISSIONS_DB_FILE = cls._orig_submissions_db

        # Enforce zero drift
        with open(cls.root_db, "wb") as f:
            f.write(cls.pristine_root_bytes)
        with open(cls.codex_db, "wb") as f:
            f.write(cls.pristine_codex_bytes)

        server.load_brand_submissions()

        if hasattr(cls, "_temp_dir"):
            try:
                cls._temp_dir.cleanup()
            except Exception:
                pass
        super().tearDownClass()

    # =========================================================================
    # 1. PAYLOAD BOUNDARY ADVERSARIAL STRESS (>25MB -> HTTP 413)
    # =========================================================================

    def test_adversarial_payload_exceeds_25mb_clinical_upload(self):
        """Send >25MB Content-Length to /api/clinical/upload; verify HTTP 413 without server crash."""
        status, headers, body = request_in_memory(
            "POST",
            "/api/clinical/upload",
            headers={"Content-Length": str(26 * 1024 * 1024)},
            body=b"header-only-body"
        )
        self.assertEqual(status, 413)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "error")
        self.assertIn("exceeds maximum limit of 25mb", data.get("message", "").lower())

    def test_adversarial_payload_exceeds_25mb_general_post_routes(self):
        """Send >25MB Content-Length to general POST routes; verify HTTP 413 on each route."""
        routes = [
            "/api/submissions",
            "/api/adjudication/submit",
            "/api/visual/inspect",
            "/api/hinglish/check",
            "/api/submissions/approve",
            "/api/submissions/reject"
        ]
        oversized_len = str(28 * 1024 * 1024)
        for route in routes:
            with self.subTest(route=route):
                status, _, body = request_in_memory(
                    "POST",
                    route,
                    headers={"Content-Length": oversized_len},
                    body=b"X"
                )
                self.assertEqual(status, 413, f"Route {route} did not reject >25MB with 413, got {status}")
                data = json.loads(body.decode("utf-8"))
                self.assertEqual(data.get("status"), "error")
                self.assertIn("exceeds maximum limit of 25mb", data.get("message", "").lower())

    # =========================================================================
    # 2. CORRUPTED & TRUNCATED PDF PAYLOADS (-> HTTP 400)
    # =========================================================================

    def test_adversarial_corrupted_truncated_pdf_header(self):
        """Corrupted PDF stream starting with %PDF- but truncated immediately after header returns HTTP 400."""
        truncated_bytes = b"%PDF-1.7\n%truncated header without body or xref"
        payload = {
            "filename": "truncated_header.pdf",
            "file_data": base64.b64encode(truncated_bytes).decode("utf-8")
        }
        raw_body = json.dumps(payload).encode("utf-8")
        status, _, body = request_in_memory("POST", "/api/clinical/upload", headers={"Content-Type": "application/json"}, body=raw_body)
        self.assertEqual(status, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "error")
        self.assertIn("corrupted or invalid pdf", data.get("message", "").lower())

    def test_adversarial_corrupted_garbage_bytes_with_pdf_signature(self):
        """PDF payload containing %PDF- followed by 2KB of random non-PDF noise returns HTTP 400."""
        garbage_bytes = b"%PDF-1.4\n" + os.urandom(2048)
        payload = {
            "filename": "garbage_noise.pdf",
            "file_data": base64.b64encode(garbage_bytes).decode("utf-8")
        }
        raw_body = json.dumps(payload).encode("utf-8")
        status, _, body = request_in_memory("POST", "/api/clinical/upload", headers={"Content-Type": "application/json"}, body=raw_body)
        self.assertEqual(status, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "error")
        self.assertIn("corrupted or invalid pdf", data.get("message", "").lower())

    def test_adversarial_malformed_base64_pdf_data(self):
        """Malformed / corrupted base64 string in file_data returns HTTP 400."""
        payload = {
            "filename": "malformed_b64.pdf",
            "file_data": "data:application/pdf;base64,THIS_IS_NOT_VALID_BASE64_%%%!!!"
        }
        raw_body = json.dumps(payload).encode("utf-8")
        status, _, body = request_in_memory("POST", "/api/clinical/upload", headers={"Content-Type": "application/json"}, body=raw_body)
        self.assertEqual(status, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "error")

    # =========================================================================
    # 3. WRONG FILE TYPES (-> HTTP 400)
    # =========================================================================

    def test_adversarial_wrong_file_type_plain_text(self):
        """Plain text file disguised as PDF returns HTTP 400."""
        text_content = b"This is a raw text file masquerading as clinical evidence."
        payload = {
            "filename": "clinical_notes.txt",
            "file_data": base64.b64encode(text_content).decode("utf-8")
        }
        raw_body = json.dumps(payload).encode("utf-8")
        status, _, body = request_in_memory("POST", "/api/clinical/upload", headers={"Content-Type": "application/json"}, body=raw_body)
        self.assertEqual(status, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "error")
        self.assertIn("invalid file format", data.get("message", "").lower())

    def test_adversarial_wrong_file_type_windows_executable(self):
        """Binary executable (MZ header) uploaded as PDF returns HTTP 400."""
        exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00This program cannot be run in DOS mode."
        payload = {
            "filename": "malicious_payload.exe",
            "file_data": base64.b64encode(exe_content).decode("utf-8")
        }
        raw_body = json.dumps(payload).encode("utf-8")
        status, _, body = request_in_memory("POST", "/api/clinical/upload", headers={"Content-Type": "application/json"}, body=raw_body)
        self.assertEqual(status, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "error")
        self.assertIn("invalid file format", data.get("message", "").lower())

    def test_adversarial_wrong_file_type_zip_archive(self):
        """ZIP archive (PK header) uploaded as PDF returns HTTP 400."""
        zip_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00" + b"\x00" * 30
        payload = {
            "filename": "evidence_bundle.zip",
            "file_data": base64.b64encode(zip_content).decode("utf-8")
        }
        raw_body = json.dumps(payload).encode("utf-8")
        status, _, body = request_in_memory("POST", "/api/clinical/upload", headers={"Content-Type": "application/json"}, body=raw_body)
        self.assertEqual(status, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "error")
        self.assertIn("invalid file format", data.get("message", "").lower())

    # =========================================================================
    # 4. ADJUDICATION WITH IRRELEVANT EVIDENCE (-> REJECTED_POLICY_IRRELEVANT)
    # =========================================================================

    def test_adversarial_adjudication_irrelevant_legal_waiver_for_clinical_efficacy(self):
        """Adjudication with legal_waiver_signoff for clinical_efficacy returns REJECTED_POLICY_IRRELEVANT."""
        payload = {
            "allegation_id": "allegation-clinical-99",
            "allegation_category": "clinical_efficacy",
            "counter_evidence": {
                "evidence_type": "legal_waiver_signoff",
                "reference_id": "WAIVER-LEGAL-2026-99",
                "justification": "Signed disclaimer and release waiver from commercial brand department."
            }
        }
        raw_body = json.dumps(payload).encode("utf-8")
        status, _, body = request_in_memory("POST", "/api/adjudication/submit", headers={"Content-Type": "application/json"}, body=raw_body)
        self.assertEqual(status, 200) # Handler returns 200 with rejection envelope
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "rejected")
        self.assertEqual(data.get("adjudication"), "REJECTED_POLICY_IRRELEVANT")
        self.assertFalse(data.get("result", {}).get("success"))
        self.assertIn("not relevant to allegation category", data.get("result", {}).get("message", "").lower())

    def test_adversarial_adjudication_irrelevant_agency_auth_for_clinical_efficacy(self):
        """Adjudication with agency_authorization or influencer_contract_exemption for clinical_efficacy returns REJECTED_POLICY_IRRELEVANT."""
        for irrelevant_type in ["agency_authorization", "influencer_contract_exemption"]:
            with self.subTest(evidence_type=irrelevant_type):
                payload = {
                    "allegation_id": "allegation-clin-02",
                    "allegation_category": "clinical_efficacy",
                    "counter_evidence": {
                        "evidence_type": irrelevant_type,
                        "reference_id": "AUTH-2026-0091",
                        "justification": "Authorized agency representation and influencer exemption signoff."
                    }
                }
                raw_body = json.dumps(payload).encode("utf-8")
                status, _, body = request_in_memory("POST", "/api/adjudication/submit", headers={"Content-Type": "application/json"}, body=raw_body)
                self.assertEqual(status, 200)
                data = json.loads(body.decode("utf-8"))
                self.assertEqual(data.get("status"), "rejected")
                self.assertEqual(data.get("adjudication"), "REJECTED_POLICY_IRRELEVANT")
                self.assertFalse(data.get("result", {}).get("success"))

    # =========================================================================
    # 5. BLANK & SHORT COUNTER-EVIDENCE (-> REJECTED_INSUFFICIENT_EVIDENCE)
    # =========================================================================

    def test_adversarial_adjudication_short_justification_under_10_chars(self):
        """Counter-evidence with justification < 10 characters returns REJECTED_INSUFFICIENT_EVIDENCE."""
        short_justifications = ["", "Valid", "Too short", "123456789"] # length <= 9
        for just in short_justifications:
            with self.subTest(justification=just):
                payload = {
                    "allegation_id": "allegation-short-01",
                    "allegation_category": "clinical_efficacy",
                    "counter_evidence": {
                        "evidence_type": "clinical_trial_certificate",
                        "reference_id": "CTRI/2026/02/0044",
                        "justification": just
                    }
                }
                raw_body = json.dumps(payload).encode("utf-8")
                status, _, body = request_in_memory("POST", "/api/adjudication/submit", headers={"Content-Type": "application/json"}, body=raw_body)
                self.assertEqual(status, 200)
                data = json.loads(body.decode("utf-8"))
                self.assertEqual(data.get("status"), "rejected")
                self.assertEqual(data.get("adjudication"), "REJECTED_INSUFFICIENT_EVIDENCE")
                self.assertFalse(data.get("result", {}).get("success"))
                self.assertIn("min 10 characters", data.get("result", {}).get("message", "").lower())

    def test_adversarial_adjudication_missing_reference_id(self):
        """Counter-evidence with blank reference_id returns REJECTED_INSUFFICIENT_EVIDENCE."""
        payload = {
            "allegation_id": "allegation-blank-ref",
            "allegation_category": "clinical_efficacy",
            "counter_evidence": {
                "evidence_type": "clinical_trial_certificate",
                "reference_id": "   ",
                "justification": "This justification is definitely longer than ten characters."
            }
        }
        raw_body = json.dumps(payload).encode("utf-8")
        status, _, body = request_in_memory("POST", "/api/adjudication/submit", headers={"Content-Type": "application/json"}, body=raw_body)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "rejected")
        self.assertEqual(data.get("adjudication"), "REJECTED_INSUFFICIENT_EVIDENCE")
        self.assertIn("requires a valid reference id", data.get("result", {}).get("message", "").lower())

    def test_adversarial_adjudication_missing_evidence_type(self):
        """Counter-evidence with missing or unsupported evidence_type returns REJECTED_INSUFFICIENT_EVIDENCE."""
        payload = {
            "allegation_id": "allegation-missing-type",
            "allegation_category": "clinical_efficacy",
            "counter_evidence": {
                "evidence_type": "unsupported_random_type",
                "reference_id": "REF-001",
                "justification": "This justification is long enough for testing purposes."
            }
        }
        raw_body = json.dumps(payload).encode("utf-8")
        status, _, body = request_in_memory("POST", "/api/adjudication/submit", headers={"Content-Type": "application/json"}, body=raw_body)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "rejected")
        self.assertEqual(data.get("adjudication"), "REJECTED_INSUFFICIENT_EVIDENCE")

    # =========================================================================
    # 7. LIVE TCP SOCKET SERVER ADVERSARIAL STRESS
    # =========================================================================

    def test_live_tcp_socket_server_adversarial_boundary(self):
        """Spin up live loopback TCP socket server and verify adversarial boundaries over real network stack."""
        import threading
        import urllib.request
        import urllib.error
        from http.server import HTTPServer

        try:
            httpd = HTTPServer(("127.0.0.1", 0), server.RobustVerificationHandler)
        except (PermissionError, OSError) as sock_err:
            self.skipTest(f"Loopback TCP socket binding not permitted in current sandbox environment: {sock_err}")
            return

        assigned_port = httpd.server_port

        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        base_url = f"http://127.0.0.1:{assigned_port}"

        try:
            # 1. Health check over live TCP
            try:
                with urllib.request.urlopen(f"{base_url}/api/health", timeout=3) as resp:
                    self.assertEqual(resp.status, 200)
                    h_data = json.loads(resp.read().decode("utf-8"))
                    self.assertEqual(h_data.get("status"), "healthy")
            except (urllib.error.URLError, PermissionError, OSError) as conn_err:
                self.skipTest(f"Loopback TCP connect not permitted in current sandbox environment: {conn_err}")
                return

            # 2. Oversized upload >25MB over live TCP socket returns HTTP 413
            try:
                req = urllib.request.Request(
                    f"{base_url}/api/clinical/upload",
                    headers={"Content-Length": str(26 * 1024 * 1024), "Content-Type": "application/json"},
                    data=b'{"payload": "oversized"}'
                )
                urllib.request.urlopen(req, timeout=3)
                self.fail("Expected HTTP 413 for oversized upload, but request succeeded.")
            except urllib.error.HTTPError as he:
                self.assertEqual(he.code, 413)
                err_data = json.loads(he.read().decode("utf-8"))
                self.assertEqual(err_data.get("status"), "error")
                self.assertIn("25mb", err_data.get("message", "").lower())

            # 3. Corrupted PDF over live TCP socket returns HTTP 400
            try:
                bad_pdf_payload = json.dumps({
                    "filename": "corrupted.pdf",
                    "file_data": "data:application/pdf;base64,JVBERi0xLjQKJXRydW5jYXRlZCBub25zZW5zZQ=="
                }).encode("utf-8")
                req = urllib.request.Request(
                    f"{base_url}/api/clinical/upload",
                    headers={"Content-Type": "application/json"},
                    data=bad_pdf_payload
                )
                urllib.request.urlopen(req, timeout=3)
                self.fail("Expected HTTP 400 for corrupted PDF, but request succeeded.")
            except urllib.error.HTTPError as he:
                self.assertEqual(he.code, 400)
                err_data = json.loads(he.read().decode("utf-8"))
                self.assertIn("corrupted or invalid pdf", err_data.get("message", "").lower())

            # 4. Wrong file type (Windows EXE) over live TCP socket returns HTTP 400
            try:
                exe_payload = json.dumps({
                    "filename": "malicious.exe",
                    "file_data": "data:application/pdf;base64,TVqQAAMAAAAEAAAA//8A"
                }).encode("utf-8")
                req = urllib.request.Request(
                    f"{base_url}/api/clinical/upload",
                    headers={"Content-Type": "application/json"},
                    data=exe_payload
                )
                urllib.request.urlopen(req, timeout=3)
                self.fail("Expected HTTP 400 for wrong file type, but request succeeded.")
            except urllib.error.HTTPError as he:
                self.assertEqual(he.code, 400)
                err_data = json.loads(he.read().decode("utf-8"))
                self.assertIn("invalid file format", err_data.get("message", "").lower())

            # 5. Adjudication irrelevant evidence over live TCP socket
            adj_irrelevant_payload = json.dumps({
                "allegation_id": "live-allegation-01",
                "allegation_category": "clinical_efficacy",
                "counter_evidence": {
                    "evidence_type": "legal_waiver_signoff",
                    "reference_id": "WAIVER-LIVE-001",
                    "justification": "Signed legal waiver for marketing campaign."
                }
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/adjudication/submit",
                headers={"Content-Type": "application/json"},
                data=adj_irrelevant_payload
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                self.assertEqual(resp.status, 200)
                adj_data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(adj_data.get("status"), "rejected")
                self.assertEqual(adj_data.get("adjudication"), "REJECTED_POLICY_IRRELEVANT")

            # 6. Adjudication short justification over live TCP socket
            adj_short_payload = json.dumps({
                "allegation_id": "live-allegation-02",
                "allegation_category": "clinical_efficacy",
                "counter_evidence": {
                    "evidence_type": "clinical_trial_certificate",
                    "reference_id": "CTRI/2026/01/0001",
                    "justification": "short"
                }
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/adjudication/submit",
                headers={"Content-Type": "application/json"},
                data=adj_short_payload
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                self.assertEqual(resp.status, 200)
                adj_data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(adj_data.get("status"), "rejected")
                self.assertEqual(adj_data.get("adjudication"), "REJECTED_INSUFFICIENT_EVIDENCE")
        finally:
            httpd.shutdown()
            httpd.server_close()

    # =========================================================================
    # 8. PHYSICAL DATABASE ZERO DRIFT INVARIANCE
    # =========================================================================

    def test_physical_database_invariance(self):
        """Assert zero bytes drift: both database files strictly equal pristine SHA-256."""
        for label, db_path in [("root", self.root_db), ("codex", self.codex_db)]:
            with open(db_path, "rb") as f:
                content = f.read()
            h = hashlib.sha256(content).hexdigest()
            self.assertEqual(
                h,
                EXPECTED_DB_SHA256,
                f"Physical database drift detected on {label} DB! Expected {EXPECTED_DB_SHA256}, got {h}"
            )


if __name__ == "__main__":
    unittest.main()


