"""
Empirical Challenger Test Suite for Milestone 3 (Improvement 3: Hinglish Advertising Compliance Engine).
Role: Challenger 1 (EMPIRICAL CHALLENGER / critic / specialist)
Test Targets:
1. Variations of capitalization, extra whitespace, tabs, and punctuation in Hinglish claims.
2. Punctuation-adjacent hashtags (#vigyapan!, #vigyapan,, #ad., etc.).
3. Boundary percentages (94.1%, 94.2%, 94.3%, 95.0%, 100.0%, etc.).
4. Discount percentages mixed with clinical words (e.g. '50% discount on asardaar formula').
5. Counter-evidence with exactly 9 vs 10 characters in justification (whitespace stripped boundaries).
6. Full verification of existing 49 tests in test_hinglish_compliance.py.
"""

import io
import os
import sys
import json
import re
import hashlib
import unittest
from typing import Dict, Any, Tuple, Optional

# Ensure codex and backend are on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODEX_ROOT = os.path.join(REPO_ROOT, "codex")
BACKEND_DIR = os.path.join(CODEX_ROOT, "backend")

for p in [REPO_ROOT, CODEX_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import server
from app.core.review_engine import DeterministicReviewEngine, deterministic_engine


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


class HTTPTestClient:
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
    def post(cls, path: str, json_data: Any = None) -> Tuple[int, Dict[str, str], bytes]:
        headers = {"Content-Type": "application/json"}
        body = json.dumps(json_data).encode("utf-8")
        return cls.request("POST", path, headers=headers, body=body)


# =============================================================================
# Stress Category 1: Capitalization, Whitespace, Tabs, and Punctuation
# =============================================================================
class TestChallengerCapitalizationWhitespacePunctuation(unittest.TestCase):
    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_uppercase_and_mixedcase_superlatives(self):
        """Tests UPPERCASE and MixedCase variations across all prohibited patterns."""
        cases = [
            ("CHAMATKARI cream", "HINGLISH-SUPERLATIVE-01"),
            ("ChAmAtKaRi formula", "HINGLISH-SUPERLATIVE-01"),
            ("JAD SE KHATAM karega", "HINGLISH-SUPERLATIVE-01"),
            ("Jadd Se Khatam", "HINGLISH-SUPERLATIVE-01"),
            ("HAMESHA KE LIYE relief", "HINGLISH-SUPERLATIVE-01"),
            ("SHAT PRATISHAT result", "HINGLISH-SUPERLATIVE-01"),
            ("EK JHATKE MEIN gayab", "HINGLISH-SUPERLATIVE-01"),
            ("RAMBAN ILAJ hai", "HINGLISH-AYUSH-03"),
            ("RaAmBaN IlAaJ", "HINGLISH-AYUSH-03"),
            ("PAKKA ILAJ milega", "HINGLISH-AYUSH-03"),
            ("BILKUL THEEK ho jayega", "HINGLISH-AYUSH-03"),
            ("BILKUL THIK karein", "HINGLISH-AYUSH-03"),
            ("GORA RANG paayein", "HINGLISH-COLORIST-02"),
            ("RANG GORA banaye", "HINGLISH-COLORIST-02"),
            ("FAIRNESS GUARANTEE dete hain", "HINGLISH-COLORIST-02"),
            ("EK HAFTE MEIN GORA", "HINGLISH-COLORIST-02"),
            ("RANG NIKHARE bina side effect", "HINGLISH-COLORIST-02"),
            ("GORAPAN paayein", "HINGLISH-COLORIST-02"),
        ]
        for phrase, expected_rule in cases:
            with self.subTest(phrase=phrase):
                findings = self.engine.check_hinglish_and_regional_claims(
                    f"#vigyapan {phrase}",
                    clinical_studies=[]
                )
                matched = [f for f in findings if f.rule_id == expected_rule]
                self.assertTrue(len(matched) > 0, f"Failed matching {expected_rule} for: '{phrase}'")

    def test_extra_whitespace_tabs_newlines_in_superlatives(self):
        """Tests claims separated by multiple spaces, tabs, and newlines."""
        cases = [
            ("jad    se    khatam", "HINGLISH-SUPERLATIVE-01"),
            ("jad\tse\tkhatam", "HINGLISH-SUPERLATIVE-01"),
            ("jad\n  se\n  khatam", "HINGLISH-SUPERLATIVE-01"),
            ("hamesha   ke   liye", "HINGLISH-SUPERLATIVE-01"),
            ("hamesha\t\tke\tliye", "HINGLISH-SUPERLATIVE-01"),
            ("shat   pratishat", "HINGLISH-SUPERLATIVE-01"),
            ("shat\tpratishat", "HINGLISH-SUPERLATIVE-01"),
            ("shat - pratishat", "HINGLISH-SUPERLATIVE-01"),
            ("shat-pratishat", "HINGLISH-SUPERLATIVE-01"),
            ("shat \t - \t pratishat", "HINGLISH-SUPERLATIVE-01"),
            ("ek   jhatke   mein", "HINGLISH-SUPERLATIVE-01"),
            ("ramban   ilaj", "HINGLISH-AYUSH-03"),
            ("pakka   ilaj", "HINGLISH-AYUSH-03"),
            ("bilkul   theek", "HINGLISH-AYUSH-03"),
            ("gora   rang", "HINGLISH-COLORIST-02"),
            ("rang   gora", "HINGLISH-COLORIST-02"),
            ("fairness   guarantee", "HINGLISH-COLORIST-02"),
            ("ek   hafte   mein   gora", "HINGLISH-COLORIST-02"),
            ("rang   nikhare", "HINGLISH-COLORIST-02"),
        ]
        for phrase, expected_rule in cases:
            with self.subTest(phrase=phrase):
                findings = self.engine.check_hinglish_and_regional_claims(
                    f"#vigyapan {phrase} acne ko",
                    clinical_studies=[]
                )
                matched = [f for f in findings if f.rule_id == expected_rule]
                self.assertTrue(len(matched) > 0, f"Failed matching {expected_rule} for: '{phrase}'")

    def test_punctuation_enclosed_claims(self):
        """Tests claims wrapped in quotes, parentheses, brackets, or ending in punctuation."""
        cases = [
            ('"chamatkari"', "HINGLISH-SUPERLATIVE-01"),
            ("'chamatkari'", "HINGLISH-SUPERLATIVE-01"),
            ("(chamatkari)", "HINGLISH-SUPERLATIVE-01"),
            ("[chamatkari]", "HINGLISH-SUPERLATIVE-01"),
            ("chamatkari!", "HINGLISH-SUPERLATIVE-01"),
            ("chamatkari, aur best!", "HINGLISH-SUPERLATIVE-01"),
            ("chamatkari?", "HINGLISH-SUPERLATIVE-01"),
            ("chamatkari...", "HINGLISH-SUPERLATIVE-01"),
            ('"jad se khatam"!', "HINGLISH-SUPERLATIVE-01"),
            ('(hamesha ke liye)...', "HINGLISH-SUPERLATIVE-01"),
            ('gora rang.', "HINGLISH-COLORIST-02"),
            ('"fairness guarantee"?', "HINGLISH-COLORIST-02"),
            ('pakka ilaj!', "HINGLISH-AYUSH-03"),
        ]
        for phrase, expected_rule in cases:
            with self.subTest(phrase=phrase):
                findings = self.engine.check_hinglish_and_regional_claims(
                    f"#vigyapan {phrase} formula",
                    clinical_studies=[]
                )
                matched = [f for f in findings if f.rule_id == expected_rule]
                self.assertTrue(len(matched) > 0, f"Failed matching {expected_rule} for: '{phrase}'")


# =============================================================================
# Stress Category 2: Punctuation-Adjacent Hashtags
# =============================================================================
class TestChallengerPunctuationAdjacentHashtags(unittest.TestCase):
    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_punctuation_adjacent_disclosure_hashtags(self):
        """Validates that promotional copy is properly shielded by punctuation-adjacent hashtags."""
        # When promo words like 'discount' or 'buy now' are present, disclosure is mandatory.
        # Check hashtags with trailing punctuation, enclosing quotes/parentheses.
        valid_tags = [
            "#vigyapan!",
            "#vigyapan,",
            "#vigyapan.",
            "#vigyapan;",
            "#vigyapan?",
            "#ad.",
            "#ad!",
            "#ad,",
            "#ad;",
            "#ad?",
            "(#vigyapan)",
            "[#ad]",
            '"#vigyapan"',
            "'#ad'",
            "#prayasit!",
            "#sahyog,",
            "#sponsored.",
        ]
        for tag in valid_tags:
            with self.subTest(tag=tag):
                copy = f"Bhaari discount paayein aaj hi buy now link bio mein {tag}"
                findings = self.engine.check_hinglish_and_regional_claims(copy)
                disclaimer_findings = [f for f in findings if f.category == "disclaimer"]
                self.assertEqual(
                    len(disclaimer_findings), 0,
                    f"Punctuation-adjacent tag '{tag}' failed to suppress missing disclosure violation"
                )

    def test_non_word_boundary_false_hashtag_does_not_suppress(self):
        """Validates that word-character extensions of hashtags (e.g. #advance, #vigyapann) DO NOT suppress disclosure."""
        invalid_tags = [
            "#advance",
            "#advertising",
            "#admire",
            "#vigyapann",
            "#prayasita",
            "#sahyogita",
        ]
        for tag in invalid_tags:
            with self.subTest(tag=tag):
                copy = f"Bhaari discount paayein aaj hi buy now link bio mein {tag}"
                findings = self.engine.check_hinglish_and_regional_claims(copy)
                disclaimer_findings = [f for f in findings if f.category == "disclaimer"]
                self.assertTrue(
                    len(disclaimer_findings) > 0,
                    f"Invalid tag '{tag}' erroneously suppressed missing disclosure violation"
                )


# =============================================================================
# Stress Category 3: Boundary Percentages (CS-2026-88: 94.2% Target)
# =============================================================================
class TestChallengerBoundaryPercentages(unittest.TestCase):
    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_percentage_boundary_evaluations(self):
        """
        Target hydration endpoint in CS-2026-88 is 94.2%.
        - 94.1%: abs(94.1 - 94.2) = 0.1 <= 1.0 and != 94.2 -> BORDERLINE-06 (medium)
        - 94.2%: exact match -> COMPLIANT (0 clinical findings)
        - 94.3%: > 94.2 -> EXAGGERATION-05 (high, delta = +0.1%)
        - 95.0%: > 94.2 -> EXAGGERATION-05 (high, delta = +0.8%)
        - 100.0%: > 94.2 -> EXAGGERATION-05 (high, delta = +5.8%)
        - 93.2%: abs(93.2 - 94.2) = 1.0 <= 1.0 -> BORDERLINE-06 (medium)
        - 93.1%: < 94.2 and abs delta > 1.0 -> COMPLIANT (conservative claim, 0 clinical findings)
        """
        cases = [
            (94.1, "HINGLISH-CLINICAL-BORDERLINE-06", "medium", None),
            (94.2, None, None, None),
            (94.3, "HINGLISH-CLINICAL-EXAGGERATION-05", "high", "+0.1%"),
            (95.0, "HINGLISH-CLINICAL-EXAGGERATION-05", "high", "+0.8%"),
            (100.0, "HINGLISH-CLINICAL-EXAGGERATION-05", "high", "+5.8%"),
            (93.2, "HINGLISH-CLINICAL-BORDERLINE-06", "medium", None),
            (93.1, None, None, None),
            (94.20, None, None, None),  # trailing zero representation
        ]

        for pct, expected_rule, expected_sev, expected_delta in cases:
            with self.subTest(pct=pct):
                copy = f"#vigyapan Clinical study ke anusaar {pct}% hydration asar dekha gaya."
                findings = self.engine.check_hinglish_and_regional_claims(copy)
                clinical_findings = [f for f in findings if "CLINICAL" in (f.rule_id or "")]

                if expected_rule is None:
                    self.assertEqual(
                        len(clinical_findings), 0,
                        f"Expected compliant (0 clinical findings) for {pct}%, but got: {clinical_findings}"
                    )
                else:
                    self.assertTrue(
                        len(clinical_findings) > 0,
                        f"Expected {expected_rule} for {pct}%, but got no clinical findings"
                    )
                    f = clinical_findings[0]
                    self.assertEqual(f.rule_id, expected_rule)
                    self.assertEqual(f.severity, expected_sev)
                    if expected_delta:
                        self.assertIn(f"Statistical Exaggeration Delta: {expected_delta}", f.explanation)


# =============================================================================
# Stress Category 4: Discount Percentages Mixed with Clinical Words
# =============================================================================
class TestChallengerDiscountPercentagesMixedWithClinical(unittest.TestCase):
    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_discount_percentages_on_asardaar_formula(self):
        """
        '50% discount on asardaar formula #ad'
        - '50%' is a commercial discount -> shielded from clinical exaggeration.
        - 'asardaar' alone is not '100% asar' -> no superlative finding.
        - '#ad' is present -> no missing disclosure.
        Result: exactly 0 violations!
        """
        copy = "50% discount on asardaar formula #ad"
        findings = self.engine.check_hinglish_and_regional_claims(copy)
        self.assertEqual(len(findings), 0, f"Expected 0 findings for clean discount copy, got: {findings}")

    def test_discount_mixed_with_clinical_and_superlative_combinations(self):
        """Tests variations of commercial percentages with clinical terms."""
        cases = [
            # 1. 50% discount on authentic clinical hydration formula (compliant)
            (
                "50% discount on 94.2% hydration formula #vigyapan",
                0,  # 50% shielded, 94.2% compliant endpoint, #vigyapan present
                None
            ),
            # 2. 50% off on chamatkari formula #vigyapan
            (
                "Paayein 50% off on chamatkari formula #vigyapan",
                1,  # 50% shielded, chamatkari flagged, #vigyapan present
                "HINGLISH-SUPERLATIVE-01"
            ),
            # 3. 50% discount without hashtag -> missing disclosure flagged, discount shielded
            (
                "Get 50% discount on asardaar formula link bio mein",
                1,  # missing disclosure flagged, discount NOT flagged as clinical
                "HINGLISH-DISCLOSURE-04"
            ),
            # 4. Multiple commercial percentages
            (
                "#ad Flat 50% discount and 20% cashback on asardaar formula",
                0,  # both commercial % shielded, no superlative, #ad present
                None
            ),
        ]

        for copy, expected_count, expected_rule in cases:
            with self.subTest(copy=copy):
                findings = self.engine.check_hinglish_and_regional_claims(copy)
                self.assertEqual(
                    len(findings), expected_count,
                    f"Unexpected findings count ({len(findings)} != {expected_count}) for '{copy}': {findings}"
                )
                if expected_rule:
                    rule_ids = [f.rule_id for f in findings]
                    self.assertIn(expected_rule, rule_ids)
                # Verify that commercial % was NEVER flagged as clinical
                for f in findings:
                    if "50%" in (f.highlighted_text or "") or "20%" in (f.highlighted_text or ""):
                        self.assertNotIn("CLINICAL", f.rule_id or "")


# =============================================================================
# Stress Category 5: Counter-Evidence Justification Exactly 9 vs 10 Chars
# =============================================================================
class TestChallengerCounterEvidenceJustificationBoundary(unittest.TestCase):
    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_justification_strictly_below_10_rejected(self):
        """Boundary test: justifications with lengths 0 to 9 chars must fail."""
        failing_justifications = [
            "",             # len 0
            "a",            # len 1
            "12345",        # len 5
            "12345678",     # len 8
            "123456789",    # len 9
            "Valid doc",    # len 9
            "Clinical!",    # len 9
            "   123456789   ",  # stripped len 9
            "\t123456789\n",    # stripped len 9
            "  nine ch  ",       # stripped len 7
        ]
        for just in failing_justifications:
            with self.subTest(justification=just):
                payload = {
                    "evidence_type": "clinical_trial_certificate",
                    "reference_id": "CT-2026-TEST",
                    "justification": just
                }
                # Direct review engine
                res = self.engine.adjudicate_counter_evidence(
                    "allegation-test-9", "hinglish_claim", payload
                )
                self.assertFalse(res["success"])
                self.assertEqual(res["adjudication"], "REJECTED_INSUFFICIENT_EVIDENCE")
                self.assertIn("min 10 characters", res["message"])

                # REST API endpoint /api/adjudication/submit
                api_payload = {
                    "allegation_id": "allegation-test-9",
                    "allegation_category": "hinglish_claim",
                    "counter_evidence": payload
                }
                status, _, body = HTTPTestClient.post("/api/adjudication/submit", json_data=api_payload)
                self.assertEqual(status, 200)
                data = json.loads(body.decode("utf-8"))
                self.assertEqual(data.get("adjudication"), "REJECTED_INSUFFICIENT_EVIDENCE")
                self.assertFalse(data.get("result", {}).get("success", True))

    def test_justification_at_or_above_10_accepted(self):
        """Boundary test: justifications with length 10 or more must succeed."""
        passing_justifications = [
            "1234567890",         # exactly 10
            "Valid doc!",         # exactly 10
            "Clinical!1",         # exactly 10
            "   1234567890   ",   # stripped len 10
            "\n1234567890\t",     # stripped len 10
            "12345678901",        # len 11
            "Clinical trial report substantiates all claims properly.", # len > 10
        ]
        for just in passing_justifications:
            with self.subTest(justification=just):
                payload = {
                    "evidence_type": "clinical_trial_certificate",
                    "reference_id": "CT-2026-TEST",
                    "justification": just
                }
                # Direct review engine
                res = self.engine.adjudicate_counter_evidence(
                    "allegation-test-10", "hinglish_claim", payload
                )
                self.assertTrue(res["success"], f"Expected success for len {len(just.strip())}: '{just}'")
                self.assertEqual(res["adjudication"], "ALLEGATION_REVERTED_AND_DISMISSED")
                self.assertEqual(res["status"], "dismissed_with_evidence")
                self.assertEqual(res["restored_score_delta"], 15)
                self.assertEqual(len(res["document_hash"]), 16)

                # REST API endpoint /api/adjudication/submit
                api_payload = {
                    "allegation_id": "allegation-test-10",
                    "allegation_category": "hinglish_claim",
                    "counter_evidence": payload
                }
                status, _, body = HTTPTestClient.post("/api/adjudication/submit", json_data=api_payload)
                self.assertEqual(status, 200)
                data = json.loads(body.decode("utf-8"))
                self.assertEqual(data.get("adjudication"), "ALLEGATION_REVERTED_AND_DISMISSED")
                self.assertTrue(data.get("result", {}).get("success", False))


# =============================================================================
# Stress Category 6: End-to-End Adversarial Payload Stress & Parity
# =============================================================================
class TestChallengerAdversarialEndToEnd(unittest.TestCase):
    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_unicode_hindi_mixed_with_latin_hinglish(self):
        """Tests that Latin regexes gracefully handle Devanagari Unicode characters without crashing."""
        mixed_text = "Yeh #vigyapan अद्भुत cream hai jo deta hai 100% asar aur gora rang!"
        findings = self.engine.check_hinglish_and_regional_claims(mixed_text)
        rule_ids = [f.rule_id for f in findings]
        self.assertIn("HINGLISH-CLINICAL-EXAGGERATION-05", rule_ids)
        self.assertIn("HINGLISH-COLORIST-02", rule_ids)

    def test_rapid_score_deductions_floor_at_zero(self):
        """Ensures that many simultaneous violations correctly clamp score to 0 and do not go negative."""
        extreme_text = (
            "Chamatkari formula! 100% asar! Jad se khatam! Hamesha ke liye! "
            "Shat pratishat! Ek jhatke mein! Ramban ilaj! Pakka ilaj! Bilkul theek! "
            "Gora rang! Rang gora! Fairness guarantee! Ek hafte mein gora! Rang nikhare! Gorapan! "
            "Discount link bio mein aaj hi order karein!"
        )
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": extreme_text})
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["compliance_score"], 0)
        self.assertGreaterEqual(len(data["findings"]), 10)


if __name__ == "__main__":
    unittest.main()
