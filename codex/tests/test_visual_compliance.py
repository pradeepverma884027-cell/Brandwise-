"""
Unit and Integration Test Suite for Visual Asset Compliance Engine & Inspection API.

Validates Improvement 2 Feature Specifications (R1, R4, R5):
1. Logo geometry distortion boundary testing (pass at <=2.00%, fail at >2.00%).
2. Brand palette Euclidean RGB distance threshold testing:
   - primary (#0F172A), accent (#0284C7), success (#10B981)
   - distance < 15.0 -> pass
   - 15.0 <= distance <= 65.0 -> fail (palette_drift, medium severity)
   - distance > 65.0 -> pass
3. WCAG 2.2 contrast ratio pass/fail boundary at 4.5:1:
   - ratio >= 4.5:1 -> pass
   - ratio < 4.5:1 -> fail (contrast_failure, high severity)
4. Alternative text accessibility checks (empty, whitespace, missing vs descriptive).
5. Pre-loaded synthetic visual asset presets (Compliant Hero, Logo Stretch, Palette/Contrast/Alt).
6. In-memory REST API contract tests for POST /api/visual/inspect using HTTPTestClient.
"""

import io
import os
import sys
import json
import math
import unittest
from typing import Dict, Any, Tuple

# Path configuration
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CODEX_ROOT = os.path.join(REPO_ROOT, "codex")
BACKEND_DIR = os.path.join(CODEX_ROOT, "backend")

for p in [REPO_ROOT, CODEX_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import server
from app.core.review_engine import DeterministicReviewEngine, deterministic_engine


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


class TestVisualComplianceEngine(unittest.TestCase):
    """Test suite for deterministic visual compliance rules in DeterministicReviewEngine."""

    def setUp(self):
        self.engine = DeterministicReviewEngine()

    # -------------------------------------------------------------------------
    # 1. Geometry Aspect Ratio Distortion Boundary Tests (2.0% boundary)
    # -------------------------------------------------------------------------
    def test_geometry_distortion_pass_within_threshold(self):
        """Aspect ratio drift <= 2.0% is compliant and raises no logo_distortion violation."""
        # 1.99% positive drift
        result_199 = self.engine.inspect_visual_geometry_and_palette({
            "aspect_ratio": 1.0199,
            "expected_aspect_ratio": 1.0,
            "alt_text": "Valid logo alt text"
        })
        self.assertEqual(result_199["aspect_ratio_drift"], 1.99)
        geom_violations = [v for v in result_199["violations"] if v["type"] == "logo_distortion"]
        self.assertEqual(len(geom_violations), 0)

        # Exact 2.00% boundary drift
        result_200 = self.engine.inspect_visual_geometry_and_palette({
            "aspect_ratio": 1.0200,
            "expected_aspect_ratio": 1.0,
            "alt_text": "Valid logo alt text"
        })
        self.assertEqual(result_200["aspect_ratio_drift"], 2.00)
        geom_violations = [v for v in result_200["violations"] if v["type"] == "logo_distortion"]
        self.assertEqual(len(geom_violations), 0)

        # 0.0% drift (perfect ratio match)
        result_zero = self.engine.inspect_visual_geometry_and_palette({
            "aspect_ratio": 1.0,
            "expected_aspect_ratio": 1.0,
            "alt_text": "Valid logo alt text"
        })
        self.assertEqual(result_zero["aspect_ratio_drift"], 0.0)
        geom_violations = [v for v in result_zero["violations"] if v["type"] == "logo_distortion"]
        self.assertEqual(len(geom_violations), 0)

    def test_geometry_distortion_fail_beyond_threshold(self):
        """Aspect ratio drift > 2.0% (e.g. 2.01%) flags high-severity logo_distortion violation."""
        # 2.01% boundary failure
        result_201 = self.engine.inspect_visual_geometry_and_palette({
            "aspect_ratio": 1.0201,
            "expected_aspect_ratio": 1.0,
            "alt_text": "Valid logo alt text"
        })
        self.assertEqual(result_201["aspect_ratio_drift"], 2.01)
        geom_violations = [v for v in result_201["violations"] if v["type"] == "logo_distortion"]
        self.assertEqual(len(geom_violations), 1)
        self.assertEqual(geom_violations[0]["severity"], "high")
        self.assertIn("2.01%", geom_violations[0]["message"])
        self.assertIn("Brand Identity Guidelines", geom_violations[0]["source_ref"])

        # Significant 8.0% stretch (e.g. Preset 2)
        result_80 = self.engine.inspect_visual_geometry_and_palette({
            "aspect_ratio": 1.08,
            "expected_aspect_ratio": 1.0,
            "alt_text": "Valid logo alt text"
        })
        self.assertEqual(result_80["aspect_ratio_drift"], 8.0)
        self.assertTrue(any(v["type"] == "logo_distortion" for v in result_80["violations"]))

    def test_geometry_distortion_negative_boundary(self):
        """Aspect ratio shrinkage (drift below 1.0) also obeys the 2.0% boundary."""
        # 0.9801 -> 1.99% drift -> pass
        res_pass = self.engine.inspect_visual_geometry_and_palette({
            "aspect_ratio": 0.9801,
            "expected_aspect_ratio": 1.0,
            "alt_text": "Logo"
        })
        self.assertEqual(res_pass["aspect_ratio_drift"], 1.99)
        self.assertEqual(len([v for v in res_pass["violations"] if v["type"] == "logo_distortion"]), 0)

        # 0.9800 -> 2.00% drift -> pass
        res_boundary = self.engine.inspect_visual_geometry_and_palette({
            "aspect_ratio": 0.9800,
            "expected_aspect_ratio": 1.0,
            "alt_text": "Logo"
        })
        self.assertEqual(res_boundary["aspect_ratio_drift"], 2.00)
        self.assertEqual(len([v for v in res_boundary["violations"] if v["type"] == "logo_distortion"]), 0)

        # 0.9799 -> 2.01% drift -> fail
        res_fail = self.engine.inspect_visual_geometry_and_palette({
            "aspect_ratio": 0.9799,
            "expected_aspect_ratio": 1.0,
            "alt_text": "Logo"
        })
        self.assertEqual(res_fail["aspect_ratio_drift"], 2.01)
        self.assertEqual(len([v for v in res_fail["violations"] if v["type"] == "logo_distortion"]), 1)

    def test_geometry_custom_expected_ratio(self):
        """Evaluates geometry distortion relative to custom non-square expected ratios (e.g. 16:9)."""
        expected_16_9 = 16.0 / 9.0  # 1.7777...
        # Exactly expected ratio
        res_exact = self.engine.inspect_visual_geometry_and_palette({
            "aspect_ratio": expected_16_9,
            "expected_aspect_ratio": expected_16_9,
            "alt_text": "Header Banner"
        })
        self.assertEqual(res_exact["aspect_ratio_drift"], 0.0)
        self.assertFalse(any(v["type"] == "logo_distortion" for v in res_exact["violations"]))

        # Distorted 16:9 banner (ratio 1.90, drift ~ 6.88%)
        res_distorted = self.engine.inspect_visual_geometry_and_palette({
            "aspect_ratio": 1.90,
            "expected_aspect_ratio": expected_16_9,
            "alt_text": "Header Banner"
        })
        self.assertGreater(res_distorted["aspect_ratio_drift"], 2.0)
        self.assertTrue(any(v["type"] == "logo_distortion" for v in res_distorted["violations"]))

    # -------------------------------------------------------------------------
    # 2. Brand Palette Euclidean RGB Distance Threshold Tests (15.0 to 65.0)
    # -------------------------------------------------------------------------
    def test_palette_drift_primary_color_thresholds(self):
        """Tests Euclidean distance boundaries from Primary brand color #0F172A (15, 23, 42)."""
        # Exact color: distance = 0.0 -> pass
        res_exact = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#0F172A"],
            "alt_text": "Valid alt"
        })
        self.assertEqual(len([v for v in res_exact["violations"] if v["type"] == "palette_drift"]), 0)

        # Distance = 14.0 ((29, 23, 42) -> #1D172A) < 15.0 -> pass (within brand tolerance)
        res_14 = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#1D172A"],
            "alt_text": "Valid alt"
        })
        self.assertEqual(len([v for v in res_14["violations"] if v["type"] == "palette_drift"]), 0)

        # Distance = 15.0 ((30, 23, 42) -> #1E172A) == 15.0 -> fail (palette_drift)
        res_15 = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#1E172A"],
            "alt_text": "Valid alt"
        })
        p_drift = [v for v in res_15["violations"] if v["type"] == "palette_drift"]
        self.assertEqual(len(p_drift), 1)
        self.assertEqual(p_drift[0]["severity"], "medium")
        self.assertIn("primary", p_drift[0]["message"])

        # Distance = 50.0 ((65, 23, 42) -> #41172A) in [15.0, 65.0] -> fail (palette_drift)
        res_50 = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#41172A"],
            "alt_text": "Valid alt"
        })
        self.assertEqual(len([v for v in res_50["violations"] if v["type"] == "palette_drift"]), 1)

        # Distance = 65.0 ((80, 23, 42) -> #50172A) == 65.0 -> fail (palette_drift)
        res_65 = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#50172A"],
            "alt_text": "Valid alt"
        })
        self.assertEqual(len([v for v in res_65["violations"] if v["type"] == "palette_drift"]), 1)

        # Distance = 66.0 ((81, 23, 42) -> #51172A) > 65.0 -> pass (independent color, not near-brand drift)
        res_66 = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#51172A"],
            "alt_text": "Valid alt"
        })
        self.assertEqual(len([v for v in res_66["violations"] if v["type"] == "palette_drift"]), 0)

    def test_palette_drift_accent_color_thresholds(self):
        """Tests Euclidean distance boundaries from Accent brand color #0284C7 (2, 132, 199)."""
        # Exact accent: distance = 0.0 -> pass
        res_exact = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#0284C7"],
            "alt_text": "Valid alt"
        })
        self.assertEqual(len([v for v in res_exact["violations"] if v["type"] == "palette_drift"]), 0)

        # Distance = 14.0 ((2, 146, 199) -> #0292C7) < 15.0 -> pass
        res_14 = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#0292C7"],
            "alt_text": "Valid alt"
        })
        self.assertEqual(len([v for v in res_14["violations"] if v["type"] == "palette_drift"]), 0)

        # Distance = 15.0 ((2, 147, 199) -> #0293C7) == 15.0 -> fail (palette_drift)
        res_15 = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#0293C7"],
            "alt_text": "Valid alt"
        })
        p_drift = [v for v in res_15["violations"] if v["type"] == "palette_drift"]
        self.assertEqual(len(p_drift), 1)
        self.assertEqual(p_drift[0]["severity"], "medium")
        self.assertIn("accent", p_drift[0]["message"])

        # Distance = 65.0 ((2, 197, 199) -> #02C5C7) == 65.0 -> fail (palette_drift)
        res_65 = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#02C5C7"],
            "alt_text": "Valid alt"
        })
        self.assertEqual(len([v for v in res_65["violations"] if v["type"] == "palette_drift"]), 1)

        # Distance = 70.0 ((2, 202, 199) -> #02CAC7) > 65.0 -> pass
        res_70 = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#02CAC7"],
            "alt_text": "Valid alt"
        })
        self.assertEqual(len([v for v in res_70["violations"] if v["type"] == "palette_drift"]), 0)

    def test_palette_drift_success_color_thresholds(self):
        """Tests Euclidean distance boundaries from Success brand color #10B981 (16, 185, 129)."""
        # Exact success: distance = 0.0 -> pass
        res_exact = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#10B981"],
            "alt_text": "Valid alt"
        })
        self.assertEqual(len([v for v in res_exact["violations"] if v["type"] == "palette_drift"]), 0)

        # Distance = 14.0 ((16, 185, 143) -> #10B98F) < 15.0 -> pass
        res_14 = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#10B98F"],
            "alt_text": "Valid alt"
        })
        self.assertEqual(len([v for v in res_14["violations"] if v["type"] == "palette_drift"]), 0)

        # Distance = 15.0 ((16, 185, 144) -> #10B990) == 15.0 -> fail (palette_drift)
        res_15 = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#10B990"],
            "alt_text": "Valid alt"
        })
        p_drift = [v for v in res_15["violations"] if v["type"] == "palette_drift"]
        self.assertEqual(len(p_drift), 1)
        self.assertEqual(p_drift[0]["severity"], "medium")
        self.assertIn("success", p_drift[0]["message"])

        # Distance = 65.0 ((16, 185, 194) -> #10B9C2) == 65.0 -> fail (palette_drift)
        res_65 = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#10B9C2"],
            "alt_text": "Valid alt"
        })
        self.assertEqual(len([v for v in res_65["violations"] if v["type"] == "palette_drift"]), 1)

        # Distant non-brand color (e.g. #FFAA00 bright orange, dist > 100) -> pass
        res_orange = self.engine.inspect_visual_geometry_and_palette({
            "detected_hex_colors": ["#FFAA00"],
            "alt_text": "Valid alt"
        })
        self.assertEqual(len([v for v in res_orange["violations"] if v["type"] == "palette_drift"]), 0)

    # -------------------------------------------------------------------------
    # 3. WCAG 2.2 Contrast Ratio Boundary Tests (4.5:1 boundary)
    # -------------------------------------------------------------------------
    def test_contrast_ratio_pass_and_fail_boundaries(self):
        """Tests WCAG 2.2 AA 4.5:1 contrast ratio pass and fail boundaries."""
        # 4.51:1 (#73777b on #ffffff) -> pass
        ratio_451 = self.engine.calculate_contrast_ratio("#73777b", "#ffffff")
        self.assertGreaterEqual(ratio_451, 4.5)
        res_451 = self.engine.inspect_visual_geometry_and_palette({
            "disclaimer_fg": "#73777b",
            "disclaimer_bg": "#ffffff",
            "alt_text": "Valid alt"
        })
        self.assertEqual(len([v for v in res_451["violations"] if v["type"] == "contrast_failure"]), 0)

        # Exact 4.50:1 boundary (#737873 on #ffffff) -> pass
        ratio_450 = self.engine.calculate_contrast_ratio("#737873", "#ffffff")
        self.assertEqual(ratio_450, 4.5)
        res_450 = self.engine.inspect_visual_geometry_and_palette({
            "disclaimer_fg": "#737873",
            "disclaimer_bg": "#ffffff",
            "alt_text": "Valid alt"
        })
        self.assertEqual(len([v for v in res_450["violations"] if v["type"] == "contrast_failure"]), 0)

        # 4.49:1 (#747873 on #ffffff) -> fail
        ratio_449 = self.engine.calculate_contrast_ratio("#747873", "#ffffff")
        self.assertLess(ratio_449, 4.5)
        res_449 = self.engine.inspect_visual_geometry_and_palette({
            "disclaimer_fg": "#747873",
            "disclaimer_bg": "#ffffff",
            "alt_text": "Valid alt"
        })
        contrast_violations = [v for v in res_449["violations"] if v["type"] == "contrast_failure"]
        self.assertEqual(len(contrast_violations), 1)
        self.assertEqual(contrast_violations[0]["severity"], "high")
        self.assertIn("fails WCAG 2.2 AA", contrast_violations[0]["message"])

        # Severe contrast failure (#94A3B8 on #ffffff, 2.56:1) -> fail
        res_poor = self.engine.inspect_visual_geometry_and_palette({
            "disclaimer_fg": "#94A3B8",
            "disclaimer_bg": "#ffffff",
            "alt_text": "Valid alt"
        })
        self.assertEqual(res_poor["contrast_ratio"], 2.56)
        self.assertEqual(len([v for v in res_poor["violations"] if v["type"] == "contrast_failure"]), 1)

        # Inverted polarity (#ffffff on #94A3B8) yields same 2.56 ratio -> fail
        res_inverted = self.engine.inspect_visual_geometry_and_palette({
            "disclaimer_fg": "#ffffff",
            "disclaimer_bg": "#94A3B8",
            "alt_text": "Valid alt"
        })
        self.assertEqual(res_inverted["contrast_ratio"], 2.56)
        self.assertEqual(len([v for v in res_inverted["violations"] if v["type"] == "contrast_failure"]), 1)

    # -------------------------------------------------------------------------
    # 4. Alt-Text Presence and Accessibility Validation
    # -------------------------------------------------------------------------
    def test_alt_text_validation(self):
        """Verifies descriptive alt text passes while empty, whitespace-only, or None fails."""
        # Descriptive alt text -> pass
        res_valid = self.engine.inspect_visual_geometry_and_palette({
            "alt_text": "Clinical study chart showing 94.2% hydration increase in 14 days"
        })
        self.assertEqual(len([v for v in res_valid["violations"] if v["type"] == "missing_alt_text"]), 0)

        # Empty string -> fail
        res_empty = self.engine.inspect_visual_geometry_and_palette({
            "alt_text": ""
        })
        alt_violations = [v for v in res_empty["violations"] if v["type"] == "missing_alt_text"]
        self.assertEqual(len(alt_violations), 1)
        self.assertEqual(alt_violations[0]["severity"], "medium")
        self.assertIn("WCAG 2.2 §1.1.1", alt_violations[0]["source_ref"])

        # Whitespace-only string -> fail
        res_spaces = self.engine.inspect_visual_geometry_and_palette({
            "alt_text": "   \t\n  "
        })
        self.assertEqual(len([v for v in res_spaces["violations"] if v["type"] == "missing_alt_text"]), 1)

        # None / missing alt_text -> fail
        res_none = self.engine.inspect_visual_geometry_and_palette({})
        self.assertEqual(len([v for v in res_none["violations"] if v["type"] == "missing_alt_text"]), 1)

    # -------------------------------------------------------------------------
    # 5. Synthetic Visual Asset Presets Validation (Presets 1, 2, 3)
    # -------------------------------------------------------------------------
    def test_preset_1_compliant_asset(self):
        """Preset 1 (Compliant Hero Asset) passes all visual checks with zero violations."""
        preset = {
            "asset_id": "preset-compliant-hero.png",
            "aspect_ratio": 1.0,
            "expected_aspect_ratio": 1.0,
            "detected_hex_colors": ["#0F172A", "#0284C7", "#10B981"],
            "disclaimer_fg": "#0F172A",
            "disclaimer_bg": "#FFFFFF",
            "alt_text": "Brand logo with clinical hydration claim"
        }
        res = self.engine.inspect_visual_geometry_and_palette(preset)
        self.assertTrue(res["is_compliant"])
        self.assertEqual(len(res["violations"]), 0)
        self.assertEqual(res["aspect_ratio_drift"], 0.0)
        self.assertGreaterEqual(res["contrast_ratio"], 15.0)
        self.assertEqual(res["asset_id"], "preset-compliant-hero.png")

    def test_preset_2_logo_geometry_drift(self):
        """Preset 2 (Logo Geometry Drift) triggers high severity logo_distortion (8.0% drift)."""
        preset = {
            "asset_id": "preset-logo-geom-drift.png",
            "aspect_ratio": 1.08,
            "expected_aspect_ratio": 1.0,
            "detected_hex_colors": ["#0F172A", "#0284C7", "#10B981"],
            "disclaimer_fg": "#0F172A",
            "disclaimer_bg": "#FFFFFF",
            "alt_text": "DermaCare product banner with 8% horizontal logo stretch"
        }
        res = self.engine.inspect_visual_geometry_and_palette(preset)
        self.assertFalse(res["is_compliant"])
        self.assertEqual(len(res["violations"]), 1)
        v = res["violations"][0]
        self.assertEqual(v["type"], "logo_distortion")
        self.assertEqual(v["severity"], "high")
        self.assertEqual(res["aspect_ratio_drift"], 8.0)

    def test_preset_3_palette_drift_contrast_and_alt_failure(self):
        """Preset 3 (Palette Drift + Contrast Failure) triggers palette_drift, contrast_failure, and missing_alt_text."""
        preset = {
            "asset_id": "preset-palette-contrast-fail.png",
            "aspect_ratio": 1.0,
            "expected_aspect_ratio": 1.0,
            "detected_hex_colors": ["#3A3A3A"],
            "disclaimer_fg": "#94A3B8",
            "disclaimer_bg": "#FFFFFF",
            "alt_text": ""
        }
        res = self.engine.inspect_visual_geometry_and_palette(preset)
        self.assertFalse(res["is_compliant"])
        self.assertEqual(len(res["violations"]), 3)

        v_types = {v["type"]: v for v in res["violations"]}
        self.assertIn("palette_drift", v_types)
        self.assertEqual(v_types["palette_drift"]["severity"], "medium")

        self.assertIn("contrast_failure", v_types)
        self.assertEqual(v_types["contrast_failure"]["severity"], "high")
        self.assertEqual(res["contrast_ratio"], 2.56)

        self.assertIn("missing_alt_text", v_types)
        self.assertEqual(v_types["missing_alt_text"]["severity"], "medium")

    # -------------------------------------------------------------------------
    # 6. In-Memory REST API Contract Tests for POST /api/visual/inspect
    # -------------------------------------------------------------------------
    def test_api_visual_inspect_success_compliant(self):
        """POST /api/visual/inspect returns 200, status=success, and is_compliant=True for valid asset."""
        payload = {
            "asset_id": "api-hero-001",
            "aspect_ratio": 1.0,
            "expected_aspect_ratio": 1.0,
            "detected_hex_colors": ["#0F172A", "#0284C7"],
            "disclaimer_fg": "#FFFFFF",
            "disclaimer_bg": "#0F172A",
            "alt_text": "Valid brand banner with clinical claims"
        }
        status, headers, body = HTTPTestClient.post("/api/visual/inspect", json_data=payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertIn("result", data)
        res = data["result"]
        self.assertTrue(res.get("is_compliant"))
        self.assertEqual(res.get("violations"), [])
        self.assertEqual(res.get("asset_id"), "api-hero-001")

    def test_api_visual_inspect_success_with_violations(self):
        """POST /api/visual/inspect returns 200, status=success, and violations array for non-compliant asset."""
        payload = {
            "asset_id": "api-distorted-002",
            "aspect_ratio": 1.15,
            "expected_aspect_ratio": 1.0,
            "detected_hex_colors": ["#3A3A3A"],
            "disclaimer_fg": "#94A3B8",
            "disclaimer_bg": "#FFFFFF",
            "alt_text": ""
        }
        status, headers, body = HTTPTestClient.post("/api/visual/inspect", json_data=payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        res = data["result"]
        self.assertFalse(res.get("is_compliant"))
        violations = res.get("violations", [])
        self.assertEqual(len(violations), 4)
        v_types = [v.get("type") for v in violations]
        self.assertIn("logo_distortion", v_types)
        self.assertIn("palette_drift", v_types)
        self.assertIn("contrast_failure", v_types)
        self.assertIn("missing_alt_text", v_types)

    def test_api_visual_inspect_malformed_json_returns_400(self):
        """POST /api/visual/inspect returns 400 when malformed non-JSON body is sent."""
        status, headers, body = HTTPTestClient.post("/api/visual/inspect", raw_body=b"{invalid: json,")
        self.assertEqual(status, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "error")
        self.assertIn("Invalid JSON payload", data.get("message", ""))

    def test_api_visual_inspect_non_dict_payload_returns_400(self):
        """POST /api/visual/inspect returns 400 when body is a JSON list instead of an object."""
        status, headers, body = HTTPTestClient.post("/api/visual/inspect", json_data=["not", "an", "object"])
        self.assertEqual(status, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "error")
        self.assertIn("must be a JSON object", data.get("message", ""))

    def test_api_visual_inspect_empty_object_handled_gracefully(self):
        """POST /api/visual/inspect handles empty object gracefully without 500 server crash."""
        status, headers, body = HTTPTestClient.post("/api/visual/inspect", json_data={})
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        res = data.get("result", {})
        self.assertFalse(res.get("is_compliant"))  # Missing alt text triggers violation
        self.assertTrue(any(v.get("type") == "missing_alt_text" for v in res.get("violations", [])))

    def test_api_visual_inspect_codex_prefix_routing(self):
        """POST /codex/api/visual/inspect correctly routes via path normalizer."""
        payload = {
            "aspect_ratio": 1.0,
            "expected_aspect_ratio": 1.0,
            "detected_hex_colors": ["#0F172A"],
            "disclaimer_fg": "#0F172A",
            "disclaimer_bg": "#FFFFFF",
            "alt_text": "Compliant hero banner"
        }
        status, headers, body = HTTPTestClient.post("/codex/api/visual/inspect", json_data=payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")


if __name__ == "__main__":
    unittest.main(verbosity=2)
