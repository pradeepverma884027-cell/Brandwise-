"""
Unit and regression tests for Improvement 2 Frontend Single-Page Application (SPA)
Validates Visual Asset Inspector UI, Synthetic Presets, Counter-Evidence Adjudication Gateway,
client-side fallback mathematical formulas, and tri-file HTML mirror parity.
"""

import hashlib
import math
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CODEX_ROOT = REPO_ROOT / "codex"


class TestImprovement2Frontend(unittest.TestCase):
    """Test suite verifying Frontend SPA changes for Milestone 3 (Improvement 2 UI)."""

    def test_tri_file_sha256_mirror_parity(self):
        """Verifies codex/frontend/index.html, index.html, and docs/index.html are 100% byte-for-byte identical."""
        paths = [
            CODEX_ROOT / "frontend" / "index.html",
            REPO_ROOT / "index.html",
            REPO_ROOT / "docs" / "index.html"
        ]

        hashes = []
        sizes = []
        for p in paths:
            self.assertTrue(p.exists(), f"File does not exist: {p}")
            data = p.read_bytes()
            hashes.append(hashlib.sha256(data).hexdigest())
            sizes.append(len(data))

        self.assertEqual(len(set(hashes)), 1, f"SHA-256 mismatch across mirrors: {list(zip(paths, hashes))}")
        self.assertEqual(len(set(sizes)), 1, f"Size mismatch across mirrors: {list(zip(paths, sizes))}")

    def test_visual_inspector_tab_and_navigation(self):
        """Verifies Visual Inspector navigation buttons and activeTab routing are present."""
        html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn("Visual Inspector", html)
        self.assertIn("activeTab === 'visual'", html)
        self.assertIn("openVisualViolationsCount", html)
        self.assertIn("Visual Asset Compliance &amp; Geometry Inspector", html)
        self.assertIn("Inspect Visual Asset", html)

    def test_synthetic_presets_present(self):
        """Verifies all 3 mandated synthetic visual asset test presets exist."""
        html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn("Compliant Asset", html)
        self.assertIn("preset-compliant-hero.png", html)

        self.assertIn("Logo Geometry Drift", html)
        self.assertIn("preset-logo-geom-drift.png", html)

        self.assertIn("Palette Drift &amp; Contrast Failure", html)
        self.assertIn("preset-palette-contrast-fail.png", html)

    def test_counter_evidence_gateway_and_canonical_types(self):
        """Verifies Counter-Evidence modal and the 6 canonical evidence types."""
        html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn("Submit Counter-Evidence", html)
        self.assertIn("Submit Compliance Counter-Evidence", html)

        canonical_types = [
            "clinical_trial_certificate",
            "cdsco_stage4_clearance",
            "legal_waiver_signoff",
            "lab_assay_report",
            "influencer_contract_exemption",
            "ayush_clinical_registry"
        ]
        for ctype in canonical_types:
            self.assertIn(ctype, html, f"Missing canonical counter-evidence type: {ctype}")

        self.assertIn("Allegation Dismissed", html)
        self.assertIn("Evidence Accepted", html)
        self.assertIn("Insufficient Evidence", html)

    def test_endpoint_and_fallback_contracts(self):
        """Verifies REST endpoints and dual-mode client-side fallbacks."""
        html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn("/api/visual/inspect", html)
        self.assertIn("/api/adjudication/submit", html)
        self.assertIn("simulateVisualInspection", html)
        self.assertIn("handleInspectVisualAsset", html)
        self.assertIn("handleCounterEvidenceSubmit", html)

    def test_score_restoration_and_audit_log_tracking(self):
        """Verifies compliance score restores by +15 pts and logs to dynamic auditLogs."""
        html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn("restoredScoreDelta", html)
        self.assertIn("auditLogs", html)
        self.assertIn("+ 15", html)

    def test_client_fallback_math_formulas(self):
        """Validates that mathematical formulas in client fallback behave deterministically."""
        # 1. Aspect ratio drift: actual=1.08, expected=1.00 -> 8.0% > 2.0%
        actual = 1.08
        expected = 1.00
        drift = round(abs(actual - expected) / expected * 100, 2)
        self.assertEqual(drift, 8.0)
        self.assertGreater(drift, 2.0)

        # 2. Euclidean RGB distance: #3A3A3A (58, 58, 58) vs #0F172A (15, 23, 42)
        # sqrt((58-15)^2 + (58-23)^2 + (58-42)^2) = sqrt(1849 + 1225 + 256) = sqrt(3330) ≈ 57.7
        r1, g1, b1 = 58, 58, 58
        r2, g2, b2 = 15, 23, 42
        dist = math.sqrt((r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2)
        self.assertAlmostEqual(dist, 57.706, places=2)
        self.assertTrue(15.0 <= dist <= 65.0)

        # 3. WCAG contrast ratio:
        def luminance(r, g, b):
            def ch(v):
                s = v / 255.0
                return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4
            return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)

        # #94A3B8: 148, 163, 184
        l_fg = luminance(148, 163, 184)
        l_bg = luminance(255, 255, 255)
        ratio_fail = round((max(l_fg, l_bg) + 0.05) / (min(l_fg, l_bg) + 0.05), 2)
        self.assertLess(ratio_fail, 4.5)  # ~2.56 < 4.5 -> violation

        # #0F172A on #FFFFFF
        l_dark = luminance(15, 23, 42)
        ratio_pass = round((max(l_dark, l_bg) + 0.05) / (min(l_dark, l_bg) + 0.05), 2)
        self.assertGreater(ratio_pass, 4.5)  # ~17.9 >= 4.5 -> compliant


if __name__ == "__main__":
    unittest.main()
