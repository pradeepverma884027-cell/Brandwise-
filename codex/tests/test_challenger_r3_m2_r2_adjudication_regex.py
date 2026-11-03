"""
Adversarial Challenger Test Suite: Milestone 2 Iteration 2 (Challenger 2)
Focus: Adjudication Policy Relevance & Regex Parity

Verifies:
1. Adjudication Policy Relevance:
   - Irrelevant evidence (legal_waiver_signoff for clinical_efficacy) -> REJECTED_POLICY_IRRELEVANT
   - Relevant evidence (clinical_trial_certificate for clinical_efficacy) -> ALLEGATION_REVERTED_AND_DISMISSED (+15 pts)
   - Comprehensive matrix of permissible vs impermissible evidence types for clinical_efficacy
   - REST API parity for /api/adjudication/submit
2. Regex Parity:
   - Execution of test_challenger_imp3_m4_docs_offline.js (144 assertions pass)
   - "fairness guarantee" text docked exactly 20 points (not 40) in both Python engine and docs/index.html simulation
3. Devanagari Hindi text & #विज्ञापन hashtag:
   - #विज्ञापन hashtag produces 0 false positives (clean copy, standalone, promotional disclosure)
   - Violating Devanagari Hindi phrases (superlatives, absolute cures, colorist claims) are properly flagged
"""

import os
import sys
import json
import subprocess
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODEX_ROOT = os.path.join(REPO_ROOT, "codex")
BACKEND_DIR = os.path.join(CODEX_ROOT, "backend")

for p in [REPO_ROOT, CODEX_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.core.review_engine import DeterministicReviewEngine
from tests.test_adjudication import HTTPTestClient


class TestAdjudicationPolicyRelevance(unittest.TestCase):
    """Adversarial stress-testing of interactive counter-evidence policy relevance."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_irrelevant_evidence_type_rejected(self):
        """Confirm evidence_type='legal_waiver_signoff' for allegation_category='clinical_efficacy' is REJECTED."""
        res = self.engine.adjudicate_counter_evidence(
            allegation_id="alg-clin-irr-01",
            allegation_category="clinical_efficacy",
            counter_evidence={
                "evidence_type": "legal_waiver_signoff",
                "reference_id": "WAIVER-CORP-99",
                "justification": "Legal department waiver provided for billboard copy claim."
            }
        )
        self.assertFalse(res["success"])
        self.assertEqual(res["adjudication"], "REJECTED_POLICY_IRRELEVANT")
        self.assertEqual(res["allegation_id"], "alg-clin-irr-01")
        self.assertEqual(res["allegation_category"], "clinical_efficacy")
        self.assertEqual(res["evidence_type"], "legal_waiver_signoff")
        self.assertIn("not relevant to allegation category 'clinical_efficacy'", res["message"])

    def test_relevant_evidence_type_accepted_and_restores_15_points(self):
        """Confirm evidence_type='clinical_trial_certificate' for allegation_category='clinical_efficacy' is ACCEPTED."""
        res = self.engine.adjudicate_counter_evidence(
            allegation_id="alg-clin-rel-01",
            allegation_category="clinical_efficacy",
            counter_evidence={
                "evidence_type": "clinical_trial_certificate",
                "reference_id": "CTRI-2026-CERT-904",
                "justification": "Clinical trial certificate verifying 94.2% hydration protocol on 120 subjects."
            }
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["adjudication"], "ALLEGATION_REVERTED_AND_DISMISSED")
        self.assertEqual(res["allegation_id"], "alg-clin-rel-01")
        self.assertEqual(res["allegation_category"], "clinical_efficacy")
        self.assertEqual(res["evidence_type"], "clinical_trial_certificate")
        self.assertEqual(res["restored_score_delta"], 15)
        self.assertEqual(len(res["document_hash"]), 16)
        self.assertIn("reversal_timestamp", res)

    def test_clinical_efficacy_evidence_matrix_completeness(self):
        """Stress-test all canonical evidence types against clinical_efficacy policy requirements."""
        permissible_types = [
            "clinical_trial_certificate",
            "cdsco_stage4_clearance",
            "lab_assay_report",
            "ayush_clinical_registry"
        ]
        impermissible_types = [
            "legal_waiver_signoff",
            "influencer_contract_exemption",
            "agency_authorization"
        ]

        for p_type in permissible_types:
            with self.subTest(permissible_type=p_type):
                res = self.engine.adjudicate_counter_evidence(
                    allegation_id=f"alg-{p_type}",
                    allegation_category="clinical_efficacy",
                    counter_evidence={
                        "evidence_type": p_type,
                        "reference_id": f"REF-{p_type.upper()}-01",
                        "justification": f"Valid clinical substantiation documentation for {p_type}."
                    }
                )
                self.assertTrue(res["success"], f"Expected {p_type} to be accepted for clinical_efficacy")
                self.assertEqual(res["adjudication"], "ALLEGATION_REVERTED_AND_DISMISSED")
                self.assertEqual(res["restored_score_delta"], 15)

        for i_type in impermissible_types:
            with self.subTest(impermissible_type=i_type):
                res = self.engine.adjudicate_counter_evidence(
                    allegation_id=f"alg-{i_type}",
                    allegation_category="clinical_efficacy",
                    counter_evidence={
                        "evidence_type": i_type,
                        "reference_id": f"REF-{i_type.upper()}-01",
                        "justification": f"Non-clinical documentation presented for {i_type}."
                    }
                )
                self.assertFalse(res["success"], f"Expected {i_type} to be rejected for clinical_efficacy")
                self.assertEqual(res["adjudication"], "REJECTED_POLICY_IRRELEVANT")

    def test_api_adjudication_policy_relevance(self):
        """Verify REST API /api/adjudication/submit enforces policy relevance."""
        # Impermissible -> 200 with status=rejected, adjudication=REJECTED_POLICY_IRRELEVANT
        status, headers, body = HTTPTestClient.post(
            "/api/adjudication/submit",
            json_data={
                "allegation_id": "alg-api-irr",
                "allegation_category": "clinical_efficacy",
                "counter_evidence": {
                    "evidence_type": "legal_waiver_signoff",
                    "reference_id": "WAIVER-01",
                    "justification": "Legal waiver for clinical claim."
                }
            }
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "rejected")
        self.assertEqual(data.get("adjudication"), "REJECTED_POLICY_IRRELEVANT")

        # Permissible -> 200 with status=success, adjudication=ALLEGATION_REVERTED_AND_DISMISSED
        status, headers, body = HTTPTestClient.post(
            "/api/adjudication/submit",
            json_data={
                "allegation_id": "alg-api-rel",
                "allegation_category": "clinical_efficacy",
                "counter_evidence": {
                    "evidence_type": "clinical_trial_certificate",
                    "reference_id": "CTRI-01",
                    "justification": "Clinical trial certificate substantiating efficacy."
                }
            }
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("adjudication"), "ALLEGATION_REVERTED_AND_DISMISSED")
        self.assertEqual(data["result"]["restored_score_delta"], 15)


class TestRegexParityAndFairnessGuarantee(unittest.TestCase):
    """Verifies regex parity test suite and fairness guarantee scoring behavior."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_offline_docs_test_suite_passes_all_144_assertions(self):
        """Run node codex/tests/test_challenger_imp3_m4_docs_offline.js and confirm 144 assertions pass (0 failures)."""
        js_path = os.path.join(REPO_ROOT, "codex", "tests", "test_challenger_imp3_m4_docs_offline.js")
        proc = subprocess.run(["node", js_path], capture_output=True, text=True, cwd=REPO_ROOT)
        self.assertEqual(proc.returncode, 0, f"Node test suite failed with error:\n{proc.stderr}")
        self.assertIn("TOTAL ASSERTIONS: 144", proc.stdout)
        self.assertIn("PASSED: 144", proc.stdout)
        self.assertIn("FAILED: 0", proc.stdout)
        self.assertIn("VERDICT: ALL OFFLINE GITHUB PAGES CHALLENGES PASSED (APPROVE)", proc.stdout)

    def test_fairness_guarantee_docked_exactly_20_points_not_40(self):
        """Test 'fairness guarantee' text: confirm it is docked exactly 20 points, not 40."""
        samples = [
            "fairness guarantee",
            "fairness guarantee #vigyapan",
            "#vigyapan Dete hain complete fairness guarantee.",
            "Hamari cream deti hai fairness guarantee bina kisi side effect #ad"
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                findings = self.engine.check_hinglish_and_regional_claims(sample)
                # Should match only colorist rule (HINGLISH-COLORIST-02), NOT duplicate match on 'guarantee'
                colorist_matches = [f for f in findings if f.rule_id == "HINGLISH-COLORIST-02"]
                superlative_matches = [f for f in findings if f.rule_id == "HINGLISH-SUPERLATIVE-01" and "guarantee" in f.highlighted_text.lower()]

                self.assertEqual(len(colorist_matches), 1, f"Expected exactly 1 colorist finding for '{sample}', got {len(colorist_matches)}")
                self.assertEqual(len(superlative_matches), 0, f"Expected 0 superlative findings for 'guarantee' in '{sample}', got {len(superlative_matches)}")

                # Calculate score
                score = 100
                for f in findings:
                    sev = (f.severity or "high").lower()
                    if sev in ("high", "critical"):
                        score -= 20
                    elif sev == "medium":
                        score -= 10
                    else:
                        score -= 5

                docked = 100 - score
                self.assertEqual(docked, 20, f"Expected exactly 20 points docked for '{sample}', but got {docked} points docked (score={score})")


class TestDevanagariHindiAndVigyapanHashtag(unittest.TestCase):
    """Verifies Devanagari Hindi text handling and zero false positives for #विज्ञापन hashtag."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    def test_vigyapan_hashtag_zero_false_positives(self):
        """Confirm #विज्ञापन produces 0 false positives across multiple contexts."""
        clean_samples = [
            "#विज्ञापन",
            "DermaCare skin hydration ke liye daily cream. #विज्ञापन",
            "यह क्रीम त्वचा को नमी प्रदान करती है और त्वचा स्वस्थ रखती है। #विज्ञापन",
            "दैनिक उपयोग के लिए सुरक्षित फॉर्मूलेशन। #विज्ञापन",
            "DermaCare par 50% discount! Aaj hi order karein link bio mein! #विज्ञापन",
            "आज ही 50% छूट पर खरीदें! लिंक बायो में देखें! #विज्ञापन",
            "#विज्ञापन प्राकृतिक अवयवों से भरपूर मॉइस्चराइज़र।"
        ]
        for sample in clean_samples:
            with self.subTest(sample=sample):
                findings = self.engine.check_hinglish_and_regional_claims(sample)
                self.assertEqual(
                    len(findings), 0,
                    f"False positive detected on clean sample '{sample}': {[f.explanation for f in findings]}"
                )

    def test_promotional_copy_without_vigyapan_is_flagged(self):
        """Confirm promotional copy without #विज्ञापन is flagged for missing commercial disclosure."""
        unflagged_promo_samples = [
            "DermaCare par 50% discount! Aaj hi order karein link bio mein!",
            "आज ही 50% छूट पर खरीदें! लिंक बायो में देखें!"
        ]
        for sample in unflagged_promo_samples:
            with self.subTest(sample=sample):
                findings = self.engine.check_hinglish_and_regional_claims(sample)
                disclosure_findings = [f for f in findings if f.rule_id == "HINGLISH-DISCLOSURE-04"]
                self.assertEqual(
                    len(disclosure_findings), 1,
                    f"Expected HINGLISH-DISCLOSURE-04 finding on '{sample}', but got none"
                )

    def test_violating_devanagari_hindi_text_is_flagged(self):
        """Confirm violating Devanagari Hindi text is properly flagged across all rule categories."""
        violating_samples = [
            ("यह चमत्कारी क्रीम है #विज्ञापन", "चमत्कारी", "HINGLISH-SUPERLATIVE-01"),
            ("१००% असर मुंहासों पर #विज्ञापन", "१००% असर", ("HINGLISH-SUPERLATIVE-01", "HINGLISH-CLINICAL-EXAGGERATION-05")),
            ("मुंहासे जड़ से खत्म करें #विज्ञापन", "जड़ से खत्म", "HINGLISH-SUPERLATIVE-01"),
            ("हमेशा के लिए झुर्रियां खत्म #विज्ञापन", "हमेशा के लिए", "HINGLISH-SUPERLATIVE-01"),
            ("शत प्रतिशत फायदा मिलेगा #विज्ञापन", "शत प्रतिशत", "HINGLISH-SUPERLATIVE-01"),
            ("एक झटके में दर्द गायब #विज्ञापन", "एक झटके में", "HINGLISH-SUPERLATIVE-01"),
            ("यह रामबाण इलाज है #विज्ञापन", "रामबाण इलाज", "HINGLISH-AYUSH-03"),
            ("दाग धब्बों का पक्का इलाज #विज्ञापन", "पक्का इलाज", "HINGLISH-AYUSH-03"),
            ("त्वचा बिल्कुल ठीक हो जाएगी #विज्ञापन", "बिल्कुल ठीक", "HINGLISH-AYUSH-03"),
            ("गारंटीड रिजल्ट पाएं #विज्ञापन", "गारंटीड", "HINGLISH-SUPERLATIVE-01"),
            ("७ दिन में गोरा रंग पाएं #विज्ञापन", "गोरा रंग", "HINGLISH-COLORIST-02"),
            ("रंग को गोरा करने वाली क्रीम #विज्ञापन", "रंग को गोरा", "HINGLISH-COLORIST-02"),
            ("हमारी क्रीम देती है फेयरनेस गारंटी #विज्ञापन", "फेयरनेस गारंटी", "HINGLISH-COLORIST-02"),
            ("एक हफ्ते में गोरा चेहरा #विज्ञापन", "एक हफ्ते में गोरा", "HINGLISH-COLORIST-02"),
            ("यह क्रीम रंगत निखारे #विज्ञापन", "रंगत निखारे", "HINGLISH-COLORIST-02"),
            ("असली गोरापन पाएं #विज्ञापन", "गोरापन", "HINGLISH-COLORIST-02")
        ]

        for text, phrase, expected_rules in violating_samples:
            if isinstance(expected_rules, str):
                expected_rules = [expected_rules]
            with self.subTest(text=text, phrase=phrase):
                findings = self.engine.check_hinglish_and_regional_claims(text)
                self.assertGreater(
                    len(findings), 0,
                    f"Failed to flag violating Devanagari text: '{text}' containing '{phrase}'"
                )
                matched_rules = [f.rule_id for f in findings]
                self.assertTrue(
                    any(r in matched_rules for r in expected_rules),
                    f"Expected one of rules {expected_rules} for '{phrase}', got {matched_rules}"
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
