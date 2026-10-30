"""
Unit and Integration Test Suite for Interactive Counter-Evidence Adjudication Engine & REST API.

Validates Improvement 2 Feature Specifications (R2, R4, R5):
1. All 6 canonical evidence types:
   - clinical_trial_certificate
   - cdsco_stage4_clearance
   - legal_waiver_signoff
   - lab_assay_report
   - influencer_contract_exemption
   - ayush_clinical_registry
2. Valid submission returns:
   - success: True
   - adjudication: "ALLEGATION_REVERTED_AND_DISMISSED"
   - restored_score_delta: 15
   - document_hash (16-char hex SHA-256)
   - reversal_timestamp (ISO 8601 UTC)
3. Deterministic SHA-256 document hashing:
   - Same inputs generate bit-identical 16-char hex digest.
   - User-supplied document_hash is preserved when present.
4. Insufficient / invalid evidence handling:
   - Justification < 10 characters -> rejected.
   - Boundary tests at 9 characters (fails) and 10 characters (passes).
   - Missing or whitespace-only reference ID -> rejected.
   - Non-canonical evidence types -> rejected.
5. End-to-end adjudication cycle:
   - Violation flagged -> counter-evidence submitted -> allegation dismissed -> score restored (+15 pts).
6. Audit trail persistence:
   - Dismissal event recorded in Supabase audit_logs table with document_hash and timestamp.
7. In-memory REST API contract tests for POST /api/adjudication/submit using HTTPTestClient:
   - 200 with status="success" on valid payload.
   - status="rejected" on insufficient evidence.
   - 400 on malformed JSON or non-dict payloads.
"""

import io
import os
import sys
import json
import time
import hashlib
import unittest
from datetime import datetime
from typing import Dict, Any, Tuple

# Path configuration
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODEX_ROOT = os.path.join(REPO_ROOT, "codex")
BACKEND_DIR = os.path.join(CODEX_ROOT, "backend")

for p in [REPO_ROOT, CODEX_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import server
from app.core.review_engine import DeterministicReviewEngine, deterministic_engine, CANONICAL_EVIDENCE_TYPES


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
    """In-memory client invoking server.RobustVerificationHandler directly without OS network ports."""

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
    def get(cls, path: str, headers: Dict[str, str] = None) -> Tuple[int, Dict[str, str], bytes]:
        return cls.request("GET", path, headers=headers)

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


class TestCounterEvidenceAdjudication(unittest.TestCase):
    """Test suite verifying interactive counter-evidence adjudication rules and REST API contracts."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    # -------------------------------------------------------------------------
    # 1. Canonical Evidence Types & Successful Adjudication
    # -------------------------------------------------------------------------
    def test_all_six_canonical_evidence_types_succeed(self):
        """Verifies all 6 mandated canonical evidence types successfully dismiss allegations."""
        for evidence_type in CANONICAL_EVIDENCE_TYPES:
            with self.subTest(evidence_type=evidence_type):
                payload = {
                    "evidence_type": evidence_type,
                    "reference_id": f"REF-{evidence_type.upper()}-2026",
                    "justification": f"Substantiating documentation verified under regulatory protocol {evidence_type}."
                }
                res = self.engine.adjudicate_counter_evidence(
                    allegation_id="allegation-001",
                    allegation_category="claim",
                    counter_evidence=payload
                )

                self.assertTrue(res["success"])
                self.assertEqual(res["adjudication"], "ALLEGATION_REVERTED_AND_DISMISSED")
                self.assertEqual(res["restored_score_delta"], 15)
                self.assertEqual(res["evidence_type"], evidence_type)
                self.assertEqual(res["evidence_reference"], f"REF-{evidence_type.upper()}-2026")
                self.assertEqual(res["allegation_id"], "allegation-001")
                self.assertEqual(res["allegation_category"], "claim")
                self.assertEqual(res["status"], "dismissed_with_evidence")
                self.assertIn("audit_note", res)

                # Validate timestamp is valid ISO 8601 UTC
                ts = res["reversal_timestamp"]
                parsed_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                self.assertIsNotNone(parsed_dt)

                # Validate document hash is 16-character hex
                doc_hash = res["document_hash"]
                self.assertEqual(len(doc_hash), 16)
                self.assertTrue(all(c in "0123456789abcdefABCDEF" for c in doc_hash))

    # -------------------------------------------------------------------------
    # 2. Deterministic SHA-256 Document Hashing
    # -------------------------------------------------------------------------
    def test_deterministic_document_hashing(self):
        """Generates deterministic 16-character SHA-256 hex digest for identical inputs."""
        counter_ev = {
            "evidence_type": "clinical_trial_certificate",
            "reference_id": "CT-2026-HYD-88",
            "justification": "Double-blind clinical study confirming 94.2% stratum corneum hydration."
        }

        # Expected hash computation: sha256("allegation-042:clinical_trial_certificate:CT-2026-HYD-88:Double-blind...").hexdigest()[:16]
        expected_raw = f"allegation-042:{counter_ev['evidence_type']}:{counter_ev['reference_id']}:{counter_ev['justification']}".encode("utf-8")
        expected_hash = hashlib.sha256(expected_raw).hexdigest()[:16]

        res1 = self.engine.adjudicate_counter_evidence("allegation-042", "clinical", counter_ev)
        res2 = self.engine.adjudicate_counter_evidence("allegation-042", "clinical", counter_ev)

        self.assertEqual(res1["document_hash"], expected_hash)
        self.assertEqual(res2["document_hash"], expected_hash)
        self.assertEqual(res1["document_hash"], res2["document_hash"])

    def test_explicit_document_hash_preserved(self):
        """User-supplied explicit document hash is preserved verbatim."""
        counter_ev = {
            "evidence_type": "cdsco_stage4_clearance",
            "reference_id": "CDSCO-904",
            "justification": "CDSCO Stage IV official approval letter on file.",
            "document_hash": "custom_hash_778899"
        }
        res = self.engine.adjudicate_counter_evidence("allegation-099", "regulatory", counter_ev)
        self.assertTrue(res["success"])
        self.assertEqual(res["document_hash"], "custom_hash_778899")

    # -------------------------------------------------------------------------
    # 3. Justification Length Boundary Value Analysis (10 characters)
    # -------------------------------------------------------------------------
    def test_justification_boundary_at_10_characters(self):
        """Justification with exactly 9 characters fails; exactly 10 characters passes."""
        # 0 chars (empty) -> fails
        res_0 = self.engine.adjudicate_counter_evidence("a-1", "claim", {
            "evidence_type": "lab_assay_report",
            "reference_id": "LAB-01",
            "justification": ""
        })
        self.assertFalse(res_0["success"])
        self.assertEqual(res_0["adjudication"], "REJECTED_INSUFFICIENT_EVIDENCE")

        # 9 chars -> fails
        res_9 = self.engine.adjudicate_counter_evidence("a-1", "claim", {
            "evidence_type": "lab_assay_report",
            "reference_id": "LAB-01",
            "justification": "123456789"
        })
        self.assertFalse(res_9["success"])
        self.assertEqual(res_9["adjudication"], "REJECTED_INSUFFICIENT_EVIDENCE")
        self.assertIn("min 10 characters", res_9["message"])

        # 10 chars -> passes
        res_10 = self.engine.adjudicate_counter_evidence("a-1", "claim", {
            "evidence_type": "lab_assay_report",
            "reference_id": "LAB-01",
            "justification": "1234567890"
        })
        self.assertTrue(res_10["success"])
        self.assertEqual(res_10["adjudication"], "ALLEGATION_REVERTED_AND_DISMISSED")

        # 11 chars -> passes
        res_11 = self.engine.adjudicate_counter_evidence("a-1", "claim", {
            "evidence_type": "lab_assay_report",
            "reference_id": "LAB-01",
            "justification": "12345678901"
        })
        self.assertTrue(res_11["success"])

        # Padding spaces stripped: "  123456789  " has 9 real chars -> fails
        res_spaces = self.engine.adjudicate_counter_evidence("a-1", "claim", {
            "evidence_type": "lab_assay_report",
            "reference_id": "LAB-01",
            "justification": "   123456789   "
        })
        self.assertFalse(res_spaces["success"])

    # -------------------------------------------------------------------------
    # 4. Invalid Evidence Type & Reference ID Validation
    # -------------------------------------------------------------------------
    def test_invalid_evidence_type_rejection(self):
        """Non-canonical or blank evidence types are rejected with descriptive messages."""
        invalid_types = ["random_blog_post", "twitter_screenshot", "self_declaration", "internal_memo", ""]
        for bad_type in invalid_types:
            with self.subTest(bad_type=bad_type):
                res = self.engine.adjudicate_counter_evidence("a-1", "claim", {
                    "evidence_type": bad_type,
                    "reference_id": "REF-01",
                    "justification": "Valid justification exceeding ten characters."
                })
                self.assertFalse(res["success"])
                self.assertEqual(res["adjudication"], "REJECTED_INSUFFICIENT_EVIDENCE")
                self.assertIn("Must be one of", res["message"])

    def test_missing_or_whitespace_reference_id_rejection(self):
        """Missing, empty, or whitespace-only reference ID is rejected."""
        for bad_ref in ["", "   ", "\t\n", None]:
            with self.subTest(bad_ref=bad_ref):
                res = self.engine.adjudicate_counter_evidence("a-1", "claim", {
                    "evidence_type": "legal_waiver_signoff",
                    "reference_id": bad_ref,
                    "justification": "Valid justification exceeding ten characters."
                })
                self.assertFalse(res["success"])
                self.assertEqual(res["adjudication"], "REJECTED_INSUFFICIENT_EVIDENCE")
                self.assertIn("requires a valid reference ID", res["message"])

    # -------------------------------------------------------------------------
    # 5. End-to-End Adjudication & Score Restoration (+15 points)
    # -------------------------------------------------------------------------
    def test_end_to_end_adjudication_score_restoration_cycle(self):
        """Simulates full lifecycle: visual/text violation flagged -> counter-evidence -> dismissed -> +15 score."""
        # Step 1: Visual asset inspected with aspect ratio distortion
        asset_metadata = {
            "asset_id": "hero-launch.png",
            "aspect_ratio": 1.08,
            "expected_aspect_ratio": 1.0,
            "detected_hex_colors": ["#0F172A"],
            "disclaimer_fg": "#FFFFFF",
            "disclaimer_bg": "#0F172A",
            "alt_text": "Hero image"
        }
        inspection = self.engine.inspect_visual_geometry_and_palette(asset_metadata)
        self.assertFalse(inspection["is_compliant"])
        self.assertEqual(len(inspection["violations"]), 1)
        flagged_allegation = inspection["violations"][0]
        self.assertEqual(flagged_allegation["type"], "logo_distortion")

        # Initial penalized compliance score
        initial_compliance_score = 75

        # Step 2: Creator provides legal brand waiver sign-off as counter-evidence
        counter_evidence = {
            "evidence_type": "legal_waiver_signoff",
            "reference_id": "LEGAL-WAIVER-2026-004",
            "justification": "Brand creative director signed off on 8% horizontal stretch for wide billboard format."
        }
        adjudication_result = self.engine.adjudicate_counter_evidence(
            allegation_id=flagged_allegation["id"],
            allegation_category=flagged_allegation["type"],
            counter_evidence=counter_evidence
        )

        # Step 3: Verify allegation dismissed and score restored
        self.assertTrue(adjudication_result["success"])
        self.assertEqual(adjudication_result["adjudication"], "ALLEGATION_REVERTED_AND_DISMISSED")

        delta = adjudication_result["restored_score_delta"]
        self.assertEqual(delta, 15)
        restored_score = min(initial_compliance_score + delta, 100)
        self.assertEqual(restored_score, 90)

    # -------------------------------------------------------------------------
    # 6. Audit Trail Logging Verification
    # -------------------------------------------------------------------------
    def test_audit_trail_logging_on_dismissal(self):
        """Dismissal via REST API writes structured entry with document_hash and timestamp to audit log."""
        initial_log_count = len(server.SUPABASE_MOCK_TABLES["audit_logs"])
        payload = {
            "allegation_id": "v-geom-test-audit",
            "allegation_category": "logo_distortion",
            "counter_evidence": {
                "evidence_type": "influencer_contract_exemption",
                "reference_id": "INF-AGREEMENT-2026-88",
                "justification": "Signed influencer brand guidelines agreement explicitly permitting this variation."
            }
        }

        status, headers, body = HTTPTestClient.post("/api/adjudication/submit", json_data=payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")

        # Verify audit log table received new entry
        current_logs = server.SUPABASE_MOCK_TABLES["audit_logs"]
        self.assertEqual(len(current_logs), initial_log_count + 1)
        latest_entry = current_logs[-1]

        self.assertEqual(latest_entry.get("action"), "ALLEGATION_DISMISSED")
        self.assertEqual(latest_entry.get("actor"), "Compliance Adjudication Engine")
        self.assertEqual(latest_entry.get("role"), "automated_adjudicator")
        self.assertEqual(latest_entry.get("document_hash"), data["result"]["document_hash"])
        self.assertIn("v-geom-test-audit", latest_entry.get("details", ""))
        self.assertIn("INF-AGREEMENT-2026-88", latest_entry.get("details", ""))

    # -------------------------------------------------------------------------
    # 7. In-Memory REST API Contract Tests for POST /api/adjudication/submit
    # -------------------------------------------------------------------------
    def test_api_adjudication_submit_success_valid_evidence(self):
        """POST /api/adjudication/submit returns 200, status=success, and ALLEGATION_REVERTED_AND_DISMISSED."""
        payload = {
            "allegation_id": "allegation-cli-01",
            "allegation_category": "claim",
            "counter_evidence": {
                "evidence_type": "ayush_clinical_registry",
                "reference_id": "AYUSH-REG-2026-904",
                "justification": "Ayush bio-analytical clinical trial certification registered in national registry."
            }
        }
        status, headers, body = HTTPTestClient.post("/api/adjudication/submit", json_data=payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("adjudication"), "ALLEGATION_REVERTED_AND_DISMISSED")
        result = data.get("result", {})
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("restored_score_delta"), 15)
        self.assertEqual(result.get("evidence_type"), "ayush_clinical_registry")

    def test_api_adjudication_submit_insufficient_evidence_returns_rejected(self):
        """POST /api/adjudication/submit returns 200 with status=rejected on insufficient evidence."""
        payload = {
            "allegation_id": "allegation-cli-02",
            "allegation_category": "claim",
            "counter_evidence": {
                "evidence_type": "clinical_trial_certificate",
                "reference_id": "CT-01",
                "justification": "Too short"  # 9 chars -> fails
            }
        }
        status, headers, body = HTTPTestClient.post("/api/adjudication/submit", json_data=payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "rejected")
        self.assertEqual(data.get("adjudication"), "REJECTED_INSUFFICIENT_EVIDENCE")
        result = data.get("result", {})
        self.assertFalse(result.get("success"))
        self.assertIn("min 10 characters", result.get("message", ""))

    def test_api_adjudication_submit_malformed_json_returns_400(self):
        """POST /api/adjudication/submit returns 400 when malformed JSON payload is sent."""
        status, headers, body = HTTPTestClient.post("/api/adjudication/submit", raw_body=b"{broken: json")
        self.assertEqual(status, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "error")
        self.assertIn("Invalid JSON payload", data.get("message", ""))

    def test_api_adjudication_submit_non_dict_payload_returns_400(self):
        """POST /api/adjudication/submit returns 400 when payload is not a JSON object."""
        status, headers, body = HTTPTestClient.post("/api/adjudication/submit", json_data=["list", "payload"])
        self.assertEqual(status, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "error")
        self.assertIn("must be a JSON object", data.get("message", ""))

    def test_api_adjudication_submit_empty_body_rejected_cleanly(self):
        """POST /api/adjudication/submit handles empty object cleanly without 500 server crash."""
        status, headers, body = HTTPTestClient.post("/api/adjudication/submit", json_data={})
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "rejected")
        self.assertEqual(data.get("adjudication"), "REJECTED_INSUFFICIENT_EVIDENCE")

    def test_api_adjudication_submit_codex_prefix_routing(self):
        """POST /codex/api/adjudication/submit correctly routes via path normalizer."""
        payload = {
            "allegation_id": "allegation-route-01",
            "allegation_category": "claim",
            "counter_evidence": {
                "evidence_type": "cdsco_stage4_clearance",
                "reference_id": "CDSCO-ROUTE-2026",
                "justification": "Verified routing via /codex prefix with valid clearance."
            }
        }
        status, headers, body = HTTPTestClient.post("/codex/api/adjudication/submit", json_data=payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("adjudication"), "ALLEGATION_REVERTED_AND_DISMISSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
