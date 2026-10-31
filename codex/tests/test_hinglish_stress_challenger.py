"""
Adversarial Stress Test Suite for Hinglish & Multilingual Advertising Compliance Engine.
Role: Challenger 1 (Milestone 1)
Target: check_hinglish_and_regional_claims in codex/backend/app/core/review_engine.py
        and POST /api/hinglish/check in server.py
"""

import sys
import os
import unittest
import json
import time
import io
from typing import Any, Dict, List, Optional, Tuple

# Ensure backend and root are in sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_path = os.path.abspath(os.path.join(repo_root, "codex", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from app.core.review_engine import DeterministicReviewEngine, deterministic_engine, FindingCandidate
import server


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


class InProcessHTTPClient:
    """Invokes server.RobustVerificationHandler in-memory for testing."""

    @classmethod
    def post(
        cls, path: str, json_data: Optional[dict] = None, raw_body: Optional[bytes] = None
    ) -> Tuple[int, Dict[str, str], bytes]:
        headers = {"Host": "localhost:8000", "Content-Type": "application/json"}
        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
        elif raw_body is not None:
            body = raw_body
        else:
            body = b""
        headers["Content-Length"] = str(len(body))

        header_lines = [f"POST {path} HTTP/1.1"]
        for k, v in headers.items():
            header_lines.append(f"{k}: {v}")
        header_bytes = "\r\n".join(header_lines).encode("utf-8") + b"\r\n\r\n"
        full_req = header_bytes + body

        sock = MockSocket(full_req)
        try:
            server.RobustVerificationHandler(sock, ("127.0.0.1", 54321), MockServer())
        except Exception:
            pass

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


class TestHinglishWhitespaceAndCaseStress(unittest.TestCase):
    """Stress tests variations in whitespace, tabs, newlines, and case."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_uppercase_superlatives_and_claims(self):
        variations = [
            ("CHAMATKARI", "chamatkari"),
            ("Ye CHAMATKAR formula hai", "chamatkar"),
            ("JAD SE KHATAM", "jad se khatam"),
            ("HAMESHA KE LIYE", "hamesha ke liye"),
            ("SHAT PRATISHAT", "shat pratishat"),
            ("EK JHATKE MEIN", "ek jhatke mein"),
            ("RAMBAN ILAJ", "ramban ilaj"),
            ("PAKKA ILAJ", "pakka ilaj"),
            ("BILKUL THEEK", "bilkul theek"),
        ]
        for copy, expected_phrase in variations:
            findings = self.engine.check_hinglish_and_regional_claims(copy)
            self.assertGreaterEqual(
                len(findings), 1,
                f"Failed to detect uppercase claim: '{copy}' for expected '{expected_phrase}'"
            )

    def test_multiple_whitespace_and_tabs_in_claims(self):
        copies = [
            "Jad   Se   Khatam",
            "jad \t se \t\n khatam",
            "jadd   se   khatam",
            "Hamesha   ke   liye",
            "hamesha \t\n ke \t liye",
            "ek   jhatke   mein",
            "ek \t jhatke \n me",
            "ramban   ilaj",
            "raamban \t ilaaj",
            "pakka   ilaj",
            "pakka \t ilaaj",
            "bilkul   theek",
            "bilkul \t thik",
            "100%   asar",
            "100% \t\n asardaar",
        ]
        for copy in copies:
            findings = self.engine.check_hinglish_and_regional_claims(copy)
            self.assertGreaterEqual(
                len(findings), 1,
                f"Failed to detect multi-space/tab claim: '{copy}'"
            )

    def test_colorist_claims_case_and_whitespace(self):
        colorist_variations = [
            ("GORAPAN", "gorapan"),
            ("Gorapan", "gorapan"),
            ("Gora   Rang", "gora rang"),
            ("gore \t rang", "gore rang"),
            ("Rang   Gora", "rang gora"),
            ("rang \t ko \t gora", "rang ko gora"),
            ("FAIRNESS   GUARANTEE", "fairness guarantee"),
            ("Ek   Hafte   Mein   Gora", "ek hafte mein gora"),
            ("ek \t hafte \n me \t gora", "ek hafte me gora"),
            ("Rang   Nikhare", "rang nikhare"),
            ("Rangat \t Nikhare", "rangat nikhare"),
            ("rangat \n nikhar", "rangat nikhar"),
        ]
        for copy, phrase in colorist_variations:
            findings = self.engine.check_hinglish_and_regional_claims(copy)
            rule_ids = [f.rule_id for f in findings]
            self.assertTrue(
                any("COLORIST" in rid for rid in rule_ids),
                f"Failed to detect colorist claim '{copy}' (expected {phrase})"
            )


class TestHinglishSubstringCollisions(unittest.TestCase):
    """Stress tests benign sentences that might collide with substrings."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_benign_asardar_without_superlative(self):
        # 'asardar' by itself without 100% should not be flagged as prohibited absolute cure
        text = "Hamara regular moisturising cream bahut asardar hai."
        findings = self.engine.check_hinglish_and_regional_claims(text)
        self.assertEqual(len(findings), 0, f"False positive triggered for benign 'asardar': {findings}")

    def test_benign_gora_village(self):
        # 'gora' by itself (e.g. place name) without rang/nikhare/gorapan should not trigger colorist violation
        text = "Hamare gora village mein sab kisaan khush hain."
        findings = self.engine.check_hinglish_and_regional_claims(text)
        colorist_findings = [f for f in findings if "COLORIST" in (f.rule_id or "")]
        self.assertEqual(len(colorist_findings), 0, f"False positive for 'gora village': {colorist_findings}")

    def test_commercial_discounts_do_not_trigger_clinical_exaggeration(self):
        # Discounts like 50% off or 20% cashback must NOT be flagged as clinical trial exaggeration
        discounts = [
            "Use code GLOW50 for 50% off on all products #ad",
            "Flat 20% discount on first order with code FIRST20 #vigyapan",
            "Get 30% cashback on purchase today #sponsored",
            "Aaj hi order karein aur 40% chhoot paayein #prayasit",
            "Sale is live: 70% off on complete skincare set #sahyog",
        ]
        for copy in discounts:
            findings = self.engine.check_hinglish_and_regional_claims(copy)
            clinical_findings = [f for f in findings if "CLINICAL" in (f.rule_id or "")]
            self.assertEqual(
                len(clinical_findings), 0,
                f"Commercial discount triggered false clinical exaggeration in '{copy}': {clinical_findings}"
            )

    def test_clean_compliant_hinglish_returns_zero_findings(self):
        clean_copies = [
            "Hamara dermatologist-tested serum skin ko hydrate karta hai #ad",
            "Daily skin routine ke saath visible results dekhein #vigyapan",
            "Skin ko mile 94.2% hydration over 14 days of regular use #sahyog",
            "Natural ingredients se banaya gaya botanical oil #sponsored",
        ]
        for copy in clean_copies:
            findings = self.engine.check_hinglish_and_regional_claims(copy)
            self.assertEqual(len(findings), 0, f"Compliant copy produced unexpected findings: '{copy}' -> {findings}")


class TestHinglishScriptsPunctuationEmojis(unittest.TestCase):
    """Stress tests mixed scripts, punctuation, and emojis."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_emoji_and_punctuation_surrounding_superlatives(self):
        copy = "Arre dosto! 🌟 Ye chamatkari formula deta hai 100% asar aur gora rang! 💥✨ #vigyapan"
        findings = self.engine.check_hinglish_and_regional_claims(copy)
        rule_ids = [f.rule_id for f in findings]
        self.assertIn("HINGLISH-SUPERLATIVE-01", rule_ids)
        self.assertIn("HINGLISH-COLORIST-02", rule_ids)

    def test_parentheses_quotes_and_brackets(self):
        copy = 'Dosto, ye (chamatkari) formula aur [jad se khatam] karne wala "pakka ilaj" hai! #ad'
        findings = self.engine.check_hinglish_and_regional_claims(copy)
        matched_texts = [f.highlighted_text for f in findings]
        self.assertTrue(any("chamatkari" in t for t in matched_texts))
        self.assertTrue(any("jad se khatam" in t for t in matched_texts))
        self.assertTrue(any("pakka ilaj" in t for t in matched_texts))

    def test_mixed_devanagari_and_latin_script(self):
        copy = "Yeh आयुर्वेदिक botanical oil deta hai pakka ilaj aur gorapan! #ad"
        findings = self.engine.check_hinglish_and_regional_claims(copy)
        rule_ids = [f.rule_id for f in findings]
        self.assertIn("HINGLISH-AYUSH-03", rule_ids)
        self.assertIn("HINGLISH-COLORIST-02", rule_ids)


class TestVernacularDisclosures(unittest.TestCase):
    """Stress tests disclosure presence, position, and promotional triggers."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_disclosure_tags_recognized(self):
        tags = ["#vigyapan", "#prayasit", "#sahyog", "#ad", "#sponsored"]
        for tag in tags:
            # Promo with disclosure should NOT trigger missing disclosure finding
            copy = f"Aaj hi order karein aur discount paayein! {tag}"
            findings = self.engine.check_hinglish_and_regional_claims(copy)
            disc_findings = [f for f in findings if f.category == "disclaimer"]
            self.assertEqual(
                len(disc_findings), 0,
                f"Tag '{tag}' at end failed to satisfy disclosure requirement: {disc_findings}"
            )

    def test_disclosure_positions_start_middle_end(self):
        # Start
        copy_start = "#vigyapan Aaj hi order karein link bio mein!"
        f_start = [f for f in self.engine.check_hinglish_and_regional_claims(copy_start) if f.category == "disclaimer"]
        self.assertEqual(len(f_start), 0, "Disclosure at START not recognized")

        # Middle
        copy_mid = "Aaj hi order karein #sahyog link bio mein!"
        f_mid = [f for f in self.engine.check_hinglish_and_regional_claims(copy_mid) if f.category == "disclaimer"]
        self.assertEqual(len(f_mid), 0, "Disclosure in MIDDLE not recognized")

        # End
        copy_end = "Aaj hi order karein link bio mein! #sponsored"
        f_end = [f for f in self.engine.check_hinglish_and_regional_claims(copy_end) if f.category == "disclaimer"]
        self.assertEqual(len(f_end), 0, "Disclosure at END not recognized")

    def test_missing_disclosure_flagged_for_all_promo_triggers(self):
        promo_copies = [
            "Heavy discount available right now!",
            "Is product ko turant khareedo dosto!",
            "Aaj hi order karo limited stock hai!",
            "Loot lo aisi offer baar baar nahi aati!",
            "Code lagao aur bachat paao!",
            "Direct link bio mein milega!",
            "Buy now before stock runs out!",
            "Use code GLOW20 to order now!",
            "Abhi order karein aur fayda dekhein!",
        ]
        for copy in promo_copies:
            findings = self.engine.check_hinglish_and_regional_claims(copy)
            disc_findings = [f for f in findings if f.category == "disclaimer"]
            self.assertEqual(
                len(disc_findings), 1,
                f"Failed to flag missing disclosure for promo copy: '{copy}'"
            )
            self.assertEqual(disc_findings[0].rule_id, "HINGLISH-DISCLOSURE-04")
            self.assertEqual(disc_findings[0].severity, "high")

    def test_non_promotional_copy_without_disclosure_is_not_flagged(self):
        informational_copies = [
            "Yeh cream dermatologically tested botanical ingredients se bani hai.",
            "Winter season mein skin hydration maintain karna zaroori hai.",
            "Hamari research team ne 100 logon par clinical trial conduct kiya.",
        ]
        for copy in informational_copies:
            findings = self.engine.check_hinglish_and_regional_claims(copy)
            disc_findings = [f for f in findings if f.category == "disclaimer"]
            self.assertEqual(
                len(disc_findings), 0,
                f"Non-promotional copy unexpectedly flagged for missing disclosure: '{copy}'"
            )


class TestCrossLingualClinicalExaggeration(unittest.TestCase):
    """Stress tests clinical efficacy comparison, rounding, and timeline."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_exact_clinical_percentage_is_compliant(self):
        # 94.2% exactly matches CS-2026-88
        copy = "Hamare study ke mutabik skin ko mile 94.2% hydration #ad"
        findings = self.engine.check_hinglish_and_regional_claims(copy)
        clinical_findings = [f for f in findings if "CLINICAL" in (f.rule_id or "")]
        self.assertEqual(len(clinical_findings), 0, f"Exact match 94.2% flagged: {clinical_findings}")

    def test_borderline_rounding_flagged_as_medium_severity(self):
        # 94% vs 94.2% (difference 0.2% <= 1.0%)
        copy = "Is serum se mile 94% asar #ad"
        findings = self.engine.check_hinglish_and_regional_claims(copy)
        borderline_findings = [f for f in findings if f.rule_id == "HINGLISH-CLINICAL-BORDERLINE-06"]
        self.assertEqual(len(borderline_findings), 1)
        self.assertEqual(borderline_findings[0].severity, "medium")
        self.assertIn("CS-2026-88", borderline_findings[0].explanation)
        self.assertIn("94.2%", borderline_findings[0].suggested_fix)

    def test_statistical_exaggeration_flagged_as_high_severity(self):
        # 100% vs 94.2% (delta +5.8%)
        copy = "Ye formula deta hai 100% asar skin par #ad"
        findings = self.engine.check_hinglish_and_regional_claims(copy)
        exag_findings = [f for f in findings if f.rule_id == "HINGLISH-CLINICAL-EXAGGERATION-05"]
        self.assertEqual(len(exag_findings), 1)
        self.assertEqual(exag_findings[0].severity, "high")
        self.assertIn("+5.8%", exag_findings[0].explanation)
        self.assertIn("94.2%", exag_findings[0].suggested_fix)

    def test_timeline_compression_check(self):
        # 7 days claimed vs 14 days in clinical study CS-2026-88
        copy = "Sirf 7 din mein acne theek karein #ad"
        findings = self.engine.check_hinglish_and_regional_claims(copy)
        timeline_findings = [f for f in findings if f.rule_id == "HINGLISH-CLINICAL-TIMELINE-07"]
        self.assertEqual(len(timeline_findings), 1)
        self.assertEqual(timeline_findings[0].severity, "high")
        self.assertIn("-7 days", timeline_findings[0].explanation)
        self.assertIn("14 dinon", timeline_findings[0].suggested_fix)

    def test_timeline_compliant_days(self):
        # 14 days and 21 days should NOT trigger timeline compression
        for days in [14, 21, 30]:
            copy = f"Sirf {days} din mein visible acne reduction dekhein #ad"
            findings = self.engine.check_hinglish_and_regional_claims(copy)
            timeline_findings = [f for f in findings if f.rule_id == "HINGLISH-CLINICAL-TIMELINE-07"]
            self.assertEqual(
                len(timeline_findings), 0,
                f"Compliant timeline of {days} days unexpectedly flagged: {timeline_findings}"
            )


class TestBoundaryAndAdversarialInputs(unittest.TestCase):
    """Stress tests boundary inputs, zero-length, extreme length, and Unicode."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_empty_and_whitespace_only(self):
        self.assertEqual(self.engine.check_hinglish_and_regional_claims(""), [])
        self.assertEqual(self.engine.check_hinglish_and_regional_claims("   \t\n   "), [])

    def test_none_input_safe(self):
        self.assertEqual(self.engine.check_hinglish_and_regional_claims(None), [])

    def test_large_input_10k_chars_no_redos_or_hang(self):
        # Construct 10,000+ characters of mixed text
        base_text = "Yeh dermatological serum skin ko hydrate karta hai. Regular use se hydration badhegi. "
        large_text = (base_text * 120) + " Ye chamatkari formula deta hai 100% asar! Aaj hi order karein! #ad"
        self.assertGreater(len(large_text), 10000)

        t0 = time.perf_counter()
        findings = self.engine.check_hinglish_and_regional_claims(large_text)
        elapsed = time.perf_counter() - t0

        self.assertLess(elapsed, 1.0, f"Engine took {elapsed:.3f}s on 10k chars (potential ReDoS)")
        self.assertGreaterEqual(len(findings), 2, "Failed to locate violations in large string")

    def test_massive_input_100k_chars_performance(self):
        # 100,000 characters
        base_text = "Clean Hinglish copy for scale testing and regex backtracking check. "
        massive_text = base_text * 1500
        self.assertGreater(len(massive_text), 100000)

        t0 = time.perf_counter()
        findings = self.engine.check_hinglish_and_regional_claims(massive_text)
        elapsed = time.perf_counter() - t0

        self.assertLess(elapsed, 2.0, f"Engine took {elapsed:.3f}s on 100k chars")
        self.assertEqual(len(findings), 0)

    def test_zero_percent_and_extreme_numbers(self):
        # 0% should not divide by zero or cause unhandled exceptions
        copy = "0% asar aur 0 din mein fayda #ad"
        findings = self.engine.check_hinglish_and_regional_claims(copy)
        self.assertIsInstance(findings, list)

    def test_high_unicode_and_zero_width_chars(self):
        copy = "Ye\u200b chamatkari\u200c formula\ufeff deta hai gorapan\u200d! #ad"
        findings = self.engine.check_hinglish_and_regional_claims(copy)
        self.assertIsInstance(findings, list)


class TestSuggestedFixesQuality(unittest.TestCase):
    """Verifies that all findings provide intent-preserving, non-empty Hinglish rewrites."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_all_rules_provide_hinglish_suggested_fixes(self):
        # Trigger all rules simultaneously
        composite_copy = (
            "Arre dosto! Ye chamatkari formula aur ramban ilaj jad se khatam karega acne ko hamesha ke liye! "
            "Shat pratishat pakka ilaj ek jhatke mein bilkul theek karega. "
            "Gora rang aur fairness guarantee se ek hafte mein gora ho jaoge, rangat nikhare aur gorapan paayein! "
            "100% asar aur sirf 7 din mein results. Aaj hi order karein link bio mein!"
        )
        findings = self.engine.check_hinglish_and_regional_claims(composite_copy)
        self.assertGreaterEqual(len(findings), 10, f"Expected 10+ findings, got {len(findings)}")

        hinglish_markers = ["ke", "mein", "se", "karein", "madad", "sahayak", "anusaar", "behtar", "dinon", "shuru", "gaya", "aur", "ya"]

        for f in findings:
            self.assertIsNotNone(f.suggested_fix, f"Finding {f.rule_id} missing suggested_fix")
            self.assertGreater(len(f.suggested_fix.strip()), 5, f"Finding {f.rule_id} has trivial fix")
            self.assertIsNotNone(f.source_ref, f"Finding {f.rule_id} missing source_ref")
            self.assertGreaterEqual(f.confidence, 0.90, f"Finding {f.rule_id} confidence < 0.90")

        # Verify that the vast majority of findings provide culturally resonant Hinglish particles
        hinglish_markers = ["ke", "mein", "se", "karein", "madad", "sahayak", "anusaar", "behtar", "dinon", "shuru", "gaya", "aur", "ya", "banaye", "apnayein"]
        vernacular_count = sum(
            1 for f in findings if any(marker in f.suggested_fix.lower() for marker in hinglish_markers)
        )
        vernacular_ratio = vernacular_count / len(findings)
        self.assertGreaterEqual(
            vernacular_ratio, 0.80,
            f"Expected at least 80% vernacular suggested fixes, got {vernacular_ratio:.1%} ({vernacular_count}/{len(findings)})"
        )


class TestHinglishAPIEndpoint(unittest.TestCase):
    """Stress tests the REST API POST /api/hinglish/check endpoint."""

    def test_api_valid_request_with_violations(self):
        payload = {
            "text": "Arre dosto! Ye chamatkari formula deta hai 100% asar aur gora rang! Aaj hi order karein link bio mein!",
            "channel": "hinglish_instagram"
        }
        status, _, body_bytes = InProcessHTTPClient.post("/api/hinglish/check", json_data=payload)
        self.assertEqual(status, 200)
        body = json.loads(body_bytes.decode("utf-8"))
        self.assertEqual(body.get("status"), "success")
        self.assertIn("compliance_score", body)
        self.assertIn("findings", body)
        self.assertIn("summary", body)
        self.assertFalse(body["summary"]["is_compliant"])
        self.assertGreaterEqual(body["summary"]["high_severity_count"], 3)
        self.assertLessEqual(body["compliance_score"], 40)

        # Ensure findings have serialized fields properly
        findings = body["findings"]
        for f in findings:
            self.assertIn("id", f)
            self.assertIn("status", f)
            self.assertEqual(f["status"], "open")
            self.assertIn("suggested_fix", f)

    def test_api_compliant_text_returns_100_score(self):
        payload = {
            "text": "Hamara dermatologist-tested serum skin ko hydrate karta hai. Regular use se radiant glow milega. #vigyapan",
            "channel": "hinglish_instagram"
        }
        status, _, body_bytes = InProcessHTTPClient.post("/api/hinglish/check", json_data=payload)
        self.assertEqual(status, 200)
        body = json.loads(body_bytes.decode("utf-8"))
        self.assertEqual(body.get("status"), "success")
        self.assertEqual(body.get("compliance_score"), 100)
        self.assertEqual(len(body.get("findings", [])), 0)
        self.assertTrue(body["summary"]["is_compliant"])

    def test_api_empty_body(self):
        status, _, body_bytes = InProcessHTTPClient.post("/api/hinglish/check", raw_body=b"")
        self.assertEqual(status, 400)
        body = json.loads(body_bytes.decode("utf-8"))
        self.assertEqual(body.get("status"), "error")

    def test_api_invalid_json(self):
        status, _, body_bytes = InProcessHTTPClient.post("/api/hinglish/check", raw_body=b"{invalid_json: true,")
        self.assertEqual(status, 400)
        body = json.loads(body_bytes.decode("utf-8"))
        self.assertEqual(body.get("status"), "error")

    def test_api_missing_text_field(self):
        status, _, body_bytes = InProcessHTTPClient.post("/api/hinglish/check", json_data={"channel": "hinglish_instagram"})
        self.assertEqual(status, 400)
        body = json.loads(body_bytes.decode("utf-8"))
        self.assertEqual(body.get("status"), "error")
        self.assertIn("Field 'text' is required", body.get("message", ""))

    def test_api_non_string_text_field(self):
        status, _, body_bytes = InProcessHTTPClient.post("/api/hinglish/check", json_data={"text": 12345})
        self.assertEqual(status, 400)
        body = json.loads(body_bytes.decode("utf-8"))
        self.assertEqual(body.get("status"), "error")
        self.assertIn("must be a string", body.get("message", ""))


if __name__ == "__main__":
    unittest.main()
