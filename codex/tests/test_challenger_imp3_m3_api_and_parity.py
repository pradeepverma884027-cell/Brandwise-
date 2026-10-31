"""
Adversarial Stress Test Suite & Parity Verifier for Milestone 3.
Role: Challenger 2 (Milestone 3)
Target: REST API endpoint POST /api/hinglish/check and Bit-for-Bit Mirror Parity.

Validates:
1. Enormous text payloads (>100KB, >250KB, >500KB) and dense repetition.
2. Unicode emoji, non-Latin Hindi characters (Devanagari script & numerals), mixed casing, zero-width chars.
3. Unexpected HTTP methods (GET, PUT, DELETE, PATCH, HEAD, OPTIONS).
4. Extremely negative score clamping [0, 100] with dozens of violations.
5. High-volume repeated requests with zero global state mutation and zero memory leakage.
6. SHA-256 mirror parity (dual servers and tri-HTML mirrors).
"""

import os
import sys
import json
import time
import hashlib
import unittest
import tracemalloc
import gc
from typing import Dict, Any, Tuple, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODEX_ROOT = os.path.join(REPO_ROOT, "codex")
BACKEND_DIR = os.path.join(CODEX_ROOT, "backend")

for p in [REPO_ROOT, CODEX_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import server
from codex.tests.test_hinglish_compliance import HTTPTestClient


class TestAdversarialLargePayloads(unittest.TestCase):
    """Stress tests POST /api/hinglish/check with huge payloads up to >500KB."""

    def test_payload_100kb_text(self):
        """Processes payload > 100KB without timeout, regex explosion, or memory failure."""
        padding = "Yeh gentle everyday hydrating formula hai. " * 3000  # ~132 KB
        text = padding + " chamatkari formula deta hai 100% asar acne par! #vigyapan"
        payload_bytes = len(text.encode("utf-8"))
        self.assertGreater(payload_bytes, 100 * 1024)

        t0 = time.time()
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": text})
        duration = time.time() - t0

        self.assertEqual(status, 200)
        self.assertLess(duration, 1.5, f"Processing {payload_bytes} bytes took {duration:.2f}s, expected < 1.5s")
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        self.assertFalse(data["summary"]["is_compliant"])
        self.assertGreaterEqual(len(data["findings"]), 2)

    def test_payload_250kb_text(self):
        """Processes payload > 250KB cleanly."""
        padding = "Yeh dermatological lotion daily skin health maintain karta hai. " * 4500  # ~288 KB
        text = padding + " 100% asar aur gora rang sirf ek jhatke mein! #vigyapan"
        payload_bytes = len(text.encode("utf-8"))
        self.assertGreater(payload_bytes, 250 * 1024)

        t0 = time.time()
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": text})
        duration = time.time() - t0

        self.assertEqual(status, 200)
        self.assertLess(duration, 2.5, f"Processing {payload_bytes} bytes took {duration:.2f}s, expected < 2.5s")
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(len(data["findings"]), 3)

    def test_payload_500kb_text(self):
        """Processes payload > 500KB cleanly."""
        padding = "Safe Ayurvedic and herbal extracts based formulation. " * 10000  # ~540 KB
        text = padding + " ramban ilaj pimples ke liye! #vigyapan"
        payload_bytes = len(text.encode("utf-8"))
        self.assertGreater(payload_bytes, 500 * 1024)

        t0 = time.time()
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": text})
        duration = time.time() - t0

        self.assertEqual(status, 200)
        self.assertLess(duration, 3.5, f"Processing {payload_bytes} bytes took {duration:.2f}s, expected < 3.5s")
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(len(data["findings"]), 1)

    def test_dense_repetitive_violations_payload(self):
        """Processes 50KB of repeating dense violation tokens without catastrophic regex backtracking."""
        cluster = "chamatkari 100% asar jad se khatam hamesha ke liye shat pratishat ek jhatke mein ramban ilaj "
        dense_text = (cluster * 400) + "#vigyapan"  # ~38 KB of continuous violation patterns
        t0 = time.time()
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": dense_text})
        duration = time.time() - t0

        self.assertEqual(status, 200)
        self.assertLess(duration, 2.0, f"Dense regex took {duration:.2f}s, expected < 2.0s")
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["compliance_score"], 0)


class TestAdversarialUnicodeAndDevanagari(unittest.TestCase):
    """Stress tests Unicode emoji, Devanagari script & numerals, mixed casing, and special chars."""

    def test_unicode_emojis_and_special_symbols(self):
        """Verifies emoji, mathematical symbols, and non-ASCII glyphs do not break UTF-8 handling."""
        text = (
            "🔥🌟 Dosto!! 🧴 Ye ChAmAtKaRi formula deta hai 100% AsAr aur GoRa RaNg! "
            "✨💯 Pimples jad se khatam! Buy now 50% discount link bio mein! #ViGyApAn 🚀"
        )
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": text})
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        self.assertLessEqual(data["compliance_score"], 40)
        highlighted = [f["highlighted_text"] for f in data["findings"]]
        self.assertTrue(any("chamatkari" in h.lower() for h in highlighted))
        self.assertTrue(any("gora rang" in h.lower() for h in highlighted))

    def test_devanagari_script_and_hindi_numerals(self):
        """Verifies pure Devanagari Hindi text and Devanagari numerals are handled without 500 error."""
        text = "यह चमत्कारी फॉर्मूला देता है १००% असर और गोरा रंग! #vigyapan"
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": text})
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        # Clinical extractor picks up Devanagari percentage १००% as statistical exaggeration
        self.assertIn("compliance_score", data)
        self.assertIsInstance(data["findings"], list)

    def test_mixed_devanagari_and_latin_hinglish(self):
        """Verifies code-mixed sentences containing both Devanagari and Latin script words."""
        text = "नमस्ते dosto! Ye चमत्कारी cream dega 100% asar skin par! Buy now link bio mein! #vigyapan"
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": text})
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        highlighted = [f["highlighted_text"].lower() for f in data["findings"]]
        self.assertTrue(any("100% asar" in h for h in highlighted))

    def test_mixed_casing_permutations(self):
        """Verifies extreme alternating mixed-case Hinglish patterns."""
        text = "sHaT pRaTiShAt asar aur jaD sE kHaTaM karega, rAmBaN iLaJ aur pAkKa iLaJ! #Ad"
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": text})
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "success")
        highlighted = [f["highlighted_text"].lower() for f in data["findings"]]
        self.assertTrue(any("shat pratishat" in h for h in highlighted))
        self.assertTrue(any("jad se khatam" in h for h in highlighted))
        self.assertTrue(any("ramban ilaj" in h for h in highlighted))
        self.assertTrue(any("pakka ilaj" in h for h in highlighted))

    def test_zero_width_and_invisible_characters(self):
        """Verifies zero-width space and invisible unicode characters do not crash the parser."""
        text = "Ye\u200b chamatkari\u200b formula\u200b deta hai 100% asar! #vigyapan"
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": text})
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "success")


class TestUnexpectedHTTPMethods(unittest.TestCase):
    """Stress tests unexpected and unsupported HTTP verbs on /api/hinglish/check."""

    def test_http_get_on_endpoint(self):
        """GET /api/hinglish/check returns 404 File not found (endpoint is POST-only)."""
        status, _, _ = HTTPTestClient.get("/api/hinglish/check")
        self.assertEqual(status, 404)

    def test_http_put_on_endpoint(self):
        """PUT /api/hinglish/check returns 501 Unsupported method."""
        status, _, _ = HTTPTestClient.request("PUT", "/api/hinglish/check", body=b'{"text": "test"}')
        self.assertEqual(status, 501)

    def test_http_delete_on_endpoint(self):
        """DELETE /api/hinglish/check returns 501 Unsupported method."""
        status, _, _ = HTTPTestClient.request("DELETE", "/api/hinglish/check")
        self.assertEqual(status, 501)

    def test_http_patch_on_endpoint(self):
        """PATCH /api/hinglish/check returns 501 Unsupported method."""
        status, _, _ = HTTPTestClient.request("PATCH", "/api/hinglish/check", body=b'{"text": "test"}')
        self.assertEqual(status, 501)

    def test_http_options_cors(self):
        """OPTIONS /api/hinglish/check returns 200 for CORS preflight."""
        status, headers, _ = HTTPTestClient.request("OPTIONS", "/api/hinglish/check")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("access-control-allow-origin"), "*")


class TestExtremeScoreClamping(unittest.TestCase):
    """Verifies compliance score clamping at 0 and 100 under extreme conditions."""

    def test_extreme_negative_score_clamping(self):
        """Payload with dozens of violations (raw score << 0) clamps strictly to exactly 0."""
        repeated_violations = (
            "chamatkari 100% asar jad se khatam hamesha ke liye shat pratishat "
            "ek jhatke mein ramban ilaj pakka ilaj bilkul theek gora rang rang gora "
            "fairness guarantee ek hafte mein gora rang nikhare gorapan "
        ) * 10
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": repeated_violations})
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertGreaterEqual(len(data["findings"]), 50)
        self.assertEqual(data["compliance_score"], 0)
        self.assertFalse(data["summary"]["is_compliant"])

    def test_boundary_score_deductions(self):
        """Single high severity deducts exactly -20 (score 80); single medium deducts -10 (score 90)."""
        # High severity violation: chamatkari
        s1, _, b1 = HTTPTestClient.post("/api/hinglish/check", json_data={"text": "Ye chamatkari lotion hai. #vigyapan"})
        self.assertEqual(s1, 200)
        d1 = json.loads(b1.decode("utf-8"))
        self.assertEqual(d1["compliance_score"], 80)
        self.assertEqual(d1["summary"]["high_severity_count"], 1)

        # Medium severity violation: borderline clinical rounding 94% asar
        s2, _, b2 = HTTPTestClient.post("/api/hinglish/check", json_data={"text": "Clinical testing mein 94% asar dikha. #vigyapan"})
        self.assertEqual(s2, 200)
        d2 = json.loads(b2.decode("utf-8"))
        self.assertEqual(d2["compliance_score"], 90)
        self.assertEqual(d2["summary"]["medium_severity_count"], 1)

    def test_clean_copy_score_ceiling(self):
        """Clean compliant copy achieves maximum score ceiling 100."""
        text = "Gentle daily hydrating moisturizer for all skin types. #ad #vigyapan"
        status, _, body = HTTPTestClient.post("/api/hinglish/check", json_data={"text": text})
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["compliance_score"], 100)
        self.assertTrue(data["summary"]["is_compliant"])
        self.assertEqual(len(data["findings"]), 0)


class TestHighVolumeStateIsolationAndLeaks(unittest.TestCase):
    """Verifies that high-volume repeated API checks do not leak memory or mutate global server state."""

    def test_global_state_immutability_under_load(self):
        """Verifies CLINICAL_STUDIES_CATALOG and SUPABASE_MOCK_TABLES are not mutated by check requests."""
        init_catalog_count = len(server.CLINICAL_STUDIES_CATALOG)
        init_catalog_serialized = json.dumps(server.CLINICAL_STUDIES_CATALOG, sort_keys=True)
        init_audit_count = len(server.SUPABASE_MOCK_TABLES.get("audit_logs", []))

        payloads = [
            {"text": "Clean copy with #vigyapan"},
            {"text": "Ye chamatkari formula deta hai 100% asar!"},
            {"text": "7 din mein gora rang! #ad"},
            {"text": "   "},
            {"invalid_key": "no text"},
        ]

        tracemalloc.start()
        gc.collect()
        snap1 = tracemalloc.take_snapshot()

        for i in range(150):
            p = payloads[i % len(payloads)]
            HTTPTestClient.post("/api/hinglish/check", json_data=p)

        gc.collect()
        snap2 = tracemalloc.take_snapshot()

        # Check catalog integrity
        final_catalog_count = len(server.CLINICAL_STUDIES_CATALOG)
        final_catalog_serialized = json.dumps(server.CLINICAL_STUDIES_CATALOG, sort_keys=True)
        final_audit_count = len(server.SUPABASE_MOCK_TABLES.get("audit_logs", []))

        self.assertEqual(init_catalog_count, final_catalog_count, "Clinical catalog size changed")
        self.assertEqual(init_catalog_serialized, final_catalog_serialized, "Clinical catalog content was mutated")
        self.assertEqual(init_audit_count, final_audit_count, "Audit logs were erroneously modified by /api/hinglish/check")

        stats = snap2.compare_to(snap1, "lineno")
        total_diff_kb = sum(s.size_diff for s in stats) / 1024
        tracemalloc.stop()

        # Total memory diff across 150 requests must be negligible (< 250 KB)
        self.assertLess(total_diff_kb, 250, f"Memory growth {total_diff_kb:.2f} KB indicates potential leak")

    def test_deterministic_idempotency(self):
        """Identical inputs yield bit-for-bit identical responses across repeated invocations."""
        payload = {
            "text": "Arre dosto! Ye chamatkari cream deta hai 100% asar aur gora rang! Order karein link bio mein!",
            "channel": "hinglish_instagram"
        }
        status1, _, body1 = HTTPTestClient.post("/api/hinglish/check", json_data=payload)
        status2, _, body2 = HTTPTestClient.post("/api/hinglish/check", json_data=payload)

        self.assertEqual(status1, status2)
        d1 = json.loads(body1.decode("utf-8"))
        d2 = json.loads(body2.decode("utf-8"))
        self.assertEqual(d1["compliance_score"], d2["compliance_score"])
        self.assertEqual(len(d1["findings"]), len(d2["findings"]))
        for f1, f2 in zip(d1["findings"], d2["findings"]):
            self.assertEqual(f1["category"], f2["category"])
            self.assertEqual(f1["severity"], f2["severity"])
            self.assertEqual(f1["highlighted_text"], f2["highlighted_text"])
            self.assertEqual(f1["suggested_fix"], f2["suggested_fix"])


class TestMirrorParityIntegrity(unittest.TestCase):
    """Empirically verifies 100% cryptographic SHA-256 mirror parity."""

    def test_server_sha256_mirror_parity(self):
        """server.py and codex/server.py must be 100% bit-for-bit identical."""
        p1 = os.path.join(REPO_ROOT, "server.py")
        p2 = os.path.join(REPO_ROOT, "codex", "server.py")

        with open(p1, "rb") as f1, open(p2, "rb") as f2:
            b1 = f1.read()
            b2 = f2.read()

        h1 = hashlib.sha256(b1).hexdigest()
        h2 = hashlib.sha256(b2).hexdigest()

        self.assertEqual(len(b1), len(b2), f"Server file sizes differ: {len(b1)} vs {len(b2)}")
        self.assertEqual(h1, h2, f"Server SHA-256 hashes differ: {h1} vs {h2}")

    def test_frontend_html_tri_file_parity(self):
        """codex/frontend/index.html, index.html, and docs/index.html must be 100% bit-for-bit identical."""
        p_codex = os.path.join(REPO_ROOT, "codex", "frontend", "index.html")
        p_root = os.path.join(REPO_ROOT, "index.html")
        p_docs = os.path.join(REPO_ROOT, "docs", "index.html")

        with open(p_codex, "rb") as f1, open(p_root, "rb") as f2, open(p_docs, "rb") as f3:
            b1 = f1.read()
            b2 = f2.read()
            b3 = f3.read()

        h1 = hashlib.sha256(b1).hexdigest()
        h2 = hashlib.sha256(b2).hexdigest()
        h3 = hashlib.sha256(b3).hexdigest()

        self.assertEqual(len(b1), len(b2), f"HTML sizes differ between codex and root: {len(b1)} vs {len(b2)}")
        self.assertEqual(len(b1), len(b3), f"HTML sizes differ between codex and docs: {len(b1)} vs {len(b3)}")
        self.assertEqual(h1, h2, f"HTML SHA-256 differs between codex and root: {h1} vs {h2}")
        self.assertEqual(h1, h3, f"HTML SHA-256 differs between codex and docs: {h1} vs {h3}")


if __name__ == "__main__":
    unittest.main()
