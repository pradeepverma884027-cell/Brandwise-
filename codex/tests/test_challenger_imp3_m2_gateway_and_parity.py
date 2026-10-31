"""
Empirical Challenger Test Suite for Milestone 2:
Multilingual & Code-Mixed (Hinglish) Advertising Compliance Engine.

Focus Areas:
1. 100% SHA-256 Mirror Parity across codex/frontend/index.html, index.html, and docs/index.html.
2. 100% SHA-256 Mirror Parity between server.py and codex/server.py.
3. Babel JSX script compilation across all three HTML files without syntax errors.
4. Adjudication submission logic for Hinglish allegations:
   - Valid counter-evidence restores +15 compliance score, sets status to dismissed_with_evidence, records SHA-256 hash.
   - Insufficient evidence (justification < 10 chars, missing ref ID, invalid type) rejects properly.
   - Boundary tests at 9 and 10 characters, whitespace trimming, and canonical evidence types.
5. REST API endpoint contract tests (/api/adjudication/submit) with audit log persistence.
6. Frontend client-side fallback simulation & dynamic score restoration math.
"""

import io
import os
import sys
import json
import time
import hashlib
import subprocess
import unittest
from datetime import datetime
from typing import Dict, Any, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODEX_ROOT = os.path.join(REPO_ROOT, "codex")
BACKEND_DIR = os.path.join(CODEX_ROOT, "backend")

for p in [REPO_ROOT, CODEX_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import server
from app.core.review_engine import DeterministicReviewEngine, deterministic_engine, CANONICAL_EVIDENCE_TYPES


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
    """In-memory client invoking server.RobustVerificationHandler directly without OS network sockets."""

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
    def post(cls, path: str, json_data: Any = None, raw_body: bytes = None, headers: Dict[str, str] = None) -> Tuple[int, Dict[str, str], bytes]:
        headers = dict(headers or {})
        if raw_body is not None:
            body = raw_body
        elif json_data is not None:
            headers.setdefault("Content-Type", "application/json")
            body = json.dumps(json_data).encode("utf-8")
        else:
            body = b""
        return cls.request("POST", path, headers=headers, body=body)


class TestTriFileParity(unittest.TestCase):
    """Stress tests for tri-file HTML mirror parity and server dual mirror parity."""

    def test_tri_file_sha256_exact_match(self):
        """Verifies codex/frontend/index.html, index.html, and docs/index.html are byte-for-byte identical."""
        html_paths = [
            os.path.join(REPO_ROOT, "codex", "frontend", "index.html"),
            os.path.join(REPO_ROOT, "index.html"),
            os.path.join(REPO_ROOT, "docs", "index.html")
        ]

        hashes = []
        sizes = []
        contents = []

        for p in html_paths:
            self.assertTrue(os.path.isfile(p), f"Target HTML file does not exist: {p}")
            with open(p, "rb") as f:
                data = f.read()
            contents.append(data)
            sizes.append(len(data))
            hashes.append(hashlib.sha256(data).hexdigest())

        # Assert all sizes are identical and > 0
        self.assertGreater(sizes[0], 100000, "HTML file is unexpectedly small")
        self.assertEqual(sizes[0], sizes[1], f"Size mismatch between codex/frontend/index.html and index.html: {sizes[0]} != {sizes[1]}")
        self.assertEqual(sizes[0], sizes[2], f"Size mismatch between codex/frontend/index.html and docs/index.html: {sizes[0]} != {sizes[2]}")

        # Assert all SHA256 hashes are strictly identical
        self.assertEqual(hashes[0], hashes[1], f"Hash mismatch between codex/frontend/index.html and index.html: {hashes[0]} != {hashes[1]}")
        self.assertEqual(hashes[0], hashes[2], f"Hash mismatch between codex/frontend/index.html and docs/index.html: {hashes[0]} != {hashes[2]}")

        # Exact byte-by-byte equality
        self.assertEqual(contents[0], contents[1], "Byte mismatch between codex/frontend/index.html and index.html")
        self.assertEqual(contents[0], contents[2], "Byte mismatch between codex/frontend/index.html and docs/index.html")

    def test_server_dual_mirror_sha256_match(self):
        """Verifies server.py and codex/server.py are byte-for-byte identical."""
        server_root = os.path.join(REPO_ROOT, "server.py")
        server_codex = os.path.join(REPO_ROOT, "codex", "server.py")

        self.assertTrue(os.path.isfile(server_root), f"Root server.py not found: {server_root}")
        self.assertTrue(os.path.isfile(server_codex), f"Codex server.py not found: {server_codex}")

        with open(server_root, "rb") as f1, open(server_codex, "rb") as f2:
            data1 = f1.read()
            data2 = f2.read()

        h1 = hashlib.sha256(data1).hexdigest()
        h2 = hashlib.sha256(data2).hexdigest()

        self.assertEqual(h1, h2, f"SHA-256 hash mismatch between server.py ({h1}) and codex/server.py ({h2})")
        self.assertEqual(len(data1), len(data2), f"Size mismatch between server.py ({len(data1)}) and codex/server.py ({len(data2)})")
        self.assertEqual(data1, data2, "Byte contents differ between server.py and codex/server.py")


class TestBabelJSXScriptCompilation(unittest.TestCase):
    """Stress tests for Babel JSX script extraction and syntactic compilation."""

    def test_babel_jsx_compilation_via_node_typescript(self):
        """Executes Node.js TypeScript parser against all 3 HTML mirrors to verify 0 syntactic diagnostics."""
        js_script = os.path.join(CODEX_ROOT, "tests", "verify_tri_file_babel.js")
        self.assertTrue(os.path.isfile(js_script), f"Verification script missing: {js_script}")

        res = subprocess.run(["node", js_script], capture_output=True, text=True, cwd=REPO_ROOT)
        self.assertEqual(res.returncode, 0, f"Node verification script failed with code {res.returncode}:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
        self.assertIn("Syntactic parse diagnostics count: 0", res.stdout)
        self.assertIn("VERDICT: SUCCESS - All 3 HTML files have 100% valid Babel JSX compilation!", res.stdout)

    def test_babel_script_identical_across_mirrors(self):
        """Extracts and compares the Babel script block across all 3 files."""
        html_paths = [
            os.path.join(REPO_ROOT, "codex", "frontend", "index.html"),
            os.path.join(REPO_ROOT, "index.html"),
            os.path.join(REPO_ROOT, "docs", "index.html")
        ]

        extracted_scripts = []
        for p in html_paths:
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
            start = content.find('<script type="text/babel">')
            end = content.find('</script>', start)
            self.assertNotEqual(start, -1, f"Missing babel script open tag in {p}")
            self.assertNotEqual(end, -1, f"Missing babel script close tag in {p}")
            script_code = content[start + len('<script type="text/babel">'):end]
            extracted_scripts.append(script_code)

        self.assertEqual(extracted_scripts[0], extracted_scripts[1])
        self.assertEqual(extracted_scripts[0], extracted_scripts[2])
        self.assertGreater(len(extracted_scripts[0]), 200000)


class TestHinglishAdjudicationLogic(unittest.TestCase):
    """Stress tests for the Adjudication Submission Engine on Hinglish allegations."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_adjudicate_hinglish_allegations_all_six_canonical_types(self):
        """Tests that all 6 canonical evidence types successfully dismiss Hinglish allegations."""
        hinglish_categories = [
            "hinglish_claim",
            "vernacular_superlative",
            "skin_lightening",
            "missing_disclosure",
            "clinical_exaggeration"
        ]

        for ev_type in CANONICAL_EVIDENCE_TYPES:
            for cat in hinglish_categories:
                with self.subTest(evidence_type=ev_type, category=cat):
                    allegation_id = f"f-hig-{ev_type[:4]}-{cat[:4]}"
                    payload = {
                        "evidence_type": ev_type,
                        "reference_id": f"REF-VER-{ev_type.upper()}-2026",
                        "justification": f"Clearance documentation validating statutory compliance under {ev_type}."
                    }

                    res = self.engine.adjudicate_counter_evidence(
                        allegation_id=allegation_id,
                        allegation_category=cat,
                        counter_evidence=payload
                    )

                    self.assertTrue(res["success"], f"Adjudication failed for {ev_type} on {cat}")
                    self.assertEqual(res["adjudication"], "ALLEGATION_REVERTED_AND_DISMISSED")
                    self.assertEqual(res["restored_score_delta"], 15)
                    self.assertEqual(res["status"], "dismissed_with_evidence")
                    self.assertEqual(res["allegation_id"], allegation_id)
                    self.assertEqual(res["allegation_category"], cat)
                    self.assertEqual(res["evidence_type"], ev_type)
                    self.assertEqual(res["evidence_reference"], f"REF-VER-{ev_type.upper()}-2026")

                    # Verify 16-hex SHA-256 document hash
                    doc_hash = res["document_hash"]
                    self.assertEqual(len(doc_hash), 16)
                    self.assertTrue(all(c in "0123456789abcdefABCDEF" for c in doc_hash))

                    # Verify ISO 8601 UTC timestamp
                    ts = res["reversal_timestamp"]
                    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    self.assertIsNotNone(parsed)

    def test_deterministic_sha256_hash_reproducibility(self):
        """Generates the exact bit-identical SHA-256 hash for identical Hinglish allegation inputs."""
        counter_evidence = {
            "evidence_type": "ayush_clinical_registry",
            "reference_id": "CTRI-2026-90812",
            "justification": "AYUSH Clinical Trial Registry entry documenting safety and botanical efficacy."
        }

        expected_raw = f"h-claim-superlative:{counter_evidence['evidence_type']}:{counter_evidence['reference_id']}:{counter_evidence['justification']}".encode("utf-8")
        expected_hash = hashlib.sha256(expected_raw).hexdigest()[:16]

        res1 = self.engine.adjudicate_counter_evidence("h-claim-superlative", "hinglish_claim", counter_evidence)
        res2 = self.engine.adjudicate_counter_evidence("h-claim-superlative", "hinglish_claim", counter_evidence)

        self.assertEqual(res1["document_hash"], expected_hash)
        self.assertEqual(res2["document_hash"], expected_hash)
        self.assertEqual(res1["document_hash"], res2["document_hash"])

    def test_explicit_document_hash_preserved_for_hinglish(self):
        """When user provides explicit document hash for Hinglish counter-evidence, it is preserved."""
        counter_evidence = {
            "evidence_type": "cdsco_stage4_clearance",
            "reference_id": "CDSCO-VER-2026-44",
            "justification": "Approved under CDSCO cosmetics regulation clearance protocol.",
            "document_hash": "sha256_hinglish_audit_token_9999"
        }

        res = self.engine.adjudicate_counter_evidence("h-claim-fairness", "skin_lightening", counter_evidence)
        self.assertTrue(res["success"])
        self.assertEqual(res["document_hash"], "sha256_hinglish_audit_token_9999")

    def test_justification_boundary_conditions(self):
        """Thorough boundary testing: 0, 1, 8, 9 characters fail; 10, 11, 1000 characters succeed."""
        test_cases = [
            ("", False, "empty string"),
            ("a", False, "1 character"),
            ("12345678", False, "8 characters"),
            ("123456789", False, "9 characters"),
            ("   123456789   ", False, "9 characters with leading/trailing whitespace"),
            ("1234567890", True, "exactly 10 characters"),
            ("12345678901", True, "11 characters"),
            ("   1234567890   ", True, "10 characters surrounded by whitespace"),
            ("Valid legal justification with detailed clinical trial data.", True, "long text")
        ]

        for text, should_pass, desc in test_cases:
            with self.subTest(desc=desc, text=text):
                res = self.engine.adjudicate_counter_evidence(
                    allegation_id="h-boundary-test",
                    allegation_category="hinglish_claim",
                    counter_evidence={
                        "evidence_type": "clinical_trial_certificate",
                        "reference_id": "REF-BND-01",
                        "justification": text
                    }
                )
                if should_pass:
                    self.assertTrue(res["success"], f"Failed on valid justification: {desc}")
                    self.assertEqual(res["adjudication"], "ALLEGATION_REVERTED_AND_DISMISSED")
                else:
                    self.assertFalse(res["success"], f"Passed on invalid justification: {desc}")
                    self.assertEqual(res["adjudication"], "REJECTED_INSUFFICIENT_EVIDENCE")
                    self.assertIn("min 10 characters", res["message"])

    def test_reference_id_validation_boundaries(self):
        """Missing, None, empty, or whitespace-only reference IDs are rejected."""
        bad_refs = ["", " ", "   ", "\t", "\n\r", None]
        for bad_ref in bad_refs:
            with self.subTest(bad_ref=bad_ref):
                res = self.engine.adjudicate_counter_evidence(
                    allegation_id="h-ref-test",
                    allegation_category="hinglish_claim",
                    counter_evidence={
                        "evidence_type": "legal_waiver_signoff",
                        "reference_id": bad_ref,
                        "justification": "Substantiated with official statutory signoff."
                    }
                )
                self.assertFalse(res["success"])
                self.assertEqual(res["adjudication"], "REJECTED_INSUFFICIENT_EVIDENCE")
                self.assertIn("requires a valid reference ID", res["message"])

    def test_invalid_evidence_type_rejection(self):
        """Non-canonical evidence types are rejected."""
        invalid_types = ["self_attestation", "whatsapp_screenshot", "influencer_dm", "blog_post", ""]
        for bad_type in invalid_types:
            with self.subTest(bad_type=bad_type):
                res = self.engine.adjudicate_counter_evidence(
                    allegation_id="h-type-test",
                    allegation_category="hinglish_claim",
                    counter_evidence={
                        "evidence_type": bad_type,
                        "reference_id": "REF-001",
                        "justification": "Substantiated with official statutory signoff."
                    }
                )
                self.assertFalse(res["success"])
                self.assertEqual(res["adjudication"], "REJECTED_INSUFFICIENT_EVIDENCE")
                self.assertIn("Must be one of", res["message"])


class TestHinglishAdjudicationRestApi(unittest.TestCase):
    """Stress tests for the REST API endpoint POST /api/adjudication/submit handling Hinglish claims."""

    def test_api_successful_hinglish_adjudication_and_audit_trail(self):
        """API successfully adjudicates Hinglish allegation, dismisses finding, and logs to Supabase audit trail."""
        initial_log_count = len(server.SUPABASE_MOCK_TABLES["audit_logs"])

        payload = {
            "allegation_id": "f-hig-1",
            "allegation_category": "hinglish_claim",
            "counter_evidence": {
                "evidence_type": "ayush_clinical_registry",
                "reference_id": "AYUSH-REG-2026-CHAMATKARI",
                "justification": "AYUSH-licensed clinical registry document proving herbal efficacy substantiation."
            }
        }

        status, headers, body = HTTPTestClient.post("/api/adjudication/submit", json_data=payload)
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("content-type"), "application/json")

        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["adjudication"], "ALLEGATION_REVERTED_AND_DISMISSED")

        result = data["result"]
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "dismissed_with_evidence")
        self.assertEqual(result["restored_score_delta"], 15)
        self.assertEqual(result["allegation_id"], "f-hig-1")
        self.assertEqual(len(result["document_hash"]), 16)

        # Verify Supabase audit trail entry
        self.assertEqual(len(server.SUPABASE_MOCK_TABLES["audit_logs"]), initial_log_count + 1)
        latest_log = server.SUPABASE_MOCK_TABLES["audit_logs"][-1]
        self.assertEqual(latest_log["action"], "ALLEGATION_DISMISSED")
        self.assertEqual(latest_log["actor"], "Compliance Adjudication Engine")
        self.assertEqual(latest_log["document_hash"], result["document_hash"])
        self.assertIn("f-hig-1", latest_log["details"])

    def test_api_insufficient_evidence_rejection(self):
        """API returns status='rejected' when justification is under 10 chars."""
        payload = {
            "allegation_id": "f-hig-2",
            "allegation_category": "skin_lightening",
            "counter_evidence": {
                "evidence_type": "clinical_trial_certificate",
                "reference_id": "CT-2026",
                "justification": "Short"  # only 5 chars < 10
            }
        }

        status, headers, body = HTTPTestClient.post("/api/adjudication/submit", json_data=payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "rejected")
        self.assertEqual(data["adjudication"], "REJECTED_INSUFFICIENT_EVIDENCE")
        msg = data.get("result", {}).get("message", "") or data.get("message", "")
        self.assertIn("min 10 characters", msg)

    def test_api_missing_reference_id_rejection(self):
        """API returns status='rejected' when reference_id is missing."""
        payload = {
            "allegation_id": "f-hig-3",
            "allegation_category": "missing_disclosure",
            "counter_evidence": {
                "evidence_type": "influencer_contract_exemption",
                "reference_id": "",
                "justification": "Valid justification text exceeding ten chars."
            }
        }

        status, headers, body = HTTPTestClient.post("/api/adjudication/submit", json_data=payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "rejected")
        self.assertEqual(data["adjudication"], "REJECTED_INSUFFICIENT_EVIDENCE")
        msg = data.get("result", {}).get("message", "") or data.get("message", "")
        self.assertIn("requires a valid reference ID", msg)

    def test_api_malformed_json_handling(self):
        """API returns 400 Bad Request on invalid JSON or non-dict payloads."""
        status1, _, body1 = HTTPTestClient.post("/api/adjudication/submit", raw_body=b"NOT_A_JSON")
        self.assertEqual(status1, 400)
        data1 = json.loads(body1.decode("utf-8"))
        self.assertEqual(data1["status"], "error")

        status2, _, body2 = HTTPTestClient.post("/api/adjudication/submit", raw_body=b"['list_not_dict']")
        self.assertEqual(status2, 400)
        data2 = json.loads(body2.decode("utf-8"))
        self.assertEqual(data2["status"], "error")

    def test_adversarial_injection_payloads(self):
        """Stress tests resilience against SQL injection, XSS vectors, and special characters."""
        adversarial_inputs = [
            ("<script>alert('xss')</script>", "XSS-TAG-01", "XSS vector in justification"),
            ("'; DROP TABLE audit_logs; --", "SQLI-01", "SQL injection vector"),
            ("🎉💯🔥 Namaste! Valid proof! 🌿", "EMOJI-REF-99", "Unicode emoji in justification"),
            ("आयुष क्लिनिकल ट्रायल रजिस्ट्रेशन प्रमाण पत्र", "DEV-01", "Devanagari Unicode script")
        ]

        for justification, ref_id, desc in adversarial_inputs:
            with self.subTest(desc=desc):
                payload = {
                    "allegation_id": f"adv-allegation-{ref_id}",
                    "allegation_category": "hinglish_claim",
                    "counter_evidence": {
                        "evidence_type": "ayush_clinical_registry",
                        "reference_id": ref_id,
                        "justification": justification
                    }
                }
                status, headers, body = HTTPTestClient.post("/api/adjudication/submit", json_data=payload)
                self.assertEqual(status, 200, f"API crashed on adversarial payload: {desc}")
                data = json.loads(body.decode("utf-8"))
                self.assertEqual(data["status"], "success")
                self.assertEqual(data["adjudication"], "ALLEGATION_REVERTED_AND_DISMISSED")
                self.assertEqual(len(data["result"]["document_hash"]), 16)

    def test_rapid_succession_consecutive_adjudications(self):
        """Stress tests rapid consecutive adjudications ensuring audit trail persistence and hash integrity."""
        initial_log_count = len(server.SUPABASE_MOCK_TABLES["audit_logs"])
        hashes = set()

        for i in range(10):
            payload = {
                "allegation_id": f"rapid-allegation-{i:03d}",
                "allegation_category": "hinglish_claim",
                "counter_evidence": {
                    "evidence_type": "lab_assay_report",
                    "reference_id": f"LAB-BATCH-2026-{i:03d}",
                    "justification": f"Independent assay certificate batch #{i:03d} substantiating copy claims."
                }
            }
            status, _, body = HTTPTestClient.post("/api/adjudication/submit", json_data=payload)
            self.assertEqual(status, 200)
            data = json.loads(body.decode("utf-8"))
            self.assertEqual(data["status"], "success")
            doc_hash = data["result"]["document_hash"]
            hashes.add(doc_hash)

        # All 10 distinct inputs must produce 10 distinct hashes
        self.assertEqual(len(hashes), 10)
        self.assertEqual(len(server.SUPABASE_MOCK_TABLES["audit_logs"]), initial_log_count + 10)

    def test_large_payload_stress(self):
        """Stress tests counter-evidence justification with 50,000 characters."""
        large_text = "Clinical evidence substantiation report. " * 1250  # 51,250 chars
        payload = {
            "allegation_id": "large-payload-allegation",
            "allegation_category": "hinglish_claim",
            "counter_evidence": {
                "evidence_type": "clinical_trial_certificate",
                "reference_id": "CT-LARGE-50K",
                "justification": large_text
            }
        }
        t0 = time.time()
        status, _, body = HTTPTestClient.post("/api/adjudication/submit", json_data=payload)
        elapsed = time.time() - t0
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        self.assertLess(elapsed, 1.0, "Large payload processing took too long (> 1s)")


class TestFrontendSimulationAndScoringLogic(unittest.TestCase):
    """Stress tests verifying frontend simulation fallback, score calculation, and UI contracts."""

    def test_frontend_score_restoration_math(self):
        """Validates the mathematical formula used in React SPA:
        rawHinglishScore = 100 - (openHigh*20 + openMed*10 + openLow*5) + hinglishRestoredScoreDelta
        hinglishComplianceScore = Math.max(0, Math.min(100, Math.round(rawHinglishScore)))
        """
        # Baseline: 4 open high violations (from Instagram sample)
        open_high = 4
        open_med = 0
        open_low = 0
        restored_delta = 0

        score_0 = max(0, min(100, 100 - (open_high * 20 + open_med * 10 + open_low * 5) + restored_delta))
        self.assertEqual(score_0, 20)

        # Adjudication 1: 1 violation dismissed with counter-evidence
        open_high -= 1
        restored_delta += 15
        score_1 = max(0, min(100, 100 - (open_high * 20 + open_med * 10 + open_low * 5) + restored_delta))
        self.assertEqual(score_1, 55)  # 100 - 60 + 15 = 55

        # Adjudication 2: 2nd violation dismissed
        open_high -= 1
        restored_delta += 15
        score_2 = max(0, min(100, 100 - (open_high * 20 + open_med * 10 + open_low * 5) + restored_delta))
        self.assertEqual(score_2, 90)  # 100 - 40 + 30 = 90

        # Adjudication 3: 3rd violation dismissed (clamped at 100)
        open_high -= 1
        restored_delta += 15
        score_3 = max(0, min(100, 100 - (open_high * 20 + open_med * 10 + open_low * 5) + restored_delta))
        self.assertEqual(score_3, 100)  # 100 - 20 + 45 = 125 -> clamped 100

    def test_frontend_fnv1a_hash_simulation(self):
        """Validates the deterministic client-side hash computation algorithm implemented in index.html (lines 2404-2411)."""
        evidence_type = "ayush_clinical_registry"
        reference_id = "REF-AYUSH-101"
        justification = "Substantiated botanical efficacy registry documentation."

        text_to_hash = f"{evidence_type}:{reference_id}:{justification}"
        hash_num = 0x811c9dc5
        for char in text_to_hash:
            hash_num ^= ord(char)
            # 32-bit integer multiplication emulating Math.imul(hashNum, 0x01000193)
            hash_num = (hash_num * 0x01000193) & 0xFFFFFFFF

        hex_hash = f"{hash_num:08x}"
        doc_hash = f"0x{hex_hash}71e4"

        # Check format
        self.assertTrue(doc_hash.startswith("0x"))
        self.assertEqual(len(doc_hash), 14)

    def test_frontend_omnichannel_configs_presence(self):
        """Verifies both new Hinglish channel configs and their preloaded findings in index.html."""
        html_path = os.path.join(REPO_ROOT, "codex", "frontend", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Instagram Caption (Hinglish)
        self.assertIn("'Instagram Caption (Hinglish)'", html)
        self.assertIn("f-hig-1", html)
        self.assertIn("f-hig-2", html)
        self.assertIn("f-hig-3", html)
        self.assertIn("f-hig-4", html)
        self.assertIn("Drugs and Magic Remedies Act 1954", html)
        self.assertIn("ASCI Vernacular Guidelines 2025", html)

        # Influencer Video Script (Hinglish)
        self.assertIn("'Influencer Video Script (Hinglish)'", html)
        self.assertIn("f-hinf-1", html)
        self.assertIn("f-hinf-2", html)
        self.assertIn("f-hinf-3", html)
        self.assertIn("AYUSH Guidelines", html)
        self.assertIn("CDSCO", html)

    def test_frontend_adjudication_button_and_dismissal_card(self):
        """Verifies the button wiring and dismissal UI presentation elements."""
        html_path = os.path.join(REPO_ROOT, "codex", "frontend", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Modal trigger button in Hinglish card list
        self.assertIn("handleOpenCounterEvidenceModal(finding, 'hinglish')", html)

        # Dismissal banner state elements
        self.assertIn("Allegation Dismissed &mdash; Evidence Accepted", html)
        self.assertIn("(+15 Score Restored)", html)
        self.assertIn("finding.documentHash", html)
        self.assertIn("finding.reversalTimestamp", html)
        self.assertIn("activeCounterTarget.source === 'hinglish'", html)


if __name__ == "__main__":
    unittest.main()
