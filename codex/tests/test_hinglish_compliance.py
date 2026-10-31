"""
Comprehensive Unit and Integration Test Suite for Multilingual & Code-Mixed (Hinglish)
Advertising Compliance Engine (Improvement 3: R1, R2, R3, R4, R5, R6).

Test Classes:
1. TestVernacularSuperlativesAndCures (all 9 superlative & cure patterns tested)
2. TestSkinLighteningAndColoristClaims (all 6 colorist patterns tested)
3. TestVernacularPromotionalDisclosures (promotional copy triggers missing disclosure; hashtags suppress violation)
4. TestCrossLingualClinicalComparison (100% asar exaggeration +5.8%, 94% asar borderline -0.2%, 7 din timeline compression, 50% discount commercial shielding)
5. TestCleanHinglishCopy (0 violations, score 100)
6. TestCulturallyResonantSuggestedFixes (all suggested fixes are non-empty and in Hinglish)
7. TestHinglishRESTAPIEndpoints (POST /api/hinglish/check contracts, 400 validations, score bounds [0, 100])
8. TestHinglishOmnichannelEndToEnd (Instagram Caption and Influencer Script sample copies)
9. TestHinglishParity (server SHA256 parity and tri-HTML parity)
10. TestHinglishAdjudicationGatewayE2E (counter-evidence dismissal, 16-hex hash, +15 score restoration, boundary checks, audit log persistence)
11. TestServerChannelCatalog (GET /api/channels returns 6 channels including both Hinglish channels)
"""

import io
import os
import sys
import json
import re
import hashlib
import unittest
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

# Path configuration
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODEX_ROOT = os.path.join(REPO_ROOT, "codex")
BACKEND_DIR = os.path.join(CODEX_ROOT, "backend")

for p in [REPO_ROOT, CODEX_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import server
from app.core.review_engine import (
    DeterministicReviewEngine,
    deterministic_engine,
    FindingCandidate,
    CANONICAL_EVIDENCE_TYPES
)


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


# =============================================================================
# 1. Vernacular Superlatives & Cure Claims (All 9 Patterns)
# =============================================================================
class TestVernacularSuperlativesAndCures(unittest.TestCase):
    """Validates detection of prohibited vernacular superlatives, infallible remedies, permanent cures, and magic claims."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_superlative_100_percent_asar(self):
        """Validates '100% asar' and '100% asardaar' both with and without clinical studies."""
        # A. Without clinical studies (pure vernacular superlative rule)
        findings_pure = self.engine.check_hinglish_and_regional_claims(
            "#vigyapan Formula deta hai 100% asar acne par",
            clinical_studies=[]
        )
        matched_pure = [f for f in findings_pure if "100% asar" in f.highlighted_text.lower()]
        self.assertTrue(len(matched_pure) > 0)
        f_pure = matched_pure[0]
        self.assertEqual(f_pure.category, "hinglish_claim")
        self.assertEqual(f_pure.severity, "high")
        self.assertEqual(f_pure.rule_id, "HINGLISH-SUPERLATIVE-01")
        self.assertEqual(f_pure.source_ref, "Drugs and Magic Remedies Act 1954 §3 / ASCI Vernacular Guidelines 2025 §2.4")
        self.assertEqual(f_pure.suggested_fix, "visible results ke liye regular use karein")

        # Variant '100% asardaar'
        findings_var = self.engine.check_hinglish_and_regional_claims(
            "#vigyapan Yeh 100% asardaar formula hai",
            clinical_studies=[]
        )
        matched_var = [f for f in findings_var if "100% asardaar" in f.highlighted_text.lower()]
        self.assertTrue(len(matched_var) > 0)
        self.assertEqual(matched_var[0].rule_id, "HINGLISH-SUPERLATIVE-01")

        # B. With clinical studies (enriched in-place to clinical exaggeration +5.8%)
        findings_clinical = self.engine.check_hinglish_and_regional_claims(
            "#vigyapan Formula deta hai 100% asar acne par",
            clinical_studies=None  # loads CS-2026-88
        )
        matched_clin = [f for f in findings_clinical if "100% asar" in f.highlighted_text.lower()]
        self.assertTrue(len(matched_clin) > 0)
        f_clin = matched_clin[0]
        self.assertEqual(f_clin.severity, "high")
        self.assertEqual(f_clin.rule_id, "HINGLISH-CLINICAL-EXAGGERATION-05")
        self.assertIn("Drugs and Magic Remedies Act 1954 §3", f_clin.source_ref)
        self.assertIn("CS-2026-88", f_clin.source_ref)
        self.assertIn("Statistical Exaggeration Delta: +5.8%", f_clin.explanation)
        self.assertEqual(f_clin.suggested_fix, "Claim ko 'Clinical trial mein 94.2% hydration asar' se badlein (CS-2026-88)")

    def test_superlative_chamatkari(self):
        """Validates 'chamatkari', 'chamatkar', and 'chamatkarik' variations."""
        variants = ["chamatkari cream", "chamatkar dikhayega", "chamatkarik formula"]
        for v in variants:
            with self.subTest(variant=v):
                findings = self.engine.check_hinglish_and_regional_claims(f"#vigyapan Hamara {v} skin improve karta hai.")
                matched = [f for f in findings if "chamatkar" in f.highlighted_text.lower()]
                self.assertTrue(len(matched) > 0)
                f = matched[0]
                self.assertEqual(f.category, "hinglish_claim")
                self.assertEqual(f.severity, "high")
                self.assertEqual(f.rule_id, "HINGLISH-SUPERLATIVE-01")
                self.assertIn("Drugs and Magic Remedies Act 1954 §3", f.source_ref)
                self.assertEqual(f.suggested_fix, "dermatologist-tested ingredients se banaya gaya")

    def test_superlative_jad_se_khatam(self):
        """Validates 'jad se khatam' and 'jadd se khatam' variations."""
        variants = ["jad se khatam", "jadd se khatam"]
        for v in variants:
            with self.subTest(variant=v):
                findings = self.engine.check_hinglish_and_regional_claims(f"#vigyapan Blemishes ko {v} karega.")
                matched = [f for f in findings if "khatam" in f.highlighted_text.lower()]
                self.assertTrue(len(matched) > 0)
                f = matched[0]
                self.assertEqual(f.rule_id, "HINGLISH-SUPERLATIVE-01")
                self.assertEqual(f.severity, "high")
                self.assertEqual(f.source_ref, "Drugs and Magic Remedies Act 1954 §3 / ASCI Code Ch. 1 §4")
                self.assertEqual(f.suggested_fix, "acne ko kam karne mein madad kare")

    def test_superlative_hamesha_ke_liye(self):
        """Validates 'hamesha ke liye' permanent efficacy claim."""
        findings = self.engine.check_hinglish_and_regional_claims("#vigyapan Wrinkles chale jayenge hamesha ke liye guarantee.")
        matched = [f for f in findings if "hamesha ke liye" in f.highlighted_text.lower()]
        self.assertTrue(len(matched) > 0)
        f = matched[0]
        self.assertEqual(f.rule_id, "HINGLISH-SUPERLATIVE-01")
        self.assertEqual(f.severity, "high")
        self.assertEqual(f.source_ref, "ASCI Code Ch. 1 §4 (Vernacular Substantiation)")
        self.assertEqual(f.suggested_fix, "regular skin routine ke saath lambe samay tak effective")

    def test_superlative_shat_pratishat(self):
        """Validates 'shat pratishat', 'shat-pratishat', and whitespace variants."""
        variants = [
            "shat pratishat asar",
            "shat-pratishat result",
            "shat  pratishat formula",
            "shat\tpratishat asardar"
        ]
        for v in variants:
            with self.subTest(variant=v):
                findings = self.engine.check_hinglish_and_regional_claims(f"#vigyapan Yeh {v} deta hai.")
                matched = [f for f in findings if "shat" in f.highlighted_text.lower()]
                self.assertTrue(len(matched) > 0, f"Failed matching shat pratishat for '{v}'")
                f = matched[0]
                self.assertEqual(f.rule_id, "HINGLISH-SUPERLATIVE-01")
                self.assertEqual(f.severity, "high")
                self.assertEqual(f.source_ref, "ASCI Code Ch. 1 §4 (Vernacular Substantiation)")
                self.assertEqual(f.suggested_fix, "clinically tested aur effective formula")

    def test_superlative_ek_jhatke_mein(self):
        """Validates instantaneous claim 'ek jhatke mein' and 'ek jhatke me'."""
        variants = ["ek jhatke mein acne gayab", "ek jhatke me saaf"]
        for v in variants:
            with self.subTest(variant=v):
                findings = self.engine.check_hinglish_and_regional_claims(f"#vigyapan {v} ho jayega.")
                matched = [f for f in findings if "ek jhatke" in f.highlighted_text.lower()]
                self.assertTrue(len(matched) > 0)
                f = matched[0]
                self.assertEqual(f.rule_id, "HINGLISH-SUPERLATIVE-01")
                self.assertEqual(f.severity, "high")
                self.assertEqual(f.source_ref, "Drugs and Magic Remedies Act 1954 §3 / ASCI Code Ch. 1 §4")
                self.assertEqual(f.suggested_fix, "step-by-step regular skincare routine se")

    def test_cure_ramban_ilaj(self):
        """Validates 'ramban ilaj' and 'raamban ilaaj' infallible remedy claims."""
        variants = ["ramban ilaj", "raamban ilaaj"]
        for v in variants:
            with self.subTest(variant=v):
                findings = self.engine.check_hinglish_and_regional_claims(f"#vigyapan Har skin problem ka {v}.")
                matched = [f for f in findings if ("ramban" in f.highlighted_text.lower() or "raamban" in f.highlighted_text.lower())]
                self.assertTrue(len(matched) > 0)
                f = matched[0]
                self.assertEqual(f.category, "hinglish_claim")
                self.assertEqual(f.severity, "high")
                self.assertEqual(f.rule_id, "HINGLISH-AYUSH-03")
                self.assertEqual(f.source_ref, "AYUSH Advertising Guidelines §3.1 (Traditional Medicine Claims)")
                self.assertEqual(f.suggested_fix, "ayurvedic aur clinically tested botanical formulation")

    def test_cure_pakka_ilaj(self):
        """Validates 'pakka ilaj' and 'pakka ilaaj' guaranteed cure assertions."""
        variants = ["pakka ilaj", "pakka ilaaj"]
        for v in variants:
            with self.subTest(variant=v):
                findings = self.engine.check_hinglish_and_regional_claims(f"#vigyapan Ziddi daago ka {v}.")
                matched = [f for f in findings if "pakka" in f.highlighted_text.lower()]
                self.assertTrue(len(matched) > 0)
                f = matched[0]
                self.assertEqual(f.category, "hinglish_claim")
                self.assertEqual(f.severity, "high")
                self.assertEqual(f.rule_id, "HINGLISH-AYUSH-03")
                self.assertEqual(f.source_ref, "AYUSH Advertising Guidelines §3.1 (Traditional Medicine Claims)")
                self.assertEqual(f.suggested_fix, "dermatologist-tested formulation se skin ki dekhbhal")

    def test_cure_bilkul_theek(self):
        """Validates 'bilkul theek' and 'bilkul thik' cure guarantees."""
        variants = ["bilkul theek", "bilkul thik"]
        for v in variants:
            with self.subTest(variant=v):
                findings = self.engine.check_hinglish_and_regional_claims(f"#vigyapan Aapki skin ko {v} karega.")
                matched = [f for f in findings if "bilkul" in f.highlighted_text.lower()]
                self.assertTrue(len(matched) > 0)
                f = matched[0]
                self.assertEqual(f.category, "hinglish_claim")
                self.assertEqual(f.severity, "high")
                self.assertEqual(f.rule_id, "HINGLISH-AYUSH-03")
                self.assertEqual(f.source_ref, "CDSCO Cosmetics Rules 2020 / AYUSH Guidelines §3.1")
                self.assertEqual(f.suggested_fix, "skin appearance ko behtar banane mein sahayak")

    def test_all_nine_superlatives_simultaneous_coverage(self):
        """Validates all 9 vernacular superlatives extracted simultaneously from composite copy."""
        composite_copy = (
            "#vigyapan Ye chamatkari formula deta hai 100% asardaar result aur shat pratishat asar! "
            "Pimples ko jad se khatam karega hamesha ke liye aur ek jhatke mein safai dega. "
            "Yeh skin ka ramban ilaj aur pakka ilaj hai jo bilkul theek kar dega."
        )
        findings = self.engine.check_hinglish_and_regional_claims(composite_copy, clinical_studies=[])
        superlative_findings = [f for f in findings if f.category == "hinglish_claim"]
        self.assertGreaterEqual(len(superlative_findings), 9)
        for f in superlative_findings:
            self.assertEqual(f.severity, "high")


# =============================================================================
# 2. Skin-Lightening & Colorist Claims (All 6 Patterns)
# =============================================================================
class TestSkinLighteningAndColoristClaims(unittest.TestCase):
    """Validates enforcement of ASCI Skin Lightening & Cosmetic Guidelines 2024 §2.1."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_colorist_gora_rang(self):
        """Validates 'gora rang' and 'gore rang' claims."""
        variants = ["gora rang", "gore rang"]
        for v in variants:
            with self.subTest(variant=v):
                findings = self.engine.check_hinglish_and_regional_claims(f"#vigyapan Paayein {v} sirf 14 din mein.")
                matched = [f for f in findings if "rang" in f.highlighted_text.lower()]
                self.assertTrue(len(matched) > 0)
                f = matched[0]
                self.assertEqual(f.rule_id, "HINGLISH-COLORIST-02")
                self.assertEqual(f.severity, "high")
                self.assertEqual(f.source_ref, "ASCI Skin Lightening & Cosmetic Guidelines 2024 §2.1")
                self.assertEqual(f.suggested_fix, "healthy glowing skin aur hydration")

    def test_colorist_rang_gora(self):
        """Validates 'rang gora' and 'rang ko gora' claims."""
        variants = ["rang gora", "rang ko gora"]
        for v in variants:
            with self.subTest(variant=v):
                findings = self.engine.check_hinglish_and_regional_claims(f"#vigyapan Yeh serum aapke {v} banata hai.")
                matched = [f for f in findings if "gora" in f.highlighted_text.lower()]
                self.assertTrue(len(matched) > 0)
                f = matched[0]
                self.assertEqual(f.rule_id, "HINGLISH-COLORIST-02")
                self.assertEqual(f.severity, "high")
                self.assertEqual(f.source_ref, "ASCI Skin Lightening & Cosmetic Guidelines 2024 §2.1")
                self.assertEqual(f.suggested_fix, "natural skin glow aur even texture")

    def test_colorist_fairness_guarantee(self):
        """Validates 'fairness guarantee' claim and culturally resonant Hinglish rewrite."""
        findings = self.engine.check_hinglish_and_regional_claims("#vigyapan Dete hain complete fairness guarantee.")
        matched = [f for f in findings if "fairness guarantee" in f.highlighted_text.lower()]
        self.assertTrue(len(matched) > 0)
        f = matched[0]
        self.assertEqual(f.rule_id, "HINGLISH-COLORIST-02")
        self.assertEqual(f.severity, "high")
        self.assertEqual(f.source_ref, "ASCI Skin Lightening & Cosmetic Guidelines 2024 §2.1")
        self.assertEqual(f.suggested_fix, "dermatologist-approved formula se skin radiance aur glow")

    def test_colorist_ek_hafte_mein_gora(self):
        """Validates 'ek hafte mein gora' and 'ek hafte me gora' time-bound claims."""
        variants = ["ek hafte mein gora", "ek hafte me gora"]
        for v in variants:
            with self.subTest(variant=v):
                findings = self.engine.check_hinglish_and_regional_claims(f"#vigyapan Paayein {v} chehra.")
                matched = [f for f in findings if "ek hafte" in f.highlighted_text.lower()]
                self.assertTrue(len(matched) > 0)
                f = matched[0]
                self.assertEqual(f.rule_id, "HINGLISH-COLORIST-02")
                self.assertEqual(f.severity, "high")
                self.assertEqual(f.source_ref, "ASCI Skin Lightening & Cosmetic Guidelines 2024 §2.1")
                self.assertEqual(f.suggested_fix, "14 dinon mein visible skin radiance")

    def test_colorist_rang_nikhare(self):
        """Validates 'rang nikhare' and 'rangat nikhare' claims."""
        variants = ["rang nikhare", "rangat nikhare"]
        for v in variants:
            with self.subTest(variant=v):
                findings = self.engine.check_hinglish_and_regional_claims(f"#vigyapan Aapki {v} bina kisi side effect.")
                matched = [f for f in findings if "nikhare" in f.highlighted_text.lower()]
                self.assertTrue(len(matched) > 0)
                f = matched[0]
                self.assertEqual(f.rule_id, "HINGLISH-COLORIST-02")
                self.assertEqual(f.severity, "high")
                self.assertEqual(f.source_ref, "ASCI Skin Lightening & Cosmetic Guidelines 2024 §2.1")
                self.assertEqual(f.suggested_fix, "skin barrier ko hydrate aur healthy banaye")

    def test_colorist_gorapan(self):
        """Validates 'gorapan' claim."""
        findings = self.engine.check_hinglish_and_regional_claims("#vigyapan Asli gorapan paayein iss cream se.")
        matched = [f for f in findings if "gorapan" in f.highlighted_text.lower()]
        self.assertTrue(len(matched) > 0)
        f = matched[0]
        self.assertEqual(f.rule_id, "HINGLISH-COLORIST-02")
        self.assertEqual(f.severity, "high")
        self.assertEqual(f.source_ref, "ASCI Skin Lightening & Cosmetic Guidelines 2024 §2.1")
        self.assertEqual(f.suggested_fix, "natural skin moisture aur healthy radiance")

    def test_all_six_colorist_patterns_coverage(self):
        """Validates all 6 colorist patterns detected with high severity citing ASCI 2024 §2.1."""
        test_phrases = [
            ("gora rang paayein", "gora rang"),
            ("rang gora banaye", "rang gora"),
            ("complete fairness guarantee", "fairness guarantee"),
            ("sirf ek hafte mein gora", "ek hafte mein gora"),
            ("skin ka rang nikhare", "rang nikhare"),
            ("natural gorapan laaye", "gorapan"),
        ]
        for copy, expected_token in test_phrases:
            with self.subTest(phrase=expected_token):
                findings = self.engine.check_hinglish_and_regional_claims(f"#vigyapan {copy}")
                colorist_findings = [f for f in findings if f.rule_id == "HINGLISH-COLORIST-02"]
                self.assertTrue(len(colorist_findings) > 0)
                self.assertEqual(colorist_findings[0].category, "hinglish_claim")
                self.assertEqual(colorist_findings[0].severity, "high")
                self.assertIn("ASCI Skin Lightening & Cosmetic Guidelines 2024 §2.1", colorist_findings[0].source_ref)


# =============================================================================
# 3. Vernacular Promotional Disclosures (ASCI Vernacular Guidelines 2025 §2.4)
# =============================================================================
class TestVernacularPromotionalDisclosures(unittest.TestCase):
    """Validates commercial disclosure tagging under ASCI Vernacular Advertising Guidelines 2025 §2.4."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_promotional_triggers_flagged_without_disclosure(self):
        """Verifies each promotional keyword triggers HINGLISH-DISCLOSURE-04 when hashtags are missing."""
        triggers = [
            "discount",
            "khareedo",
            "aaj hi order",
            "loot lo",
            "code lagao",
            "link bio mein",
            "buy now",
            "use code",
            "order karein"
        ]
        for trigger in triggers:
            with self.subTest(trigger=trigger):
                text = f"Arre dosto! Ye product {trigger} best price par!"
                findings = self.engine.check_hinglish_and_regional_claims(text)
                disclaimer_findings = [f for f in findings if f.category == "disclaimer"]
                self.assertTrue(len(disclaimer_findings) > 0, f"Trigger '{trigger}' failed to flag missing disclosure")
                f = disclaimer_findings[0]
                self.assertEqual(f.severity, "high")
                self.assertEqual(f.rule_id, "HINGLISH-DISCLOSURE-04")
                self.assertEqual(f.source_ref, "ASCI Vernacular Advertising Guidelines 2025 §2.4")
                self.assertEqual(f.suggested_fix, "'#vigyapan' ya '#ad' caption ke shuru mein jodein")

    def test_disclosure_suppression_with_valid_hashtags(self):
        """Verifies all 5 authorized disclosure hashtags (#vigyapan, #prayasit, #sahyog, #ad, #sponsored) suppress violation."""
        hashtags = ["#vigyapan", "#prayasit", "#sahyog", "#ad", "#sponsored"]
        base_copy = "Bhaari discount paayein aaj hi order karein link bio mein"
        for tag in hashtags:
            with self.subTest(hashtag=tag):
                # Tag at beginning
                res_start = self.engine.check_hinglish_and_regional_claims(f"{tag} {base_copy}")
                self.assertEqual(len([f for f in res_start if f.category == "disclaimer"]), 0)

                # Tag at end
                res_end = self.engine.check_hinglish_and_regional_claims(f"{base_copy} {tag}")
                self.assertEqual(len([f for f in res_end if f.category == "disclaimer"]), 0)

    def test_non_promotional_informational_copy_no_violation(self):
        """Verifies purely informational copy without commercial triggers produces 0 disclaimer violations."""
        educational_copy = "Yeh gentle hydrating cleanser skin barrier ko moisture provide karta hai."
        findings = self.engine.check_hinglish_and_regional_claims(educational_copy)
        disclaimer_findings = [f for f in findings if f.category == "disclaimer"]
        self.assertEqual(len(disclaimer_findings), 0)

    def test_disclosure_case_insensitivity_and_placement(self):
        """Verifies uppercase and mixed-case disclosures at various positions suppress violations."""
        tags = ["#VIGYAPAN", "#Ad", "#SPONSORED", "#Prayasit", "#SAHYOG"]
        for tag in tags:
            with self.subTest(tag=tag):
                text = f"Special deal {tag} link bio mein aaj hi order karein"
                findings = self.engine.check_hinglish_and_regional_claims(text)
                self.assertEqual(len([f for f in findings if f.category == "disclaimer"]), 0)


# =============================================================================
# 4. Cross-Lingual Clinical Comparison (CS-2026-88: 94.2% Hydration, 14 Days)
# =============================================================================
class TestCrossLingualClinicalComparison(unittest.TestCase):
    """Validates cross-referencing against registered clinical trial CS-2026-88."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_clinical_exaggeration_over_trial_endpoint(self):
        """Validates statistical exaggeration delta calculation (+5.8% for 100% asar, +3.8% for 98%)."""
        # 100% asar -> +5.8%
        res_100 = self.engine.check_hinglish_and_regional_claims("#vigyapan Serum deta hai 100% asar acne par")
        exagg_100 = [f for f in res_100 if f.rule_id == "HINGLISH-CLINICAL-EXAGGERATION-05"]
        self.assertTrue(len(exagg_100) > 0)
        self.assertEqual(exagg_100[0].severity, "high")
        self.assertIn("Statistical Exaggeration Delta: +5.8%", exagg_100[0].explanation)
        self.assertIn("CS-2026-88", exagg_100[0].source_ref)
        self.assertIn("94.2% hydration asar", exagg_100[0].suggested_fix)

        # 98% asar -> +3.8%
        res_98 = self.engine.check_hinglish_and_regional_claims("#vigyapan Clinical study mein 98% results dekhe gaye")
        exagg_98 = [f for f in res_98 if f.rule_id == "HINGLISH-CLINICAL-EXAGGERATION-05"]
        self.assertTrue(len(exagg_98) > 0)
        self.assertIn("Statistical Exaggeration Delta: +3.8%", exagg_98[0].explanation)

    def test_clinical_borderline_rounding(self):
        """Validates 94% asar triggers borderline medium finding (-0.2% delta)."""
        res_94 = self.engine.check_hinglish_and_regional_claims("#vigyapan 94% asar dekha gaya regular use par")
        borderline = [f for f in res_94 if f.rule_id == "HINGLISH-CLINICAL-BORDERLINE-06"]
        self.assertTrue(len(borderline) > 0)
        f = borderline[0]
        self.assertEqual(f.severity, "medium")
        self.assertIn("claims '94% asar'", f.explanation)
        self.assertIn("observed 94.2% hydration", f.explanation)
        self.assertIn("borderline under ASCI §3.2", f.explanation)
        self.assertIn("Up to 94.2% asar", f.suggested_fix)

    def test_substantiated_exact_endpoint_match_no_violation(self):
        """Verifies exact substantiated clinical endpoint (94.2% hydration) produces 0 clinical findings."""
        text = "#vigyapan Clinical trial (CS-2026-88) ke anusaar 94.2% hydration dekha gaya."
        findings = self.engine.check_hinglish_and_regional_claims(text)
        clinical_flags = [f for f in findings if "CLINICAL" in (f.rule_id or "")]
        self.assertEqual(len(clinical_flags), 0)

    def test_timeline_compression_under_14_days(self):
        """Validates timeline compression delta against 14 days protocol duration."""
        # 7 din -> -7 days
        res_7 = self.engine.check_hinglish_and_regional_claims("#vigyapan Sirf 7 din mein acne khatam ho jayega!")
        tl_7 = [f for f in res_7 if f.rule_id == "HINGLISH-CLINICAL-TIMELINE-07"]
        self.assertTrue(len(tl_7) > 0)
        self.assertEqual(tl_7[0].severity, "high")
        self.assertIn("claims clinical results in 7 din", tl_7[0].explanation)
        self.assertIn("Timeline Compression Delta: -7 days", tl_7[0].explanation)
        self.assertIn("14 dinon mein visible results", tl_7[0].suggested_fix)

        # 3 din -> -11 days
        res_3 = self.engine.check_hinglish_and_regional_claims("#vigyapan Sirf 3 din mein relief paayein!")
        tl_3 = [f for f in res_3 if f.rule_id == "HINGLISH-CLINICAL-TIMELINE-07"]
        self.assertTrue(len(tl_3) > 0)
        self.assertIn("Timeline Compression Delta: -11 days", tl_3[0].explanation)

    def test_timeline_compliant_at_or_above_14_days(self):
        """Verifies timeline >= 14 days produces 0 timeline compression findings."""
        res_14 = self.engine.check_hinglish_and_regional_claims("#vigyapan 14 din mein visible hydration results dekhein.")
        self.assertEqual(len([f for f in res_14 if f.rule_id == "HINGLISH-CLINICAL-TIMELINE-07"]), 0)

        res_21 = self.engine.check_hinglish_and_regional_claims("#vigyapan 21 din mein visible results.")
        self.assertEqual(len([f for f in res_21 if f.rule_id == "HINGLISH-CLINICAL-TIMELINE-07"]), 0)

    def test_commercial_discount_shielding(self):
        """Verifies commercial discount percentages are shielded and never flagged as clinical efficacy claims."""
        commercial_texts = [
            "#vigyapan Paayein 50% discount aaj hi order karein link bio mein",
            "#ad Flat 40% off on all items link bio mein",
            "#sponsored Get 20% cashback today link bio mein",
            "#ad Use code GLOW30 for 30% sale"
        ]
        for copy in commercial_texts:
            with self.subTest(copy=copy):
                findings = self.engine.check_hinglish_and_regional_claims(copy)
                clinical_flags = [f for f in findings if "CLINICAL" in (f.rule_id or "")]
                self.assertEqual(len(clinical_flags), 0, f"Commercial copy falsely flagged clinical: {copy}")


# =============================================================================
# 5. Clean Hinglish Copy
# =============================================================================
class TestCleanHinglishCopy(unittest.TestCase):
    """Validates that fully compliant copy produces 0 violations and 100 compliance score."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_clean_copy_zero_violations_and_100_score(self):
        """Validates clean Hinglish copy returns 0 violations."""
        clean_copy = (
            "#vigyapan #ad Yeh gentle daily face moisturizer skin barrier ko hydrate aur healthy banaye. "
            "Clinical trial (CS-2026-88) ke anusaar 14 dinon mein 94.2% hydration asar dekha gaya."
        )
        findings = self.engine.check_hinglish_and_regional_claims(clean_copy)
        self.assertEqual(len(findings), 0)

    def test_clean_copy_empty_whitespace_none(self):
        """Validates empty string, whitespace, and None safely return empty findings list."""
        self.assertEqual(self.engine.check_hinglish_and_regional_claims(""), [])
        self.assertEqual(self.engine.check_hinglish_and_regional_claims("   \n\t  "), [])
        self.assertEqual(self.engine.check_hinglish_and_regional_claims(None), [])


# =============================================================================
# 6. Culturally Resonant Suggested Fixes
# =============================================================================
class TestCulturallyResonantSuggestedFixes(unittest.TestCase):
    """Validates that every rule produces an intent-preserving, non-empty Hinglish rewrite."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_every_rule_has_non_empty_hinglish_fix(self):
        """Audits all rules in HINGLISH_SUPERLATIVE_RULES and HINGLISH_COLORIST_RULES."""
        for rule in self.engine.HINGLISH_SUPERLATIVE_RULES:
            fix = rule.get("suggested_fix", "")
            self.assertTrue(len(fix.strip()) > 0, f"Rule {rule.get('rule_id')} has empty fix")
            self.assertTrue(
                any(token in fix.lower() for token in ["se", "ke", "aur", "mein", "karein", "madad", "gaya", "dekhbhal", "sahayak"]),
                f"Rule {rule.get('rule_id')} suggested fix '{fix}' lacks Hinglish code-mixed phrasing"
            )

        for rule in self.engine.HINGLISH_COLORIST_RULES:
            fix = rule.get("suggested_fix", "")
            self.assertTrue(len(fix.strip()) > 0, f"Colorist rule {rule.get('rule_id')} has empty fix")
            self.assertTrue(
                any(token in fix.lower() for token in ["se", "aur", "glow", "radiance", "dinon", "ko", "banaye", "mein"]),
                f"Colorist rule {rule.get('rule_id')} suggested fix '{fix}' lacks Hinglish phrasing"
            )

    def test_suggested_fix_intent_preservation(self):
        """Asserts exact intent-preserving Hinglish rewrites for key regulatory concepts."""
        expected_fixes = {
            "chamatkari": "dermatologist-tested ingredients se banaya gaya",
            "jad se khatam": "acne ko kam karne mein madad kare",
            "gora rang": "healthy glowing skin aur hydration",
            "ramban ilaj": "ayurvedic aur clinically tested botanical formulation",
            "pakka ilaj": "dermatologist-tested formulation se skin ki dekhbhal",
            "fairness guarantee": "dermatologist-approved formula se skin radiance aur glow"
        }
        all_rules = self.engine.HINGLISH_SUPERLATIVE_RULES + self.engine.HINGLISH_COLORIST_RULES
        for term, expected_fix in expected_fixes.items():
            matched_rule = next((r for r in all_rules if r["pattern"].search(term)), None)
            self.assertIsNotNone(matched_rule, f"Rule for term '{term}' not found")
            self.assertEqual(matched_rule["suggested_fix"], expected_fix)


# =============================================================================
# 7. REST API Endpoints (POST /api/hinglish/check Contracts)
# =============================================================================
class TestHinglishRESTAPIEndpoints(unittest.TestCase):
    """Validates REST API endpoint contracts using in-memory HTTPTestClient."""

    def test_api_check_valid_violations_payload(self):
        """POST /api/hinglish/check returns 200, status=success, and structured findings."""
        payload = {
            "text": "Chamatkari formula deta hai gora rang! Aaj hi khareedo link bio mein!",
            "channel": "hinglish_instagram"
        }
        status, headers, body = HTTPTestClient.post("/api/hinglish/check", json_data=payload)
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("content-type", ""))

        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["findings"]), 3)  # chamatkari, gora rang, missing disclosure
        self.assertEqual(data["compliance_score"], 40)  # 100 - 3 * 20 = 40
        self.assertEqual(data["summary"]["total_findings"], 3)
        self.assertEqual(data["summary"]["high_severity_count"], 3)
        self.assertFalse(data["summary"]["is_compliant"])

        for f in data["findings"]:
            self.assertTrue(f["id"].startswith("h-claim-"))
            self.assertEqual(f["status"], "open")
            self.assertEqual(f["severity"], "high")
            self.assertTrue(len(f["suggested_fix"]) > 0)

    def test_api_check_clean_copy(self):
        """POST /api/hinglish/check with compliant copy returns 200 and score 100."""
        payload = {
            "text": "Gentle moisturizer skin hydration maintain karne mein sahayak hai. #ad #vigyapan",
            "channel": "hinglish_instagram"
        }
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data=payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["compliance_score"], 100)
        self.assertEqual(len(data["findings"]), 0)
        self.assertTrue(data["summary"]["is_compliant"])

    def test_api_check_400_bad_request_validations(self):
        """Validates 400 Bad Request on empty body, invalid JSON, missing text, non-string text."""
        # Empty body
        s, _, b = HTTPTestClient.post("/api/hinglish/check", raw_body=b"")
        self.assertEqual(s, 400)
        self.assertEqual(json.loads(b.decode("utf-8"))["status"], "error")

        # Malformed JSON
        s, _, b = HTTPTestClient.post("/api/hinglish/check", raw_body=b'{"text": "unterminated')
        self.assertEqual(s, 400)

        # Non-dict JSON
        s, _, b = HTTPTestClient.post("/api/hinglish/check", json_data=["not", "a", "dict"])
        self.assertEqual(s, 400)

        # Empty dict
        s, _, b = HTTPTestClient.post("/api/hinglish/check", json_data={})
        self.assertEqual(s, 400)

        # Missing text field
        s, _, b = HTTPTestClient.post("/api/hinglish/check", json_data={"channel": "instagram"})
        self.assertEqual(s, 400)
        self.assertIn("text", json.loads(b.decode("utf-8"))["message"].lower())

        # Non-string text
        for bad_val in [123, True, 45.6, ["list"], {"nested": "dict"}]:
            with self.subTest(bad_val=bad_val):
                s, _, b = HTTPTestClient.post("/api/hinglish/check", json_data={"text": bad_val})
                self.assertEqual(s, 400)

    def test_api_check_score_bounds_and_clamping(self):
        """Verifies score clamping to bounds [0, 100]."""
        extreme_text = (
            "Arre dosto! Ye chamatkari formula deta hai 100% asar aur gora rang! "
            "Pimples ko jad se khatam karega hamesha ke liye! Shat pratishat asar! "
            "Ye hai ramban ilaj aur pakka ilaj! Aaj hi order karein discount link bio mein!"
        )
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": extreme_text})
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["compliance_score"], 0)
        self.assertFalse(data["summary"]["is_compliant"])

    def test_api_check_path_and_mirror_routing(self):
        """Verifies path normalization (/api/hinglish/check, /codex/api/hinglish/check, trailing slashes, query params)."""
        payload = {"text": "#vigyapan Clean valid copy."}
        paths = [
            "/api/hinglish/check",
            "/codex/api/hinglish/check",
            "/api/hinglish/check/",
            "/api/hinglish/check?client=web&v=2"
        ]
        for path in paths:
            with self.subTest(path=path):
                status, _, body = HTTPTestClient.post(path, json_data=payload)
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body.decode("utf-8"))["status"], "success")

        # GET on check endpoint returns 404
        status_get, _, _ = HTTPTestClient.get("/api/hinglish/check")
        self.assertEqual(status_get, 404)


# =============================================================================
# 8. Omnichannel End-to-End Evaluation
# =============================================================================
class TestHinglishOmnichannelEndToEnd(unittest.TestCase):
    """Validates end-to-end frontend channel draft samples."""

    def test_instagram_caption_channel_sample(self):
        """Validates preloaded sample copy for 'Instagram Caption (Hinglish)' channel."""
        sample_copy = (
            "Hey guys!! DermaCare leke aaya hai chamatkari formula jo dega 100% asar acne par "
            "aur 7 din mein gora rang! Aaj hi order karein link bio mein aur paayein 50% discount!"
        )
        status, _, body = HTTPTestClient.post(
            "/api/hinglish/check",
            json_data={"text": sample_copy, "channel": "hinglish_instagram"}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        findings = data.get("findings", [])

        # Exactly 4 high-severity findings
        self.assertEqual(len(findings), 4)
        self.assertEqual(data["compliance_score"], 20)
        self.assertEqual(data["summary"]["high_severity_count"], 4)
        self.assertFalse(data["summary"]["is_compliant"])

        rule_ids = [f["rule_id"] for f in findings]
        self.assertIn("HINGLISH-SUPERLATIVE-01", rule_ids)  # chamatkari
        self.assertIn("HINGLISH-CLINICAL-EXAGGERATION-05", rule_ids)  # 100% asar
        self.assertIn("HINGLISH-COLORIST-02", rule_ids)  # gora rang
        self.assertIn("HINGLISH-DISCLOSURE-04", rule_ids)  # missing #vigyapan

    def test_influencer_video_script_channel_sample(self):
        """Validates preloaded sample script for 'Influencer Video Script (Hinglish)' channel."""
        sample_script = (
            "Dosto agar aap stubborn acne se pareshan ho toh ye cream hai aapka ramban ilaj! "
            "Ye aapke acne ko jad se khatam karegi hamesha ke liye. "
            "Loot lo ye exclusive deal aaj hi coupon code lagao GLOW50 aur paao bhaari discount link bio mein!"
        )
        status, _, body = HTTPTestClient.post(
            "/api/hinglish/check",
            json_data={"text": sample_script, "channel": "hinglish_influencer"}
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        findings = data.get("findings", [])

        # Exactly 4 high-severity findings
        self.assertEqual(len(findings), 4)
        self.assertEqual(data["compliance_score"], 20)
        self.assertEqual(data["summary"]["high_severity_count"], 4)
        self.assertFalse(data["summary"]["is_compliant"])

        rule_ids = [f["rule_id"] for f in findings]
        self.assertIn("HINGLISH-AYUSH-03", rule_ids)  # ramban ilaj
        self.assertIn("HINGLISH-SUPERLATIVE-01", rule_ids)  # jad se khatam & hamesha ke liye
        self.assertIn("HINGLISH-DISCLOSURE-04", rule_ids)  # missing disclosure


# =============================================================================
# 9. Server SHA256 Parity and Tri-HTML Mirror Parity
# =============================================================================
class TestHinglishParity(unittest.TestCase):
    """Verifies dual-server SHA256 parity and tri-file HTML mirror byte-for-byte parity."""

    def test_server_dual_mirror_sha256_parity(self):
        """Verifies server.py and codex/server.py have exact 100% SHA256 match."""
        root_server = os.path.join(REPO_ROOT, "server.py")
        codex_server = os.path.join(CODEX_ROOT, "server.py")

        self.assertTrue(os.path.isfile(root_server), f"Missing {root_server}")
        self.assertTrue(os.path.isfile(codex_server), f"Missing {codex_server}")

        with open(root_server, "rb") as f1, open(codex_server, "rb") as f2:
            root_bytes = f1.read()
            codex_bytes = f2.read()

        h_root = hashlib.sha256(root_bytes).hexdigest()
        h_codex = hashlib.sha256(codex_bytes).hexdigest()

        self.assertEqual(len(root_bytes), len(codex_bytes), "File size mismatch between server.py and codex/server.py")
        self.assertEqual(h_root, h_codex, f"SHA256 mismatch: {h_root} != {h_codex}")
        self.assertEqual(root_bytes, codex_bytes, "Byte content differs between server.py and codex/server.py")

    def test_tri_file_html_mirror_parity(self):
        """Verifies codex/frontend/index.html, index.html, and docs/index.html are byte-for-byte identical."""
        html_paths = [
            os.path.join(CODEX_ROOT, "frontend", "index.html"),
            os.path.join(REPO_ROOT, "index.html"),
            os.path.join(REPO_ROOT, "docs", "index.html")
        ]

        hashes = []
        sizes = []
        contents = []

        for p in html_paths:
            self.assertTrue(os.path.isfile(p), f"Missing HTML mirror file: {p}")
            with open(p, "rb") as f:
                data = f.read()
            contents.append(data)
            sizes.append(len(data))
            hashes.append(hashlib.sha256(data).hexdigest())

        self.assertEqual(sizes[0], sizes[1], "Size mismatch between codex/frontend and root index.html")
        self.assertEqual(sizes[0], sizes[2], "Size mismatch between codex/frontend and docs/index.html")
        self.assertEqual(hashes[0], hashes[1], "Hash mismatch between codex/frontend and root index.html")
        self.assertEqual(hashes[0], hashes[2], "Hash mismatch between codex/frontend and docs/index.html")
        self.assertEqual(contents[0], contents[1], "Byte content mismatch")
        self.assertEqual(contents[0], contents[2], "Byte content mismatch")

    def test_frontend_contains_hinglish_components(self):
        """Verifies essential Hinglish UI structures and hooks are present in HTML mirror."""
        html_path = os.path.join(REPO_ROOT, "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("activeTab === 'hinglish'", content)
        self.assertIn("Instagram Caption (Hinglish)", content)
        self.assertIn("Influencer Video Script (Hinglish)", content)
        self.assertIn("hinglish_instagram", content)
        self.assertIn("hinglish_influencer", content)
        self.assertIn("handleOpenCounterEvidenceModal(finding, 'hinglish')", content)
        self.assertIn("dismissed_with_evidence", content)
        self.assertIn("hinglishRestoredScoreDelta", content)


# =============================================================================
# 10. Hinglish Adjudication Gateway E2E Flow
# =============================================================================
class TestHinglishAdjudicationGatewayE2E(unittest.TestCase):
    """End-to-End Adjudication Gateway testing for Hinglish claims."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_adjudicate_hinglish_finding_all_canonical_evidence_types(self):
        """Verifies all 6 canonical evidence types successfully dismiss Hinglish allegations."""
        for ev_type in CANONICAL_EVIDENCE_TYPES:
            with self.subTest(evidence_type=ev_type):
                allegation_id = f"h-claim-{ev_type[:4]}-test"
                payload = {
                    "evidence_type": ev_type,
                    "reference_id": f"REF-VER-{ev_type.upper()}-2026",
                    "justification": f"Statutory clinical/regulatory evidence substantiating copy under {ev_type}."
                }
                res = self.engine.adjudicate_counter_evidence(
                    allegation_id=allegation_id,
                    allegation_category="hinglish_claim",
                    counter_evidence=payload
                )

                self.assertTrue(res["success"])
                self.assertEqual(res["adjudication"], "ALLEGATION_REVERTED_AND_DISMISSED")
                self.assertEqual(res["status"], "dismissed_with_evidence")
                self.assertEqual(res["restored_score_delta"], 15)
                self.assertEqual(res["allegation_id"], allegation_id)
                self.assertEqual(res["evidence_type"], ev_type)
                self.assertEqual(len(res["document_hash"]), 16)

                # Validate reversal_timestamp is ISO 8601 UTC
                ts = res["reversal_timestamp"]
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                self.assertIsNotNone(dt)

    def test_deterministic_cryptographic_hash_generation(self):
        """Verifies deterministic 16-hex SHA-256 hash generation for identical inputs."""
        counter_ev = {
            "evidence_type": "ayush_clinical_registry",
            "reference_id": "CTRI-2026-CHAMATKARI",
            "justification": "AYUSH Clinical Registry entry documenting herbal efficacy substantiation."
        }
        expected_raw = f"h-claim-1:{counter_ev['evidence_type']}:{counter_ev['reference_id']}:{counter_ev['justification']}".encode("utf-8")
        expected_hash = hashlib.sha256(expected_raw).hexdigest()[:16]

        res1 = self.engine.adjudicate_counter_evidence("h-claim-1", "hinglish_claim", counter_ev)
        res2 = self.engine.adjudicate_counter_evidence("h-claim-1", "hinglish_claim", counter_ev)

        self.assertEqual(res1["document_hash"], expected_hash)
        self.assertEqual(res2["document_hash"], expected_hash)

    def test_justification_boundary_length_10_chars(self):
        """Boundary analysis: 9 characters fails; 10 characters succeeds."""
        # 9 chars -> rejected
        res_9 = self.engine.adjudicate_counter_evidence("h-1", "hinglish_claim", {
            "evidence_type": "clinical_trial_certificate",
            "reference_id": "REF-01",
            "justification": "123456789"
        })
        self.assertFalse(res_9["success"])
        self.assertEqual(res_9["adjudication"], "REJECTED_INSUFFICIENT_EVIDENCE")
        self.assertIn("min 10 characters", res_9["message"])

        # 10 chars -> dismissed
        res_10 = self.engine.adjudicate_counter_evidence("h-1", "hinglish_claim", {
            "evidence_type": "clinical_trial_certificate",
            "reference_id": "REF-01",
            "justification": "1234567890"
        })
        self.assertTrue(res_10["success"])
        self.assertEqual(res_10["adjudication"], "ALLEGATION_REVERTED_AND_DISMISSED")

    def test_missing_reference_id_and_non_canonical_type_rejection(self):
        """Verifies missing reference ID and non-canonical evidence types are rejected."""
        # Missing reference ID
        res_ref = self.engine.adjudicate_counter_evidence("h-2", "hinglish_claim", {
            "evidence_type": "legal_waiver_signoff",
            "reference_id": "   ",
            "justification": "Substantiating documentation exceeds ten characters."
        })
        self.assertFalse(res_ref["success"])
        self.assertEqual(res_ref["adjudication"], "REJECTED_INSUFFICIENT_EVIDENCE")

        # Invalid evidence type
        res_type = self.engine.adjudicate_counter_evidence("h-2", "hinglish_claim", {
            "evidence_type": "custom_screenshot_proof",
            "reference_id": "REF-02",
            "justification": "Substantiating documentation exceeds ten characters."
        })
        self.assertFalse(res_type["success"])
        self.assertEqual(res_type["adjudication"], "REJECTED_INSUFFICIENT_EVIDENCE")

    def test_e2e_adjudication_score_restoration_cycle(self):
        """E2E flow: Flag Hinglish superlative -> submit counter-evidence -> dismiss -> +15 score restoration."""
        copy = "Ye cream aapka ramban ilaj hai aur 100% asar degi!"
        findings = self.engine.check_hinglish_and_regional_claims(copy, channel="hinglish_instagram")
        self.assertGreaterEqual(len(findings), 1)

        target_finding = next(f for f in findings if f.highlighted_text == "ramban ilaj")
        self.assertEqual(target_finding.category, "hinglish_claim")
        self.assertEqual(target_finding.severity, "high")

        # Initial baseline score with 1 high violation
        initial_score = 80  # 100 - 20 = 80

        # Submit AYUSH clinical trial certificate counter-evidence
        counter_evidence = {
            "evidence_type": "ayush_clinical_registry",
            "reference_id": "CTRI-2026-RAMBAN-09",
            "justification": "Registered AYUSH clinical trial demonstrating statistical efficacy on target endpoints."
        }
        adj_res = self.engine.adjudicate_counter_evidence(
            allegation_id="finding-ramban-1",
            allegation_category=target_finding.category,
            counter_evidence=counter_evidence
        )

        self.assertTrue(adj_res["success"])
        self.assertEqual(adj_res["adjudication"], "ALLEGATION_REVERTED_AND_DISMISSED")
        self.assertEqual(adj_res["status"], "dismissed_with_evidence")
        delta = adj_res["restored_score_delta"]
        self.assertEqual(delta, 15)

        # Restored score calculation
        restored_score = min(100, initial_score + delta)
        self.assertEqual(restored_score, 95)

    def test_api_adjudication_submit_audit_log_persistence(self):
        """POST /api/adjudication/submit logs dismissal event with document_hash to audit trail."""
        initial_logs_count = len(server.SUPABASE_MOCK_TABLES["audit_logs"])

        payload = {
            "allegation_id": "h-claim-audit-e2e",
            "allegation_category": "hinglish_claim",
            "counter_evidence": {
                "evidence_type": "ayush_clinical_registry",
                "reference_id": "AYUSH-REG-2026-AUDIT",
                "justification": "Official AYUSH certification verifying traditional formulation trial clearance."
            }
        }

        status, headers, body = HTTPTestClient.post("/api/adjudication/submit", json_data=payload)
        self.assertEqual(status, 200)

        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("adjudication"), "ALLEGATION_REVERTED_AND_DISMISSED")

        doc_hash = data["result"]["document_hash"]
        self.assertEqual(len(doc_hash), 16)

        # Verify entry in Supabase mock audit logs
        logs = server.SUPABASE_MOCK_TABLES["audit_logs"]
        self.assertEqual(len(logs), initial_logs_count + 1)
        latest_entry = logs[-1]
        self.assertEqual(latest_entry.get("action"), "ALLEGATION_DISMISSED")
        self.assertEqual(latest_entry.get("document_hash"), doc_hash)
        self.assertIn("h-claim-audit-e2e", latest_entry.get("details", ""))
        self.assertIn("AYUSH-REG-2026-AUDIT", latest_entry.get("details", ""))


# =============================================================================
# 11. Server Channel Catalog (GET /api/channels)
# =============================================================================
class TestServerChannelCatalog(unittest.TestCase):
    """Verifies GET /api/channels endpoint returns 6 channels including both Hinglish channels."""

    def test_get_channels_endpoint_status_and_schema(self):
        """GET /api/channels returns 200 with status=success and valid channel list."""
        status, headers, body = HTTPTestClient.get("/api/channels")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("content-type", ""))

        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertIsInstance(data.get("channels"), list)
        self.assertEqual(len(data["channels"]), 6)

    def test_get_channels_includes_hinglish_channels(self):
        """Verifies GET /api/channels includes both Hinglish channels with correct configurations."""
        status, _, body = HTTPTestClient.get("/api/channels")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        channels = data.get("channels", [])
        channel_ids = [c.get("id") for c in channels]

        # 1. Instagram Caption (Hinglish)
        self.assertIn("hinglish_instagram", channel_ids)
        h_insta = next(c for c in channels if c.get("id") == "hinglish_instagram")
        self.assertEqual(h_insta.get("name"), "Instagram Caption (Hinglish)")
        self.assertEqual(h_insta.get("type"), "vernacular_social")
        self.assertEqual(h_insta.get("char_limit"), 2200)
        self.assertEqual(h_insta.get("status"), "active")

        # 2. Influencer Video Script (Hinglish)
        has_influencer = any(c.get("id") in ("hinglish_influencer", "hinglish_influencer_video") for c in channels)
        self.assertTrue(has_influencer, f"Hinglish influencer channel missing from: {channel_ids}")

        h_inf = next(c for c in channels if c.get("id") in ("hinglish_influencer", "hinglish_influencer_video"))
        self.assertEqual(h_inf.get("name"), "Influencer Video Script (Hinglish)")
        self.assertEqual(h_inf.get("type"), "vernacular_script")
        self.assertEqual(h_inf.get("char_limit"), 3500)
        self.assertEqual(h_inf.get("status"), "active")


if __name__ == "__main__":
    unittest.main()
