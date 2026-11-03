"""
Empirical Challenger Test Suite for Milestone 3 (Task B):
Adversarial Hinglish Variations, Spelling Variants, Vernacular Disclosures,
Fairness Penalty Calibration, and Client/Server Parity.
File: codex/tests/test_challenger_r3_m3_matrix_stress.py
"""

import os
import sys
import json
import unittest

# Configure paths
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODEX_ROOT = os.path.join(REPO_ROOT, "codex")
BACKEND_DIR = os.path.join(CODEX_ROOT, "backend")

for p in [REPO_ROOT, CODEX_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import server
from codex.tests.test_r3_hinglish_matrix import HTTPTestClient
from app.core.review_engine import deterministic_engine


class TestChallengerR3M3MatrixStress(unittest.TestCase):
    """Empirical adversarial stress testing of Hinglish & Devanagari compliance rules."""

    def test_spelling_variants_asar_adversarial(self):
        """Test variations: asar vs asr vs असर and 100% asar vs १००% असर."""
        cases = [
            ("Yeh cream deta hai 100% asar #ad", "100% asar", "Latin standard"),
            ("Yeh cream deta hai 100% asr #ad", "100% asr", "Latin phonetic shorthand"),
            ("यह क्रीम देती है १००% असर #विज्ञापन", "१००% असर", "Native Devanagari"),
            ("Yeh tel deta hai 100% asardaar result #ad", "100% asardaar", "Latin suffix variant"),
            ("यह तेल देता है १००% असरदार रिजल्ट #विज्ञापन", "१००% असरदार", "Devanagari suffix variant")
        ]
        for copy, expected_substr, desc in cases:
            with self.subTest(case=desc):
                status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": copy})
                self.assertEqual(status, 200)
                data = json.loads(body.decode("utf-8"))
                self.assertFalse(data["summary"]["is_compliant"], f"Failed to flag: {copy}")
                self.assertLess(data["compliance_score"], 100)
                rule_ids = [f["rule_id"] for f in data["findings"]]
                self.assertTrue(
                    any(r in ["HINGLISH-SUPERLATIVE-01", "HINGLISH-CLINICAL-EXAGGERATION-05"] for r in rule_ids),
                    f"Unexpected rule IDs: {rule_ids} for {copy}"
                )

    def test_spelling_variants_chamatkari_adversarial(self):
        """Test variations: chamatkari vs chmatkari vs चमत्कारी."""
        cases = [
            ("Yeh chamatkari tel hai baalon ke liye #ad", "chamatkari", "Latin standard"),
            ("Yeh chamatkarik formulation hai #ad", "chamatkarik", "Latin adjectival"),
            ("Yeh chmatkari lepa hai skin ke liye #ad", "chmatkari", "Latin colloquial syncopated"),
            ("यह चमत्कारी तेल है बालों के लिए #विज्ञापन", "चमत्कारी", "Devanagari standard"),
            ("यह चमत्कार फॉर्मूला है #विज्ञापन", "चमत्कार", "Devanagari noun base")
        ]
        for copy, expected_substr, desc in cases:
            with self.subTest(case=desc):
                status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": copy})
                self.assertEqual(status, 200)
                data = json.loads(body.decode("utf-8"))
                self.assertFalse(data["summary"]["is_compliant"], f"Failed to flag: {copy}")
                self.assertLess(data["compliance_score"], 100)
                rule_ids = [f["rule_id"] for f in data["findings"]]
                self.assertIn("HINGLISH-SUPERLATIVE-01", rule_ids)

    def test_spelling_variants_jad_se_adversarial(self):
        """Test variations: jad se vs jadd se vs जड़ से."""
        cases = [
            ("Yeh tel baalon ko jad se ugata hai #ad", "jad se ugata", "Latin single d with verb"),
            ("Yeh tel baalon ko jadd se ugata hai #ad", "jadd se ugata", "Latin double d with verb"),
            ("Yeh baalon ko jad se khatam karega #ad", "jad se khatam", "Latin single d khatam"),
            ("यह बालों को जड़ से उगाता है #विज्ञापन", "जड़ से उगाता", "Devanagari standard with nuqta"),
            ("यह बालों को जड से उगाता है #विज्ञापन", "जड से उगाता", "Devanagari without nuqta"),
            ("Yeh baalon ko जड़ se ugata hai #ad", "जड़ se ugata", "Mixed script root")
        ]
        for copy, expected_substr, desc in cases:
            with self.subTest(case=desc):
                status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": copy})
                self.assertEqual(status, 200)
                data = json.loads(body.decode("utf-8"))
                self.assertFalse(data["summary"]["is_compliant"], f"Failed to flag: {copy}")
                self.assertLess(data["compliance_score"], 100)
                rule_ids = [f["rule_id"] for f in data["findings"]]
                self.assertIn("HINGLISH-SUPERLATIVE-01", rule_ids)

    def test_harmless_copy_with_devanagari_vigyapan_tag(self):
        """Test harmless copy with #विज्ञापन tag: verify score = 100 with zero false positives."""
        harmless_cases = [
            "Yeh lotion twacha ko dry hone se bachata hai aur fresh feel deta hai. #विज्ञापन",
            "DermaCare cream lagane se twacha mein नमी बनी रहती है #विज्ञापन",
            "Humari chai mein hai natural tulsi aur adrak ke swasthya gun. #विज्ञापन",
            "Daily hydration ke liye gentle moisturizer, suitable for sensitive skin. #विज्ञापन",
            "Yeh face wash twacha ko hydrate aur clean karta hai. #विज्ञापन",
            "यह लोशन त्वचा को नमी प्रदान करता है और दिनभर फ्रेश रखता है। #विज्ञापन",
            "प्राकृतिक तत्वों से भरपूर मॉइस्चराइज़र जो त्वचा को कोमल बनाए रखे। #विज्ञापन"
        ]
        for copy in harmless_cases:
            with self.subTest(copy=copy[:40]):
                status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": copy})
                self.assertEqual(status, 200)
                data = json.loads(body.decode("utf-8"))
                self.assertEqual(data["compliance_score"], 100, f"Score != 100 for harmless: '{copy}'")
                self.assertEqual(len(data["findings"]), 0, f"False positives found for: '{copy}' -> {data['findings']}")
                self.assertTrue(data["summary"]["is_compliant"])
                self.assertEqual(data["summary"]["total_findings"], 0)

    def test_promotional_copy_without_disclosure_tag(self):
        """Test promotional copy without #ad/#विज्ञापन: verify HINGLISH-DISCLOSURE-04 is raised."""
        promotional_copies = [
            "50% off on all products! Aaj hi order karein link bio mein!",
            "Loot lo sabhi beauty products! Aaj hi buy now aur payein discount!",
            "Special festival offer: Use code GLOW50 to order karein!",
            "Abhi khareedo aur 20% discount paao! Link bio mein!"
        ]
        for copy in promotional_copies:
            with self.subTest(copy=copy[:40]):
                status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": copy})
                self.assertEqual(status, 200)
                data = json.loads(body.decode("utf-8"))
                self.assertFalse(data["summary"]["is_compliant"])
                self.assertLess(data["compliance_score"], 100)
                rule_ids = [f["rule_id"] for f in data["findings"]]
                self.assertIn("HINGLISH-DISCLOSURE-04", rule_ids, f"Expected HINGLISH-DISCLOSURE-04 in {rule_ids}")

    def test_promotional_copy_with_vernacular_disclosure_tag(self):
        """Test promotional copy WITH #ad/#विज्ञापन: verify HINGLISH-DISCLOSURE-04 is NOT raised."""
        promotional_copies_with_tags = [
            "50% off on all products! Aaj hi order karein link bio mein! #ad",
            "50% off on all products! Aaj hi order karein link bio mein! #विज्ञापन",
            "Loot lo sabhi beauty products! Aaj hi buy now! #collab",
            "Special festival offer: Use code GLOW50 to order karein! #sponsored",
            "Abhi khareedo aur 20% discount paao! Link bio mein! #vigyapan",
            "Abhi khareedo aur 20% discount paao! Link bio mein! #प्रायोजित",
            "Abhi khareedo aur 20% discount paao! Link bio mein! #सहयोग"
        ]
        for copy in promotional_copies_with_tags:
            with self.subTest(copy=copy[:40]):
                status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": copy})
                self.assertEqual(status, 200)
                data = json.loads(body.decode("utf-8"))
                rule_ids = [f["rule_id"] for f in data["findings"]]
                self.assertNotIn(
                    "HINGLISH-DISCLOSURE-04",
                    rule_ids,
                    f"Disclosure tag was present but HINGLISH-DISCLOSURE-04 still raised in {rule_ids}"
                )

    def test_fairness_guarantee_penalty_calibration(self):
        """Test fairness guarantee text: verify score is docked exactly 20 points, not 40 points (score = 80)."""
        fairness_copies = [
            "Hamara cream deta hai fairness guarantee #ad",
            "Yeh lotion twacha ko deta hai fairness guarantee #विज्ञापन",
            "Fairness guarantee for radiant glowing skin #ad",
            "Yeh formula deta hai fairness guarantee #collab"
        ]
        for copy in fairness_copies:
            with self.subTest(copy=copy):
                status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": copy})
                self.assertEqual(status, 200)
                data = json.loads(body.decode("utf-8"))
                # Must be docked exactly 20 points (high severity = -20) -> score = 80
                self.assertEqual(
                    data["compliance_score"],
                    80,
                    f"Score was {data['compliance_score']} instead of 80 for '{copy}'. Findings: {data['findings']}"
                )
                self.assertEqual(
                    len(data["findings"]),
                    1,
                    f"Expected exactly 1 finding (docking 20 pts), but got {len(data['findings'])}: {data['findings']}"
                )
                finding = data["findings"][0]
                self.assertEqual(finding["rule_id"], "HINGLISH-COLORIST-02")
                self.assertEqual(finding["severity"], "high")


if __name__ == "__main__":
    unittest.main()
