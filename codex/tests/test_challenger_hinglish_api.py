"""
Empirical Challenger Test Suite for Milestone 1 Hinglish Compliance REST API
Endpoints: POST /api/hinglish/check and POST /codex/api/hinglish/check

Validates:
1. API request validation & 400 Bad Request error responses (malformed, empty, missing, invalid types).
2. Scoring contract (100 base, -20 High, -10 Medium, clamped [0, 100], clean copy = 100).
3. Findings contract (id: h-claim-{N}, status: open, lowercase severities, suggested_fix in Hinglish).
4. Path variants (/api/hinglish/check, /codex/api/hinglish/check, trailing slashes, query strings).
5. SHA256 byte-for-byte mirror parity between server.py and codex/server.py.
6. Live TCP socket transmission over actual HTTPServer instance.
"""

import io
import os
import sys
import json
import hashlib
import re
import socket
import threading
import unittest
import urllib.request
import urllib.error
from http.server import HTTPServer
from typing import Dict, Any, Tuple, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODEX_ROOT = os.path.join(REPO_ROOT, "codex")
BACKEND_DIR = os.path.join(CODEX_ROOT, "backend")

for p in [REPO_ROOT, CODEX_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import server


class MockSocket:
    """Mock socket stream allowing in-memory testing of BaseHTTPRequestHandler."""
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
    def post(cls, path: str, json_data: Any = None, raw_body: Optional[bytes] = None, headers: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, str], bytes]:
        headers = dict(headers or {})
        if raw_body is not None:
            body = raw_body
        elif json_data is not None:
            headers.setdefault("Content-Type", "application/json")
            body = json.dumps(json_data).encode("utf-8")
        else:
            body = b""
        return cls.request("POST", path, headers=headers, body=body)

    @classmethod
    def get(cls, path: str, headers: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, str], bytes]:
        return cls.request("GET", path, headers=headers)


class TestChallengerHinglishAPI(unittest.TestCase):
    """Adversarial stress-testing of Hinglish REST API validation, scoring, and contracts."""

    # =========================================================================
    # PART 1: REQUEST VALIDATION & ERROR RESPONSES (400 BAD REQUEST)
    # =========================================================================

    def test_post_malformed_json_returns_400(self):
        """Malformed JSON strings must be rejected with 400 Bad Request."""
        malformed_payloads = [
            b'{"text": "unterminated string',
            b'{"text": "val",}',  # trailing comma
            b"{'text': 'single quotes'}",  # single quotes
            b'not a json payload',
            b'{text: "unquoted key"}',
            b'{"text": \x00\x01}',  # control characters
        ]
        for malformed in malformed_payloads:
            with self.subTest(payload=malformed):
                status, headers, body = HTTPTestClient.post(
                    "/api/hinglish/check",
                    raw_body=malformed,
                    headers={"Content-Type": "application/json"}
                )
                self.assertEqual(status, 400, f"Expected 400 for malformed payload {malformed}, got {status}")
                data = json.loads(body.decode("utf-8"))
                self.assertEqual(data.get("status"), "error")
                self.assertIn("message", data)

    def test_post_empty_body_returns_400(self):
        """Empty or whitespace-only bodies must be rejected with 400 Bad Request."""
        empty_payloads = [
            b"",
            b"   ",
            b"\n\t\r  \n",
        ]
        for empty_body in empty_payloads:
            with self.subTest(empty_body=empty_body):
                status, headers, body = HTTPTestClient.post(
                    "/api/hinglish/check",
                    raw_body=empty_body,
                    headers={"Content-Type": "application/json"}
                )
                self.assertEqual(status, 400)
                data = json.loads(body.decode("utf-8"))
                self.assertEqual(data.get("status"), "error")

    def test_post_empty_object_returns_400(self):
        """Empty JSON object `{}` must return 400 Bad Request."""
        status, headers, body = HTTPTestClient.post(
            "/api/hinglish/check",
            json_data={}
        )
        self.assertEqual(status, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "error")
        self.assertIn("message", data)

    def test_post_missing_text_field_returns_400(self):
        """JSON payload missing the 'text' field must return 400 Bad Request."""
        invalid_objects = [
            {"channel": "hinglish_instagram"},
            {"content": "Arre dosto!"},
            {"query": "100% asar"},
            {"message": "Hello world"},
            {"studies": []},
        ]
        for payload in invalid_objects:
            with self.subTest(payload=payload):
                status, headers, body = HTTPTestClient.post(
                    "/api/hinglish/check",
                    json_data=payload
                )
                self.assertEqual(status, 400)
                data = json.loads(body.decode("utf-8"))
                self.assertEqual(data.get("status"), "error")
                self.assertIn("text", data.get("message", "").lower())

    def test_post_array_payload_returns_400(self):
        """Top-level JSON arrays must return 400 Bad Request."""
        array_payloads = [
            [1, 2, 3],
            [],
            ["text", "hello"],
            [{"text": "valid string inside list"}],
        ]
        for arr in array_payloads:
            with self.subTest(arr=arr):
                status, headers, body = HTTPTestClient.post(
                    "/api/hinglish/check",
                    json_data=arr
                )
                self.assertEqual(status, 400)
                data = json.loads(body.decode("utf-8"))
                self.assertEqual(data.get("status"), "error")
                self.assertIn("object", data.get("message", "").lower())

    def test_post_non_string_text_field_returns_400(self):
        """When 'text' is not a string (int, bool, float, None, list, dict), return 400."""
        invalid_text_types = [
            12345,
            0,
            -99,
            True,
            False,
            None,
            99.99,
            ["list", "of", "strings"],
            {"nested": "dict"},
        ]
        for val in invalid_text_types:
            with self.subTest(val=val):
                status, headers, body = HTTPTestClient.post(
                    "/api/hinglish/check",
                    json_data={"text": val}
                )
                self.assertEqual(status, 400, f"Expected 400 for text={val!r}, got {status}")
                data = json.loads(body.decode("utf-8"))
                self.assertEqual(data.get("status"), "error")

    # =========================================================================
    # PART 2: PATH VARIANTS & ROUTING
    # =========================================================================

    def test_codex_prefix_path_routing(self):
        """Endpoint /codex/api/hinglish/check must route identically to /api/hinglish/check."""
        payload = {"text": "#vigyapan Safe clean text."}
        status, headers, body = HTTPTestClient.post("/codex/api/hinglish/check", json_data=payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("compliance_score"), 100)

    def test_trailing_slash_path_routing(self):
        """Trailing slash on /api/hinglish/check/ must be stripped and handled cleanly."""
        payload = {"text": "#vigyapan Safe clean text."}
        status, headers, body = HTTPTestClient.post("/api/hinglish/check/", json_data=payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")

    def test_query_parameters_path_routing(self):
        """Query parameters like /api/hinglish/check?client=react&v=2 must not break routing."""
        payload = {"text": "#vigyapan Safe clean text."}
        status, headers, body = HTTPTestClient.post("/api/hinglish/check?client=react&v=2", json_data=payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")

    def test_non_post_methods_rejected(self):
        """GET request to /api/hinglish/check must return 404."""
        status, headers, body = HTTPTestClient.get("/api/hinglish/check")
        self.assertEqual(status, 404)

    # =========================================================================
    # PART 3: SCORING CONTRACTS & RESPONSE PROPERTIES
    # =========================================================================

    def test_clean_copy_score_100_and_zero_findings(self):
        """Clean copy returns HTTP 200, score 100, 0 findings, and is_compliant=True."""
        clean_copy = "#vigyapan DermaCare gentle hydration serum with dermatologist-tested hyaluronic acid."
        status, headers, body = HTTPTestClient.post(
            "/api/hinglish/check",
            json_data={"text": clean_copy, "channel": "hinglish_instagram"}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("compliance_score"), 100)
        self.assertEqual(len(data.get("findings", [])), 0)
        summary = data.get("summary", {})
        self.assertEqual(summary.get("total_findings"), 0)
        self.assertEqual(summary.get("high_severity_count"), 0)
        self.assertEqual(summary.get("medium_severity_count"), 0)
        self.assertTrue(summary.get("is_compliant"))

    def test_empty_string_text_returns_200_score_100(self):
        """Empty string text {'text': ''} returns 200, score 100, and is_compliant=True."""
        status, headers, body = HTTPTestClient.post(
            "/api/hinglish/check",
            json_data={"text": ""}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("compliance_score"), 100)
        self.assertEqual(len(data.get("findings", [])), 0)
        self.assertTrue(data.get("summary", {}).get("is_compliant"))

    def test_single_high_violation_deduction_minus_20(self):
        """A single High severity violation deducts exactly 20 points (score: 80)."""
        # Non-promotional sentence with exactly one absolute cure claim
        text = "#vigyapan Hamara ayurvedic lepa chamatkari results produce karta hai."
        status, headers, body = HTTPTestClient.post(
            "/api/hinglish/check",
            json_data={"text": text}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        findings = data.get("findings", [])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "high")
        self.assertEqual(findings[0]["highlighted_text"].lower(), "chamatkari")
        self.assertEqual(data.get("compliance_score"), 80)
        self.assertEqual(data["summary"]["high_severity_count"], 1)
        self.assertFalse(data["summary"]["is_compliant"])

    def test_two_high_violations_deduction_minus_40(self):
        """Two High severity violations deduct exactly 40 points (score: 60)."""
        # Two High claims: chamatkari + jad se khatam
        text = "#vigyapan Hamara chamatkari solution pimples ko jad se khatam karta hai."
        status, headers, body = HTTPTestClient.post(
            "/api/hinglish/check",
            json_data={"text": text}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        findings = data.get("findings", [])
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["severity"], "high")
        self.assertEqual(findings[1]["severity"], "high")
        self.assertEqual(data.get("compliance_score"), 60)
        self.assertEqual(data["summary"]["high_severity_count"], 2)

    def test_single_medium_violation_deduction_minus_10(self):
        """A single Medium severity violation deducts exactly 10 points (score: 90)."""
        # Borderline rounding of CS-2026-88 (94.2%): "94% asar" is Medium severity
        text = "#vigyapan Clinical trial shows 94% asar in everyday skin hydration levels."
        status, headers, body = HTTPTestClient.post(
            "/api/hinglish/check",
            json_data={"text": text}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        findings = data.get("findings", [])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "medium")
        self.assertEqual(data.get("compliance_score"), 90)
        self.assertEqual(data["summary"]["medium_severity_count"], 1)

    def test_mixed_high_and_medium_violations_deduction(self):
        """Mixed High (-20) and Medium (-10) violations produce score: 70."""
        text = "#vigyapan Hamara chamatkari formula deta hai 94% asar hydration mein."
        status, headers, body = HTTPTestClient.post(
            "/api/hinglish/check",
            json_data={"text": text}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("compliance_score"), 70)
        self.assertEqual(data["summary"]["high_severity_count"], 1)
        self.assertEqual(data["summary"]["medium_severity_count"], 1)

    def test_extreme_violation_copy_strictly_clamped_to_zero(self):
        """Copy with 8+ violations where deductions exceed 100 must clamp score strictly to 0."""
        # 1. chamatkari (High, -20)
        # 2. 100% asar (High, -20)
        # 3. gora rang (High, -20)
        # 4. jad se khatam (High, -20)
        # 5. hamesha ke liye (High, -20)
        # 6. shat pratishat (High, -20)
        # 7. ramban ilaj (High, -20)
        # 8. pakka ilaj (High, -20)
        # Total deduction would be -160.
        extreme_copy = (
            "Arre dosto! Ye chamatkari formula deta hai 100% asar aur gora rang! "
            "Pimples ko jad se khatam karega hamesha ke liye! Shat pratishat asar! "
            "Ye hai ramban ilaj aur pakka ilaj! Aaj hi order karein discount link bio mein!"
        )
        status, headers, body = HTTPTestClient.post(
            "/api/hinglish/check",
            json_data={"text": extreme_copy}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertGreaterEqual(len(data.get("findings", [])), 8)
        self.assertEqual(data.get("compliance_score"), 0, "Score must clamp to 0, never negative")
        self.assertFalse(data["summary"]["is_compliant"])

    # =========================================================================
    # PART 4: FINDINGS SCHEMA AND CONTRACT VERIFICATION
    # =========================================================================

    def test_findings_schema_and_attributes(self):
        """All finding items must strictly conform to contract: id format, status, lowercase severity, Hinglish fix."""
        sample_copy = "Arre dosto! Ye chamatkari formula deta hai 100% asar aur gora rang sirf 7 din mein! Aaj hi order karein link bio mein!"
        status, headers, body = HTTPTestClient.post(
            "/api/hinglish/check",
            json_data={"text": sample_copy, "channel": "hinglish_instagram"}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        findings = data.get("findings", [])
        self.assertEqual(len(findings), 4, f"Preset sample copy should return 4 findings, got {len(findings)}")

        for idx, finding in enumerate(findings):
            # 1. ID format: h-claim-{N}
            expected_id = f"h-claim-{idx + 1}"
            self.assertEqual(finding.get("id"), expected_id, f"Finding id should be {expected_id}")

            # 2. Status: open
            self.assertEqual(finding.get("status"), "open")

            # 3. Severity: strictly lowercase
            sev = finding.get("severity")
            self.assertIn(sev, ["high", "medium", "low"])
            self.assertEqual(sev, sev.lower())

            # 4. Highlighted span verification against original text
            start = finding.get("span_start")
            end = finding.get("span_end")
            highlight = finding.get("highlighted_text")
            if start is not None and end is not None and highlight is not None:
                self.assertIsInstance(start, int)
                self.assertIsInstance(end, int)
                self.assertLessEqual(start, end)
                # Highlighted text matches the slice in text (disclaimer rules add ellipsis '...' for long text)
                clean_highlight = highlight.rstrip(".").strip()
                expected_slice = sample_copy[start:end].rstrip(".").strip()
                self.assertEqual(clean_highlight.lower(), expected_slice.lower())

            # 5. Suggested fix: non-empty Hinglish rewrite
            fix = finding.get("suggested_fix")
            self.assertIsInstance(fix, str)
            self.assertGreater(len(fix.strip()), 0)
            self.assertNotEqual(fix.strip().lower(), highlight.strip().lower())

            # 6. Source reference present
            source_ref = finding.get("source_ref")
            self.assertIsInstance(source_ref, str)
            self.assertGreater(len(source_ref.strip()), 0)

            # 7. Confidence in range [0, 1]
            confidence = finding.get("confidence")
            self.assertIsInstance(confidence, (int, float))
            self.assertGreaterEqual(confidence, 0.0)
            self.assertLessEqual(confidence, 1.0)

    # =========================================================================
    # PART 5: ADVERSARIAL EDGE CASES & RESILIENCE
    # =========================================================================

    def test_unicode_devanagari_and_emojis(self):
        """Handles code-mixed Devanagari Hindi, emojis, and multiline formatting safely."""
        text = "नमस्ते Dosto! 🌟🔥 Ye chamatkari formula aur gora rang deta hai ✨! #vigyapan\nAur link bio mein check karein!"
        status, headers, body = HTTPTestClient.post(
            "/api/hinglish/check",
            json_data={"text": text}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertIsInstance(data.get("compliance_score"), int)

    def test_large_text_stress_payload(self):
        """Processes 50KB payload without catastrophic backtracking, timeout, or crash."""
        large_text = "#vigyapan " + ("DermaCare moisturizer clean hydrating skin cream. " * 1000)
        status, headers, body = HTTPTestClient.post(
            "/api/hinglish/check",
            json_data={"text": large_text}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("compliance_score"), 100)

    def test_custom_clinical_studies_override(self):
        """Accepts custom clinical dossier in payload and cross-references accordingly."""
        custom_studies = [
            {
                "study_id": "CUSTOM-TRIAL-01",
                "endpoints": {
                    "hydration_increase_percent": 88.0,
                    "duration_days": 21
                }
            }
        ]
        text = "#vigyapan Hamara moisturizer deta hai 99% asar hydration mein."
        status, headers, body = HTTPTestClient.post(
            "/api/hinglish/check",
            json_data={"text": text, "clinical_studies": custom_studies}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")

    # =========================================================================
    # PART 6: LIVE TCP SOCKET EXECUTION OVER HTTP SERVER
    # =========================================================================

    def test_live_tcp_socket_interaction(self):
        """Starts real HTTPServer on localhost and executes real HTTP requests over TCP."""
        # Bind server to port 0 (OS picks available ephemeral port)
        httpd = HTTPServer(("127.0.0.1", 0), server.RobustVerificationHandler)
        port = httpd.server_port
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        base_url = f"http://127.0.0.1:{port}"

        try:
            # 1. Test 200 OK for clean text
            req = urllib.request.Request(
                f"{base_url}/api/hinglish/check",
                data=json.dumps({"text": "#vigyapan Clean valid copy."}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                body = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(body.get("status"), "success")
                self.assertEqual(body.get("compliance_score"), 100)

            # 2. Test 400 Bad Request for malformed JSON over real socket
            req_bad = urllib.request.Request(
                f"{base_url}/api/hinglish/check",
                data=b'{"broken": json',
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req_bad, timeout=5)
            self.assertEqual(ctx.exception.code, 400)

            # 3. Test 400 Bad Request for missing text key over real socket
            req_missing = urllib.request.Request(
                f"{base_url}/api/hinglish/check",
                data=json.dumps({"channel": "hinglish_instagram"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req_missing, timeout=5)
            self.assertEqual(ctx.exception.code, 400)

            # 4. Test /codex/api/hinglish/check over real socket
            req_codex = urllib.request.Request(
                f"{base_url}/codex/api/hinglish/check",
                data=json.dumps({"text": "#vigyapan Clean text over codex prefix."}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req_codex, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                body = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(body.get("compliance_score"), 100)

        finally:
            httpd.shutdown()
            httpd.server_close()

    # =========================================================================
    # PART 7: SHA256 MIRROR PARITY VERIFICATION
    # =========================================================================

    def test_sha256_mirror_parity_server_and_codex_server(self):
        """server.py and codex/server.py must be 100% byte-for-byte identical with matching SHA256."""
        path_root_server = os.path.join(REPO_ROOT, "server.py")
        path_codex_server = os.path.join(CODEX_ROOT, "server.py")

        self.assertTrue(os.path.exists(path_root_server), "server.py does not exist")
        self.assertTrue(os.path.exists(path_codex_server), "codex/server.py does not exist")

        with open(path_root_server, "rb") as f1:
            bytes_root = f1.read()
        with open(path_codex_server, "rb") as f2:
            bytes_codex = f2.read()

        sha_root = hashlib.sha256(bytes_root).hexdigest()
        sha_codex = hashlib.sha256(bytes_codex).hexdigest()

        self.assertEqual(
            sha_root,
            sha_codex,
            f"SHA256 parity mismatch!\nserver.py:       {sha_root}\ncodex/server.py: {sha_codex}"
        )
        self.assertEqual(
            len(bytes_root),
            len(bytes_codex),
            "File length mismatch between server.py and codex/server.py"
        )
        self.assertEqual(
            bytes_root,
            bytes_codex,
            "Byte content differs between server.py and codex/server.py"
        )


if __name__ == "__main__":
    unittest.main()
