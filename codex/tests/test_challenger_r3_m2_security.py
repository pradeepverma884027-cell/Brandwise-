"""
Empirical Challenger Test Suite: Path Traversal, Upload Limits & Security Hardening
Author: teamwork_challenger_r3_m2_1
Target: Milestone 2 (Task C) Verification & Adversarial Stress Testing
"""

import base64
import hashlib
import io
import json
import os
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server


class MockSocket:
    """In-memory mock socket providing stream IO for sandboxed HTTP handler execution."""

    def __init__(self, request_bytes: bytes):
        self.rfile = io.BytesIO(request_bytes)
        self.output = io.BytesIO()

    def makefile(self, mode: str, *args, **kwargs):
        if 'r' in mode:
            return self.rfile
        return self.output

    def sendall(self, b: bytes):
        self.output.write(b)


class DummyServer:
    server_port = 8000
    server_name = '127.0.0.1'


def execute_http_request(raw_request: bytes) -> tuple[int, dict, str]:
    """Execute raw HTTP request through RobustVerificationHandler in memory."""
    mock_sock = MockSocket(raw_request)
    server.RobustVerificationHandler(mock_sock, ('127.0.0.1', 12345), DummyServer())
    raw_response = mock_sock.output.getvalue().decode('utf-8', errors='replace')

    lines = raw_response.split('\r\n')
    status_line = lines[0] if lines else ''
    status_code = int(status_line.split()[1]) if len(status_line.split()) > 1 else -1

    headers = {}
    idx = 1
    while idx < len(lines) and lines[idx]:
        if ':' in lines[idx]:
            k, v = lines[idx].split(':', 1)
            headers[k.strip().lower()] = v.strip()
        idx += 1

    body = '\r\n'.join(lines[idx + 1:]) if idx < len(lines) else ''
    return status_code, headers, body


def execute_get(path: str) -> tuple[int, dict, str]:
    req = f'GET {path} HTTP/1.1\r\nHost: localhost\r\n\r\n'.encode('utf-8')
    return execute_http_request(req)


def execute_post(path: str, body_bytes: bytes, content_type: str = 'application/json') -> tuple[int, dict, str]:
    req = (
        f'POST {path} HTTP/1.1\r\n'
        f'Host: localhost\r\n'
        f'Content-Type: {content_type}\r\n'
        f'Content-Length: {len(body_bytes)}\r\n\r\n'
    ).encode('utf-8') + body_bytes
    return execute_http_request(req)


class SecurityBaseTestCase(unittest.TestCase):
    """Base test case managing database state preservation and rollback."""

    @classmethod
    def setUpClass(cls):
        cls.db_paths = [
            os.path.join(REPO_ROOT, 'brand_submissions_db.json'),
            os.path.join(REPO_ROOT, 'codex', 'brand_submissions_db.json'),
            os.path.join(REPO_ROOT, 'supabase_users_db.json'),
            os.path.join(REPO_ROOT, 'codex', 'supabase_users_db.json'),
        ]
        cls.snapshots = {}
        for p in cls.db_paths:
            if os.path.exists(p):
                with open(p, 'rb') as f:
                    cls.snapshots[p] = f.read()

    def tearDown(self):
        for p, data in self.snapshots.items():
            try:
                with open(p, 'wb') as f:
                    f.write(data)
            except Exception:
                pass
        # Reload databases into memory to ensure mock tables match disk
        try:
            server.load_brand_submissions()
            server.load_supabase_users()
        except Exception:
            pass


class TestPathTraversalAdversarial(SecurityBaseTestCase):
    """Empirical challenge 1: Path Traversal prevention on static asset resolution."""

    def test_path_traversal_supabase_users_db(self):
        """Verify /../supabase_users_db.json is blocked and does NOT leak credentials."""
        status, headers, body = execute_get('/../supabase_users_db.json')
        self.assertIn(status, [403, 404], f"Expected 403 or 404, got {status}")
        self.assertNotIn("usr_admin_001", body)
        self.assertNotIn("password_hash", body)

    def test_path_traversal_windows_win_ini(self):
        """Verify /../../windows/win.ini is blocked and does NOT leak OS files."""
        status, headers, body = execute_get('/../../windows/win.ini')
        self.assertIn(status, [403, 404], f"Expected 403 or 404, got {status}")
        self.assertNotIn("[fonts]", body.lower())
        self.assertNotIn("[extensions]", body.lower())

    def test_path_traversal_percent_encoded_dot_dot(self):
        """Verify /%2e%2e/ URL-encoded traversal is safely blocked."""
        status, headers, body = execute_get('/%2e%2e/')
        self.assertIn(status, [403, 404], f"Expected 403 or 404, got {status}")
        self.assertNotIn("usr_admin_001", body)

    def test_path_traversal_percent_encoded_db_file(self):
        """Verify /%2e%2e/supabase_users_db.json is blocked."""
        status, headers, body = execute_get('/%2e%2e/supabase_users_db.json')
        self.assertIn(status, [403, 404], f"Expected 403 or 404, got {status}")
        self.assertNotIn("usr_admin_001", body)

    def test_path_traversal_windows_backslashes(self):
        """Verify /..\\..\\supabase_users_db.json backslash traversal is blocked."""
        status, headers, body = execute_get('/..\\..\\supabase_users_db.json')
        self.assertIn(status, [403, 404], f"Expected 403 or 404, got {status}")
        self.assertNotIn("usr_admin_001", body)

    def test_translate_path_boundary_enforcement(self):
        """Directly verify translate_path maps traversal candidates outside FRONTEND_DIR to safe 404 sentinel."""
        handler = server.RobustVerificationHandler.__new__(server.RobustVerificationHandler)
        handler.directory = server.FRONTEND_DIR

        canonical_frontend = os.path.realpath(server.FRONTEND_DIR)
        for payload in [
            '/../supabase_users_db.json',
            '/../../windows/win.ini',
            '/%2e%2e/supabase_users_db.json'
        ]:
            mapped = handler.translate_path(payload)
            self.assertTrue(
                mapped.endswith('__traversal_blocked_404__'),
                f"Payload {payload} mapped to {mapped} instead of __traversal_blocked_404__"
            )


class TestUploadLimitsAndMagicBytes(SecurityBaseTestCase):
    """Empirical challenge 2: 25MB upload limit & %PDF- magic bytes enforcement."""

    def test_upload_exceeding_25mb_rejected_413(self):
        """Verify POST payload exceeding 25MB is rejected with HTTP 413."""
        exceeding_len = 25 * 1024 * 1024 + 1024
        req_headers = (
            f'POST /api/clinical/upload HTTP/1.1\r\n'
            f'Host: localhost\r\n'
            f'Content-Type: application/pdf\r\n'
            f'Content-Length: {exceeding_len}\r\n\r\n'
        ).encode('utf-8')

        status, headers, body = execute_http_request(req_headers)
        self.assertEqual(status, 413, f"Expected HTTP 413 for payload >25MB, got {status}")
        self.assertIn("exceeds maximum limit of 25MB", body)

    def test_upload_without_pdf_header_rejected_400(self):
        """Verify raw uploaded file without %PDF- magic bytes is rejected with HTTP 400."""
        junk_payload = b'NOT_A_REAL_PDF_FILE_HEADER_TEXT_DATA'
        status, headers, body = execute_post('/api/clinical/upload', junk_payload, 'application/pdf')
        self.assertEqual(status, 400, f"Expected HTTP 400 for missing %PDF- header, got {status}")
        self.assertIn("Expected a valid PDF document starting with '%PDF-' header", body)

    def test_upload_json_base64_without_pdf_header_rejected_400(self):
        """Verify base64 JSON upload without %PDF- magic bytes is rejected with HTTP 400."""
        junk_b64 = base64.b64encode(b'PLAIN_NON_PDF_STRING').decode('ascii')
        payload = json.dumps({'filename': 'fake.pdf', 'file_data': junk_b64}).encode('utf-8')
        status, headers, body = execute_post('/api/clinical/upload', payload, 'application/json')
        self.assertEqual(status, 400, f"Expected HTTP 400 for bad base64 PDF, got {status}")
        self.assertIn("Expected a valid PDF document starting with '%PDF-' header", body)

    def test_upload_valid_fixture_pdf_accepted_200(self):
        """Verify uploading genuine PDF with %PDF- header succeeds with HTTP 200."""
        fixture_path = os.path.join(REPO_ROOT, 'codex', 'fixtures', 'Study_CS-2026-88.pdf')
        if not os.path.exists(fixture_path):
            fixture_path = os.path.join(REPO_ROOT, 'fixtures', 'Study_CS-2026-88.pdf')

        self.assertTrue(os.path.exists(fixture_path), f"Fixture not found: {fixture_path}")
        with open(fixture_path, 'rb') as f:
            valid_pdf = f.read()

        status, headers, body = execute_post('/api/clinical/upload', valid_pdf, 'application/pdf')
        self.assertEqual(status, 200, f"Expected HTTP 200 for valid PDF, got {status}: {body}")
        self.assertIn("Successfully extracted clinical evidence", body)


class TestMasterOTPRemoval(SecurityBaseTestCase):
    """Empirical challenge 3: Master OTP removal and credential reflection prevention."""

    def setUp(self):
        super().setUp()
        self._orig_env = os.environ.get("ENV")
        self._orig_render = os.environ.get("RENDER")

    def tearDown(self):
        super().tearDown()
        if self._orig_env is not None:
            os.environ["ENV"] = self._orig_env
        else:
            os.environ.pop("ENV", None)

        if self._orig_render is not None:
            os.environ["RENDER"] = self._orig_render
        else:
            os.environ.pop("RENDER", None)

    def test_master_otp_884192_rejected(self):
        """Verify master bypass OTP 884192 is rejected (HTTP 400/401, not 200)."""
        payload = json.dumps({'email': 'admin@dermacare.com', 'otp': '884192'}).encode('utf-8')
        status, headers, body = execute_post('/api/auth/verify-otp', payload)
        self.assertIn(status, [400, 401], f"Expected 400 or 401 rejection for bypass OTP, got {status}")
        self.assertNotIn("Authentication successful", body)
        self.assertIn("Invalid or expired verification code", body)

    def test_master_otp_123456_rejected(self):
        """Verify master bypass OTP 123456 is rejected (HTTP 400/401, not 200)."""
        payload = json.dumps({'email': 'admin@dermacare.com', 'otp': '123456'}).encode('utf-8')
        status, headers, body = execute_post('/api/auth/verify-otp', payload)
        self.assertIn(status, [400, 401], f"Expected 400 or 401 rejection for bypass OTP, got {status}")
        self.assertNotIn("Authentication successful", body)
        self.assertIn("Invalid or expired verification code", body)

    def test_send_otp_masked_in_production(self):
        """Verify generated OTP is not reflected in JSON response when ENV=production or RENDER=true."""
        os.environ["ENV"] = "production"
        os.environ["RENDER"] = "true"

        payload = json.dumps({'email': 'admin@dermacare.com', 'role': 'admin'}).encode('utf-8')
        status, headers, body = execute_post('/api/auth/send-otp', payload)
        self.assertEqual(status, 200)

        data = json.loads(body)
        self.assertNotIn('otp', data, "Production send-otp leaked plain OTP in response!")
        self.assertTrue(data.get('otp_masked_in_production'), "Expected otp_masked_in_production flag")

    def test_send_otp_available_in_development(self):
        """Verify generated OTP is provided in development for simulator convenience."""
        os.environ.pop("ENV", None)
        os.environ.pop("RENDER", None)

        payload = json.dumps({'email': 'admin@dermacare.com', 'role': 'admin'}).encode('utf-8')
        status, headers, body = execute_post('/api/auth/send-otp', payload)
        self.assertEqual(status, 200)

        data = json.loads(body)
        self.assertIn('otp', data, "Development mode should provide simulator OTP")
        self.assertEqual(len(data['otp']), 6, "OTP should be 6 digits")


class TestUnhandledInputCrashes(SecurityBaseTestCase):
    """Empirical challenge 4: Non-string and malformed inputs handled cleanly without 500 crashes."""

    def test_submissions_non_string_content_null(self):
        """Verify { brand_name: 123, content: null } returns clean 400, not 500."""
        payload = json.dumps({'brand_name': 123, 'content': None}).encode('utf-8')
        status, headers, body = execute_post('/api/submissions', payload)
        self.assertEqual(status, 400, f"Expected 400 for null content, got {status}")
        self.assertIn("Brand content / copy cannot be empty", body)

    def test_submissions_numeric_fields(self):
        """Verify numeric inputs into brand submission are handled without 500."""
        payload = json.dumps({'brand_name': True, 'content': 456, 'claims': 789}).encode('utf-8')
        status, headers, body = execute_post('/api/submissions', payload)
        self.assertNotEqual(status, 500, f"Unexpected 500 error on numeric fields: {body}")

    def test_clinical_verify_copy_non_string(self):
        """Verify { copy_text: 12345, study_id: null } executes without 500."""
        payload = json.dumps({'copy_text': 12345, 'study_id': None}).encode('utf-8')
        status, headers, body = execute_post('/api/clinical/verify-copy', payload)
        self.assertNotEqual(status, 500, f"Unexpected 500 on verify-copy: {body}")
        self.assertEqual(status, 200)

    def test_auth_login_null_password(self):
        """Verify null password returns clean 400 without crashing."""
        payload = json.dumps({'role': 123, 'password': None}).encode('utf-8')
        status, headers, body = execute_post('/api/auth/login', payload)
        self.assertEqual(status, 400)
        self.assertIn("Password is required", body)

    def test_auth_register_null_password(self):
        """Verify null password in register returns clean 400 without crashing."""
        payload = json.dumps({'email': 'test@example.com', 'password': None}).encode('utf-8')
        status, headers, body = execute_post('/api/auth/register', payload)
        self.assertEqual(status, 400)
        self.assertIn("Password must be at least 4 characters", body)

    def test_hinglish_check_null_and_integer_text(self):
        """Verify null or integer text in hinglish check returns clean 400."""
        payload_null = json.dumps({'text': None}).encode('utf-8')
        status, headers, body = execute_post('/api/hinglish/check', payload_null)
        self.assertEqual(status, 400)

        payload_int = json.dumps({'text': 12345}).encode('utf-8')
        status, headers, body = execute_post('/api/hinglish/check', payload_int)
        self.assertEqual(status, 400)
        self.assertIn("must be a string", body)

    def test_adjudication_non_string_types(self):
        """Verify non-string and non-dict inputs to adjudication submit do not cause 500."""
        payload = json.dumps({'allegation_id': 123, 'allegation_category': None, 'counter_evidence': 456}).encode('utf-8')
        status, headers, body = execute_post('/api/adjudication/submit', payload)
        self.assertNotEqual(status, 500, f"Unexpected 500 on adjudication: {body}")


class TestServerMirrorParity(SecurityBaseTestCase):
    """Cryptographic parity test between root server.py and codex/server.py."""

    def test_server_file_sha256_exact_match(self):
        root_server = os.path.join(REPO_ROOT, 'server.py')
        codex_server = os.path.join(REPO_ROOT, 'codex', 'server.py')

        self.assertTrue(os.path.exists(root_server), f"Missing {root_server}")
        self.assertTrue(os.path.exists(codex_server), f"Missing {codex_server}")

        with open(root_server, 'rb') as f:
            h_root = hashlib.sha256(f.read()).hexdigest()
        with open(codex_server, 'rb') as f:
            h_codex = hashlib.sha256(f.read()).hexdigest()

        self.assertEqual(h_root, h_codex, f"SHA256 mismatch: server.py={h_root} vs codex/server.py={h_codex}")


if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    print("\n" + "=" * 60)
    print("EMPIRICAL CHALLENGER VERIFICATION RESULTS")
    print("=" * 60)
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Failures:        {len(result.failures)}")
    print(f"Errors:          {len(result.errors)}")
    verdict = "APPROVE" if result.wasSuccessful() else "REJECT"
    print(f"VERDICT:         {verdict}")
    print("=" * 60)
    sys.exit(0 if result.wasSuccessful() else 1)
