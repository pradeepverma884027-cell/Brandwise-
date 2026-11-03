"""
Comprehensive Hinglish Compliance Matrix Test Suite for Brandwise Round 3.
Module: codex/tests/test_r3_hinglish_matrix.py

Automated, repeatable Python unittest suite covering the Hinglish compliance matrix:
1. Five Violating Lines:
   - Line 1: 'Yeh cream lagao aur 100% asar paao ek jhatke mein bina kisi side effect ke.'
     Violations: 100% asar (clinical exaggeration / superlative), ek jhatke mein (instantaneous outcome)
   - Line 2: 'Hamara chamatkari ayurvedic tel baalon ko jad se ugata hai hamesha ke liye.'
     Violations: chamatkari (miraculous/magic remedy), jad se (root eradication), hamesha ke liye (permanent cure)
   - Line 3: 'Instant gorapan guarantee! 7 dino mein chehre ka rang badal dega bilkul gora.'
     Violations: gorapan (colorist claim), guarantee (unsubstantiated guarantee), bilkul gora (skin-lightening claim)
   - Line 4: "World's #1 skin cream, doctor certified best formula #collab."
     Violations: World's #1 / #1, best formula (unsubstantiated superlatives without fact register backing)
   - Line 5: '50% off on all products! Aaj hi order karein link bio mein!'
     Violations: Promotional CTA lacking mandatory vernacular disclosure (#विज्ञापन / #ad / #vigyapan)

2. Five Harmless / Compliant Lines (0 false positives, score = 100):
   - Line 1: 'Daily hydration ke liye gentle moisturizer, suitable for sensitive skin. #ad'
   - Line 2: 'Yeh lotion twacha ko dry hone se bachata hai aur fresh feel deta hai. #विज्ञापन'
   - Line 3: 'Humari chai mein hai natural tulsi aur adrak ke swasthya gun. #collab'
   - Line 4: 'Regular sunscreen use karne se sun damage se protection milti hai. #sponsored'
   - Line 5: 'Yeh face wash daily dirt aur excess oil ko clean karne mein madad karta hai.'

3. Vernacular & Latin Spelling Variants:
   - 'asar' vs 'asr' vs 'असर'
   - 'chamatkari' vs 'chamatkarik' vs 'chmatkari' vs 'चमत्कारी'
   - '100% asar' vs '१००% असर' vs '100% asr'
   - 'jad se' vs 'jadd se' vs 'जड़ se' vs 'जड़ से'

4. Mixed Devanagari and Latin Script Phrases:
   - 'DermaCare cream lagane se twacha mein नमी बनी रहती है #विज्ञापन'
   - 'यह आयुर्वेदिक तेल natural herbs se bana hai #ad'

5. Compliant Hinglish Rewrites:
   - Verifies that non-empty culturally resonant suggested fixes are provided for every flagged violation.

6. REST API Endpoint Contracts:
   - POST /api/hinglish/check contracts, status, scoring bounds [0, 100], and summary payload.
"""

import io
import os
import sys
import json
import unittest
from typing import Dict, Any, Tuple, Optional, List

# Configure paths
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODEX_ROOT = os.path.join(REPO_ROOT, "codex")
BACKEND_DIR = os.path.join(CODEX_ROOT, "backend")

for p in [REPO_ROOT, CODEX_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import server
from app.core.review_engine import deterministic_engine


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
    def post(cls, path: str, json_data: Optional[dict] = None) -> Tuple[int, Dict[str, str], bytes]:
        headers = {"Content-Type": "application/json"}
        body = json.dumps(json_data).encode("utf-8") if json_data is not None else b""
        return cls.request("POST", path, headers=headers, body=body)


class TestR3HinglishMatrix(unittest.TestCase):
    """Hinglish Compliance Test Matrix Suite."""

    # -------------------------------------------------------------------------
    # SUITE 1: FIVE VIOLATING LINES
    # -------------------------------------------------------------------------

    def test_violating_line_1_efficacy_and_instantaneous(self):
        """Violating Line 1: Flags 100% asar and ek jhatke mein."""
        line = "Yeh cream lagao aur 100% asar paao ek jhatke mein bina kisi side effect ke."
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": line})
        self.assertEqual(status, 200)

        data = json.loads(body.decode("utf-8"))
        self.assertFalse(data["summary"]["is_compliant"])
        self.assertLess(data["compliance_score"], 100)

        highlighted = [f["highlighted_text"].lower() for f in data["findings"]]
        # 100% asar (clinical exaggeration or superlative)
        self.assertTrue(any("100% asar" in h or "100%" in h for h in highlighted), f"100% asar not in {highlighted}")
        # ek jhatke mein (instantaneous outcome claim)
        self.assertTrue(any("ek jhatke mein" in h for h in highlighted), f"ek jhatke mein not in {highlighted}")

        # Check compliant rewrites
        for f in data["findings"]:
            self.assertTrue(bool(f.get("suggested_fix")), f"Empty suggested_fix in finding {f}")

    def test_violating_line_2_miraculous_root_and_permanent(self):
        """Violating Line 2: Flags chamatkari, jad se, and hamesha ke liye."""
        line = "Hamara chamatkari ayurvedic tel baalon ko jad se ugata hai hamesha ke liye."
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": line})
        self.assertEqual(status, 200)

        data = json.loads(body.decode("utf-8"))
        self.assertFalse(data["summary"]["is_compliant"])
        self.assertLess(data["compliance_score"], 100)

        highlighted = [f["highlighted_text"].lower() for f in data["findings"]]
        # chamatkari (magic remedy)
        self.assertTrue(any("chamatkari" in h for h in highlighted), f"chamatkari not in {highlighted}")
        # jad se (root promise / eradication)
        self.assertTrue(any("jad se" in h for h in highlighted), f"jad se not in {highlighted}")
        # hamesha ke liye (permanent cure)
        self.assertTrue(any("hamesha ke liye" in h for h in highlighted), f"hamesha ke liye not in {highlighted}")

        # Check compliant rewrites
        for f in data["findings"]:
            self.assertTrue(bool(f.get("suggested_fix")), f"Empty suggested_fix in finding {f}")

    def test_violating_line_3_colorist_guarantee_and_complexion(self):
        """Violating Line 3: Flags gorapan and bilkul gora skin-lightening claims."""
        line = "Instant gorapan guarantee! 7 dino mein chehre ka rang badal dega bilkul gora."
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": line})
        self.assertEqual(status, 200)

        data = json.loads(body.decode("utf-8"))
        self.assertFalse(data["summary"]["is_compliant"])
        self.assertLess(data["compliance_score"], 100)

        highlighted = [f["highlighted_text"].lower() for f in data["findings"]]
        # gorapan (colorist / fairness claim)
        self.assertTrue(any("gorapan" in h for h in highlighted), f"gorapan not in {highlighted}")
        # bilkul gora (skin-lightening claim)
        self.assertTrue(any("bilkul gora" in h for h in highlighted), f"bilkul gora not in {highlighted}")

        # Check compliant rewrites
        for f in data["findings"]:
            self.assertTrue(bool(f.get("suggested_fix")), f"Empty suggested_fix in finding {f}")

    def test_violating_line_4_unsubstantiated_superlative(self):
        """Violating Line 4: Flags World's #1 and superlative claims without verified claim backing."""
        line = "World's #1 skin cream, doctor certified best formula #collab."
        # Evaluated through DeterministicReviewEngine superlative and claim audit
        findings = deterministic_engine.check_superlatives_and_claims(line)
        self.assertGreater(len(findings), 0, "Superlative #1 claim was not flagged")

        highlighted = [getattr(f, "highlighted_text", "").lower() for f in findings]
        self.assertTrue(any("#1" in h for h in highlighted), f"#1 not in {highlighted}")

        # Check compliant rewrite provided
        for f in findings:
            fix = getattr(f, "suggested_fix", "")
            self.assertTrue(bool(fix), f"Empty suggested_fix in superlative finding {f}")

    def test_violating_line_5_missing_vernacular_disclosure(self):
        """Violating Line 5: Flags promotional commercial CTA lacking vernacular disclosure."""
        line = "50% off on all products! Aaj hi order karein link bio mein!"
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": line})
        self.assertEqual(status, 200)

        data = json.loads(body.decode("utf-8"))
        self.assertFalse(data["summary"]["is_compliant"])
        self.assertLess(data["compliance_score"], 100)

        # Confirm disclaimer / missing disclosure rule triggered
        rule_ids = [f.get("rule_id") for f in data["findings"]]
        self.assertIn("HINGLISH-DISCLOSURE-04", rule_ids)
        self.assertTrue(any(f.get("category") == "disclaimer" for f in data["findings"]))

        # Check suggested fix mentions #vigyapan or #ad
        finding = next(f for f in data["findings"] if f.get("rule_id") == "HINGLISH-DISCLOSURE-04")
        self.assertTrue(any(tag in finding.get("suggested_fix", "") for tag in ["#vigyapan", "#ad", "vigyapan"]))

    # -------------------------------------------------------------------------
    # SUITE 2: FIVE HARMLESS / COMPLIANT LINES (ZERO FALSE POSITIVES)
    # -------------------------------------------------------------------------

    def test_harmless_lines_zero_false_positives(self):
        """Harmless Lines: All 5 compliant lines must produce 0 false positives, score = 100, is_compliant = True."""
        harmless_cases = [
            ("Daily hydration ke liye gentle moisturizer, suitable for sensitive skin. #ad", "Line 1 with #ad"),
            ("Yeh lotion twacha ko dry hone se bachata hai aur fresh feel deta hai. #विज्ञापन", "Line 2 with #विज्ञापन"),
            ("Humari chai mein hai natural tulsi aur adrak ke swasthya gun. #collab", "Line 3 with #collab"),
            ("Regular sunscreen use karne se sun damage se protection milti hai. #sponsored", "Line 4 with #sponsored"),
            ("Yeh face wash daily dirt aur excess oil ko clean karne mein madad karta hai.", "Line 5 editorial/organic")
        ]

        for text, desc in harmless_cases:
            with self.subTest(description=desc):
                # 1. Direct engine check
                engine_findings = deterministic_engine.check_hinglish_and_regional_claims(text)
                self.assertEqual(len(engine_findings), 0, f"False positive in engine for: '{text}' -> {[f.highlighted_text for f in engine_findings]}")

                # 2. REST API endpoint check
                status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": text})
                self.assertEqual(status, 200)

                data = json.loads(body.decode("utf-8"))
                self.assertEqual(data["compliance_score"], 100, f"Score not 100 for: '{text}' (was {data['compliance_score']})")
                self.assertEqual(len(data["findings"]), 0, f"Findings not empty for: '{text}'")
                self.assertTrue(data["summary"]["is_compliant"])
                self.assertEqual(data["summary"]["total_findings"], 0)

    # -------------------------------------------------------------------------
    # SUITE 3: SPELLING VARIANTS (LATIN & DEVANAGARI)
    # -------------------------------------------------------------------------

    def test_spelling_variants_asar(self):
        """Spelling Variants: '100% asar' vs '100% asr' vs '१००% असर'."""
        variants = [
            ("100% asar", "Yeh lotion deta hai 100% asar #vigyapan"),
            ("100% asr", "Yeh lotion deta hai 100% asr #vigyapan"),
            ("१००% असर", "यह लोशन देता है १००% असर #विज्ञापन")
        ]
        for label, copy in variants:
            with self.subTest(variant=label):
                status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": copy})
                self.assertEqual(status, 200)
                data = json.loads(body.decode("utf-8"))
                self.assertFalse(data["summary"]["is_compliant"], f"Variant {label} was not flagged as violation")
                self.assertLess(data["compliance_score"], 100)

    def test_spelling_variants_chamatkari(self):
        """Spelling Variants: 'chamatkari' vs 'chamatkarik' vs 'chmatkari' vs 'चमत्कारी'."""
        variants = [
            ("chamatkari", "Yeh chamatkari tel baalon ke liye hai #vigyapan"),
            ("chamatkarik", "Yeh chamatkarik formula acne ke liye hai #vigyapan"),
            ("chmatkari", "Yeh chmatkari lepa skin ke liye hai #vigyapan"),
            ("चमत्कारी", "यह चमत्कारी तेल बालों के लिए है #विज्ञापन")
        ]
        for label, copy in variants:
            with self.subTest(variant=label):
                status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": copy})
                self.assertEqual(status, 200)
                data = json.loads(body.decode("utf-8"))
                self.assertFalse(data["summary"]["is_compliant"], f"Variant {label} was not flagged as violation")
                self.assertLess(data["compliance_score"], 100)
                rule_ids = [f.get("rule_id") for f in data["findings"]]
                self.assertIn("HINGLISH-SUPERLATIVE-01", rule_ids)

    def test_spelling_variants_jad_se(self):
        """Spelling Variants: 'jad se' vs 'jadd se' vs 'जड़ se' vs 'जड़ से'."""
        variants = [
            ("jad se", "Hamara tel baalon ko jad se ugata hai #vigyapan"),
            ("jadd se", "Hamara tel baalon ko jadd se ugata hai #vigyapan"),
            ("जड़ se", "Hamara tel baalon ko जड़ se ugata hai #vigyapan"),
            ("जड़ से", "Hamara tel baalon ko जड़ से ugata hai #vigyapan")
        ]
        for label, copy in variants:
            with self.subTest(variant=label):
                status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": copy})
                self.assertEqual(status, 200)
                data = json.loads(body.decode("utf-8"))
                self.assertFalse(data["summary"]["is_compliant"], f"Variant {label} was not flagged as violation")
                self.assertLess(data["compliance_score"], 100)
                rule_ids = [f.get("rule_id") for f in data["findings"]]
                self.assertIn("HINGLISH-SUPERLATIVE-01", rule_ids)

    # -------------------------------------------------------------------------
    # SUITE 4: MIXED DEVANAGARI AND LATIN SCRIPT PHRASES
    # -------------------------------------------------------------------------

    def test_mixed_devanagari_and_latin_script(self):
        """Mixed Script Phrases: Compliant code-mixed sentences produce 0 false positives."""
        mixed_phrases = [
            "DermaCare cream lagane se twacha mein नमी बनी रहती है #विज्ञापन",
            "यह आयुर्वेदिक तेल natural herbs se bana hai #ad"
        ]

        for phrase in mixed_phrases:
            with self.subTest(phrase=phrase):
                status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": phrase})
                self.assertEqual(status, 200)
                data = json.loads(body.decode("utf-8"))
                self.assertEqual(data["compliance_score"], 100, f"Score not 100 for mixed phrase: '{phrase}'")
                self.assertEqual(len(data["findings"]), 0, f"False positive in mixed phrase: '{phrase}'")
                self.assertTrue(data["summary"]["is_compliant"])

    # -------------------------------------------------------------------------
    # SUITE 5: COMPLIANT HINGLISH REWRITES
    # -------------------------------------------------------------------------

    def test_compliant_hinglish_rewrites_integrity(self):
        """Verifies that suggested fixes are culturally resonant Hinglish without prohibited superlatives."""
        test_inputs = [
            "Yeh cream lagao aur 100% asar paao ek jhatke mein! #vigyapan",
            "Hamara chamatkari ayurvedic tel baalon ko jad se ugata hai hamesha ke liye! #vigyapan",
            "Instant gorapan guarantee! Chehre ka rang badal dega bilkul gora! #vigyapan"
        ]

        prohibited_in_fix = ["100% asar", "chamatkari", "jad se khatam", "bilkul theek", "gorapan"]

        for text in test_inputs:
            status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": text})
            self.assertEqual(status, 200)
            data = json.loads(body.decode("utf-8"))
            for f in data.get("findings", []):
                fix = f.get("suggested_fix")
                self.assertIsNotNone(fix)
                self.assertGreater(len(fix), 5, f"Suggested fix too short: '{fix}'")
                # Fix must not contain prohibited superlative terms
                for p_term in prohibited_in_fix:
                    self.assertNotIn(p_term, fix.lower(), f"Suggested fix '{fix}' contains prohibited term '{p_term}'")


if __name__ == "__main__":
    unittest.main()
