"""
Adversarial and Empirical Challenge Test Suite for Milestone M1:
Clinical Discrepancy Matching & Canonical Citations.

Tests evaluate_clinical_discrepancies and DeterministicReviewEngine.check_clinical_evidence.
"""

import os
import sys
import unittest
from pathlib import Path

# Add backend directory to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.clinical_extractor import (
    evaluate_clinical_discrepancies,
    DEFAULT_CLINICAL_STUDIES,
    normalize_clinical_dossier
)
from app.core.review_engine import (
    DeterministicReviewEngine,
    deterministic_engine,
    FindingCandidate
)


class TestAdversarialClinicalDiscrepancies(unittest.TestCase):
    """Adversarial stress tests for evaluate_clinical_discrepancies and check_clinical_evidence."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()
        self.canonical_citation = "Clinical Study CS-2026-88, Page 7, Table 2.1"
        self.trial_hydration = 94.2
        self.trial_days = 14

    # =========================================================================
    # SUITE A: Over-claims and Percentage Boundary Variations
    # =========================================================================

    def test_a1_boundary_just_above_endpoint_94_21(self):
        """Claiming 94.21% when study observed 94.2%: flags discrepancy but test delta precision."""
        copy = "Delivers 94.21% hydration boost."
        res = evaluate_clinical_discrepancies(copy)
        self.assertTrue(res["has_discrepancies"])
        self.assertEqual(len(res["discrepancies"]), 1)
        disc = res["discrepancies"][0]
        self.assertEqual(disc["type"], "statistical_exaggeration")
        self.assertEqual(disc["claimed_value"], "94.21%")
        self.assertEqual(disc["trial_value"], "94.2%")
        # Note: round(94.21 - 94.2, 1) produces 0.0 -> "+0.0% exaggeration"
        self.assertIn("% exaggeration", disc["delta"])

    def test_a2_over_claim_95_percent(self):
        """Claiming 95.0% vs 94.2%: delta must equal +0.8% exaggeration."""
        copy = "Achieves 95.0% hydration in testing."
        res = evaluate_clinical_discrepancies(copy)
        self.assertTrue(res["has_discrepancies"])
        disc = res["discrepancies"][0]
        self.assertEqual(disc["delta"], "+0.8% exaggeration")
        self.assertEqual(disc["citation"], self.canonical_citation)

    def test_a3_over_claim_99_percent_exact_delta(self):
        """Claiming 99% vs 94.2%: exact delta '+4.8% exaggeration' required by spec."""
        copy = "Proven to give 99% hydration improvement."
        res = evaluate_clinical_discrepancies(copy)
        self.assertTrue(res["has_discrepancies"])
        disc = res["discrepancies"][0]
        self.assertEqual(disc["delta"], "+4.8% exaggeration")
        self.assertEqual(disc["citation"], self.canonical_citation)
        self.assertIn("99.0%", disc["claimed_value"])

    def test_a4_over_claim_100_percent(self):
        """Claiming 100% vs 94.2%: delta +5.8% exaggeration."""
        copy = "Guaranteed 100% hydration results."
        res = evaluate_clinical_discrepancies(copy)
        self.assertTrue(res["has_discrepancies"])
        disc = res["discrepancies"][0]
        self.assertEqual(disc["delta"], "+5.8% exaggeration")

    def test_a5_over_claim_150_percent(self):
        """Claiming 150% vs 94.2%: delta +55.8% exaggeration."""
        copy = "Incredible 150% hydration boost over baseline."
        res = evaluate_clinical_discrepancies(copy)
        self.assertTrue(res["has_discrepancies"])
        disc = res["discrepancies"][0]
        self.assertEqual(disc["delta"], "+55.8% exaggeration")

    def test_a6_fractional_percentages(self):
        """Test multiple fractional percentages."""
        fractions = [
            (95.5, "+1.3% exaggeration"),
            (97.2, "+3.0% exaggeration"),
            (99.9, "+5.7% exaggeration"),
        ]
        for pct, expected_delta in fractions:
            copy = f"Demonstrated {pct}% hydration increase."
            res = evaluate_clinical_discrepancies(copy)
            self.assertTrue(res["has_discrepancies"], f"Failed to flag {pct}%")
            self.assertEqual(res["discrepancies"][0]["delta"], expected_delta)

    def test_a7_percentage_without_space(self):
        """Format '99%' without whitespace."""
        res = evaluate_clinical_discrepancies("99% hydration boost")
        self.assertTrue(res["has_discrepancies"])
        self.assertEqual(res["discrepancies"][0]["delta"], "+4.8% exaggeration")

    def test_a8_percentage_with_space(self):
        """Format '99 %' with whitespace."""
        res = evaluate_clinical_discrepancies("99 % hydration boost")
        self.assertTrue(res["has_discrepancies"])
        self.assertEqual(res["discrepancies"][0]["delta"], "+4.8% exaggeration")

    def test_a9_percentage_with_word_percent(self):
        """Format '99 percent' with word percent."""
        res = evaluate_clinical_discrepancies("99 percent hydration boost")
        self.assertTrue(res["has_discrepancies"])
        self.assertEqual(res["discrepancies"][0]["delta"], "+4.8% exaggeration")

    def test_a10_percentage_word_without_space_stress(self):
        """
        Adversarial test: '99percent' without space between digit and 'percent'.
        Regex r'(\\d+(?:\\.\\d+)?)\\s*(?:%|\\bpercent\\b)' fails due to \\b after digit.
        Records empirical failure behavior.
        """
        res = evaluate_clinical_discrepancies("99percent hydration boost")
        # Empirical test: does the regex detect 99percent?
        # Note: If this fails, we record the bug empirically.
        detected = any(d.get("claimed_value") in ["99%", "99.0%"] for d in res["discrepancies"])
        # We assert what the engine currently does and document the limitation
        if not detected:
            print("[FINDING-01 REPRODUCED] '99percent' is NOT detected by regex due to \\b boundary rule.")
        self.assertFalse(detected, "Engine unexpectedly matched 99percent (regex was updated?)")

    # =========================================================================
    # SUITE B: Timeline Compressions vs 14 Days
    # =========================================================================

    def test_b1_timeline_compression_1_day(self):
        """1 day vs 14 days: flags timeline compression."""
        res = evaluate_clinical_discrepancies("Noticeable hydration in 1 day!")
        self.assertTrue(res["has_discrepancies"])
        disc = res["discrepancies"][0]
        self.assertEqual(disc["type"], "timeline_compression")
        self.assertIn("-13 days", disc["delta"])
        self.assertEqual(disc["citation"], self.canonical_citation)

    def test_b2_timeline_compression_3_days(self):
        """3 days vs 14 days: delta '-11 days premature claim'."""
        res = evaluate_clinical_discrepancies("Visible improvement in 3 days.")
        self.assertTrue(res["has_discrepancies"])
        disc = res["discrepancies"][0]
        self.assertEqual(disc["delta"], "-11 days premature claim")

    def test_b3_timeline_compression_7_days_exact(self):
        """7 days vs 14 days: exact delta '-7 days premature claim' required by spec."""
        res = evaluate_clinical_discrepancies("Results in 7 days.")
        self.assertTrue(res["has_discrepancies"])
        disc = res["discrepancies"][0]
        self.assertEqual(disc["delta"], "-7 days premature claim")
        self.assertEqual(disc["citation"], self.canonical_citation)
        self.assertEqual(disc["claimed_value"], "7 days")
        self.assertEqual(disc["trial_value"], "14 days")

    def test_b4_timeline_compression_13_days(self):
        """13 days vs 14 days: boundary adjacent to trial duration."""
        res = evaluate_clinical_discrepancies("Proven efficacy in 13 days.")
        self.assertTrue(res["has_discrepancies"])
        disc = res["discrepancies"][0]
        self.assertIn("-1 days", disc["delta"])

    def test_b5_timeline_compression_48_hours_stress(self):
        """
        Adversarial test: '48 hours' vs 14 days.
        Current implementation only checks r'(\\d+)\\s*days?'.
        Records empirical failure behavior.
        """
        res = evaluate_clinical_discrepancies("Clinical results in 48 hours!")
        has_compression = any(d["type"] == "timeline_compression" for d in res["discrepancies"])
        if not has_compression:
            print("[FINDING-02 REPRODUCED] '48 hours' timeline compression is NOT detected.")
        self.assertFalse(has_compression)

    def test_b6_timeline_compression_overnight_stress(self):
        """
        Adversarial test: 'overnight' vs 14 days.
        Current implementation does not recognize 'overnight'.
        Records empirical failure behavior.
        """
        res = evaluate_clinical_discrepancies("Overnight hydration transformation!")
        has_compression = any(d["type"] == "timeline_compression" for d in res["discrepancies"])
        if not has_compression:
            print("[FINDING-03 REPRODUCED] 'overnight' timeline compression is NOT detected.")
        self.assertFalse(has_compression)

    # =========================================================================
    # SUITE C: Compliant Claims (Substantiated & Permitted)
    # =========================================================================

    def test_c1_exact_endpoint_94_2_percent(self):
        """Claiming exactly 94.2%: SUBSTANTIATED with canonical citation."""
        res = evaluate_clinical_discrepancies("Clinical study observed 94.2% hydration increase.")
        self.assertFalse(res["has_discrepancies"])
        self.assertEqual(len(res["verified_claims"]), 1)
        vc = res["verified_claims"][0]
        self.assertEqual(vc["status"], "SUBSTANTIATED")
        self.assertEqual(vc["citation"], self.canonical_citation)
        self.assertEqual(vc["claimed_value"], "94.2%")
        self.assertEqual(vc["trial_value"], "94.2%")

    def test_c2_conservative_94_0_percent(self):
        """Claiming 94.0% (< 94.2%): SUBSTANTIATED."""
        res = evaluate_clinical_discrepancies("Delivers 94.0% hydration support.")
        self.assertFalse(res["has_discrepancies"])
        self.assertEqual(len(res["verified_claims"]), 1)
        self.assertEqual(res["verified_claims"][0]["status"], "SUBSTANTIATED")

    def test_c3_conservative_90_percent(self):
        """Claiming 90% (< 94.2%): SUBSTANTIATED."""
        res = evaluate_clinical_discrepancies("Provides 90% hydration increase.")
        self.assertFalse(res["has_discrepancies"])
        self.assertEqual(len(res["verified_claims"]), 1)
        self.assertEqual(res["verified_claims"][0]["status"], "SUBSTANTIATED")

    def test_c4_conservative_50_percent(self):
        """Claiming 50% hydration (< 94.2%): SUBSTANTIATED."""
        res = evaluate_clinical_discrepancies("Delivers 50% hydration boost.")
        self.assertFalse(res["has_discrepancies"])
        self.assertEqual(len(res["verified_claims"]), 1)
        self.assertEqual(res["verified_claims"][0]["status"], "SUBSTANTIATED")

    def test_c5_compliant_duration_14_days(self):
        """Claiming 14 days matching trial duration: no timeline compression."""
        res = evaluate_clinical_discrepancies("Tested over 14 days of daily use.")
        compressions = [d for d in res["discrepancies"] if d["type"] == "timeline_compression"]
        self.assertEqual(len(compressions), 0)

    def test_c6_compliant_duration_21_days(self):
        """Claiming 21 days (> 14 days): compliant, no compression."""
        res = evaluate_clinical_discrepancies("Results maintained through 21 days.")
        compressions = [d for d in res["discrepancies"] if d["type"] == "timeline_compression"]
        self.assertEqual(len(compressions), 0)

    def test_c7_compliant_duration_30_days(self):
        """Claiming 30 days (> 14 days): compliant, no compression."""
        res = evaluate_clinical_discrepancies("Follow-up evaluation at 30 days.")
        compressions = [d for d in res["discrepancies"] if d["type"] == "timeline_compression"]
        self.assertEqual(len(compressions), 0)

    # =========================================================================
    # SUITE D: Unverified Claims & Prohibited Phrasing
    # =========================================================================

    def test_d1_unverified_cure_acne_permanently(self):
        """'cures acne permanently': flags unverified cure claims."""
        res = evaluate_clinical_discrepancies("This formula cures acne permanently.")
        self.assertTrue(res["has_discrepancies"])
        claimed_vals = [d["claimed_value"] for d in res["discrepancies"]]
        self.assertIn("cures", claimed_vals)
        self.assertIn("permanently", claimed_vals)

    def test_d2_unverified_eradicates_rosacea(self):
        """'eradicates rosacea': 'rosacea' is flagged as unsupported keyword."""
        res = evaluate_clinical_discrepancies("Eradicates rosacea with daily use.")
        self.assertTrue(res["has_discrepancies"])
        claimed_vals = [d["claimed_value"] for d in res["discrepancies"]]
        self.assertIn("rosacea", claimed_vals)
        # Note: 'eradicates' itself is NOT in cure_pattern
        self.assertNotIn("eradicates", claimed_vals)

    def test_d3_unverified_eliminates_wrinkles(self):
        """'eliminates wrinkles': 'eliminates' (cure) and 'wrinkles' (keyword) both flagged."""
        res = evaluate_clinical_discrepancies("Eliminates wrinkles in all skin types.")
        self.assertTrue(res["has_discrepancies"])
        claimed_vals_lower = [d["claimed_value"].lower() for d in res["discrepancies"]]
        self.assertIn("eliminates", claimed_vals_lower)
        self.assertIn("wrinkles", claimed_vals_lower)

    def test_d4_unverified_cellular_regeneration_stress(self):
        """
        Adversarial test: 'cellular regeneration'.
        Neither 'cellular' nor 'regeneration' is in unsupported_keywords.
        Records empirical failure behavior.
        """
        res = evaluate_clinical_discrepancies("Promotes cellular regeneration.")
        has_disc = res["has_discrepancies"]
        if not has_disc:
            print("[FINDING-04 REPRODUCED] 'cellular regeneration' is NOT detected as unverified claim.")
        self.assertFalse(has_disc)

    def test_d5_permanent_vs_permanently_stress(self):
        """
        Adversarial test: 'permanent cure' vs 'cures permanently'.
        cure_pattern = r'\b(cures?|permanently|eliminates?)\b' matches 'permanently' but NOT 'permanent'.
        """
        res = evaluate_clinical_discrepancies("A permanent solution for blemishes.")
        claimed_vals = [d["claimed_value"] for d in res["discrepancies"]]
        if "permanent" not in claimed_vals:
            print("[FINDING-05 REPRODUCED] 'permanent' (adjective) is NOT matched by cure_pattern ('permanently').")
        self.assertNotIn("permanent", claimed_vals)

    # =========================================================================
    # SUITE E: Compound Sentences & Paragraphs (3+ Distinct Assertions)
    # =========================================================================

    def test_e1_compound_sentence_three_violations(self):
        """Compound copy: 99% hydration + 7 days + eliminates wrinkles."""
        copy = "Our serum gives 99% hydration in just 7 days, eliminates wrinkles completely!"
        res = evaluate_clinical_discrepancies(copy)
        self.assertTrue(res["has_discrepancies"])
        types = [d["type"] for d in res["discrepancies"]]
        self.assertIn("statistical_exaggeration", types)
        self.assertIn("timeline_compression", types)
        self.assertIn("unverified_claim", types)
        # Verify exact deltas
        deltas = {d["type"]: d["delta"] for d in res["discrepancies"]}
        self.assertEqual(deltas["statistical_exaggeration"], "+4.8% exaggeration")
        self.assertEqual(deltas["timeline_compression"], "-7 days premature claim")

    def test_e2_compound_paragraph_full_spectrum(self):
        """Paragraph with 4 distinct assertions: over-claim, timeline, cure verb, unverified keyword."""
        copy = (
            "Experience clinical excellence: achieves 100% hydration in 3 days. "
            "It permanently eliminates dark circles and restores your youth."
        )
        res = evaluate_clinical_discrepancies(copy)
        self.assertTrue(res["has_discrepancies"])
        self.assertGreaterEqual(len(res["discrepancies"]), 4)

    def test_e3_multi_endpoint_window_crosstalk_stress(self):
        """
        Adversarial test: surrounding window (30 chars) crosstalk between hydration and sebum.
        In '95% hydration and 50% sebum reduction', the 30-char window forward from '95%'
        contains the word 'sebum', erroneously matching 95% against sebum (42.5%)!
        """
        copy = "Achieves 95% hydration and 50% sebum reduction"
        res = evaluate_clinical_discrepancies(copy)
        disc_95 = next((d for d in res["discrepancies"] if d["claimed_value"] == "95.0%"), None)
        self.assertIsNotNone(disc_95)
        if disc_95["trial_value"] == "42.5%":
            print("[FINDING-06 REPRODUCED] 30-char lookahead causes '95% hydration' to match sebum endpoint (42.5%)!")
        # We record that it matched 42.5% instead of 94.2%
        self.assertEqual(disc_95["trial_value"], "42.5%")
        # And notice message contradiction: message says observed 94.2% while trial_value is 42.5%
        self.assertIn("observed 94.2%", disc_95["message"])

    # =========================================================================
    # SUITE F: FindingCandidate Conversion & DeterministicReviewEngine
    # =========================================================================

    def test_f1_finding_candidate_conversion(self):
        """DeterministicReviewEngine.check_clinical_evidence converts to FindingCandidate correctly."""
        copy = "Achieves 99% hydration in 7 days."
        findings = self.engine.check_clinical_evidence(copy)
        self.assertEqual(len(findings), 2)

        for f in findings:
            self.assertIsInstance(f, FindingCandidate)
            self.assertEqual(f.category, "claim")
            self.assertEqual(f.rule_id, "CLINICAL-EVIDENCE-01")
            self.assertEqual(f.severity, "high")
            self.assertEqual(f.source_ref, self.canonical_citation)
            self.assertIsNotNone(f.span_start)
            self.assertIsNotNone(f.span_end)
            self.assertIsNotNone(f.highlighted_text)
            self.assertGreater(f.confidence, 0.9)

    def test_f2_finding_candidate_spans_accuracy(self):
        """Verify that FindingCandidate span_start and span_end accurately slice the original text."""
        copy = "Clinically tested to deliver 99% hydration boost within 7 days of treatment."
        findings = self.engine.check_clinical_evidence(copy)
        for f in findings:
            extracted = copy[f.span_start:f.span_end]
            self.assertEqual(extracted, f.highlighted_text)

    def test_f3_finding_candidate_empty_input(self):
        """Empty text returns empty list without error."""
        self.assertEqual(self.engine.check_clinical_evidence(""), [])
        self.assertEqual(self.engine.check_clinical_evidence(None), [])

    def test_f4_finding_candidate_compliant_text(self):
        """Compliant text returns no FindingCandidate violations."""
        copy = "Clinical study observed 94.2% hydration increase over 14 days."
        findings = self.engine.check_clinical_evidence(copy)
        self.assertEqual(len(findings), 0)

    def test_f5_custom_study_dossier_passing(self):
        """Passing a custom study dossier to check_clinical_evidence overrides default."""
        custom_study = {
            "study_id": "STUDY-CUSTOM-01",
            "duration_days": 28,
            "endpoints": {"hydration_increase_percent": 85.0, "duration_days": 28},
            "source_citation": "Clinical Study CUSTOM-01, Page 12, Table 3"
        }
        findings = self.engine.check_clinical_evidence("88% hydration in 14 days", studies=custom_study)
        self.assertEqual(len(findings), 2)
        # 14 days vs 28 days -> flagged
        day_finding = next(f for f in findings if "14 days" in f.explanation)
        self.assertEqual(day_finding.source_ref, "Clinical Study CUSTOM-01, Page 12, Table 3")
        self.assertIn("28 days", day_finding.explanation)


    # =========================================================================
    # SUITE G: Additional Boundary Cases & Stress Invariants
    # =========================================================================

    def test_g1_hyphenated_timeline_stress(self):
        r"""
        Adversarial test: '7-day trial' or '7-days'.
        Regex r'(\d+)\s*days?' does not match hyphens.
        """
        res = evaluate_clinical_discrepancies("Demonstrated in a 7-day clinical trial.")
        has_compression = any(d["type"] == "timeline_compression" for d in res["discrepancies"])
        if not has_compression:
            print("[FINDING-07 REPRODUCED] '7-day' (hyphenated) is NOT detected as timeline compression.")
        self.assertFalse(has_compression)

    def test_g2_grammar_pluralization_in_deltas(self):
        """
        Verify grammatical string construction in deltas:
        1 day -> '1 days', 13 days vs 14 -> '-1 days premature claim'.
        """
        res_1 = evaluate_clinical_discrepancies("Results in 1 day.")
        self.assertEqual(res_1["discrepancies"][0]["claimed_value"], "1 days")
        res_13 = evaluate_clinical_discrepancies("Results in 13 days.")
        self.assertEqual(res_13["discrepancies"][0]["delta"], "-1 days premature claim")

    def test_g3_non_clinical_percentage_false_substantiation(self):
        """
        Adversarial test: non-clinical percentages (e.g. 0% parabens, 20% discount)
        are unconditionally assumed to be clinical trial endpoints and marked SUBSTANTIATED.
        """
        res = evaluate_clinical_discrepancies("Contains 0% sulfates, 0% parabens.")
        self.assertEqual(len(res["verified_claims"]), 2)
        for vc in res["verified_claims"]:
            self.assertEqual(vc["status"], "SUBSTANTIATED")
            self.assertEqual(vc["citation"], self.canonical_citation)
        print("[FINDING-08 REPRODUCED] 0% sulfates/parabens falsely substantiated by hydration clinical citation.")

    def test_g4_duplicate_discrepancy_ids(self):
        """
        Adversarial test: multiple occurrences of the same percentage produce identical discrepancy IDs.
        """
        copy = "Study A showed 99% boost, but another test showed 99% improvement."
        res = evaluate_clinical_discrepancies(copy)
        ids = [d["id"] for d in res["discrepancies"]]
        self.assertEqual(ids.count("disc-p-99"), 2)
        print("[FINDING-09 REPRODUCED] Duplicate discrepancy IDs generated ('disc-p-99' x2).")


if __name__ == "__main__":
    unittest.main()
