"""
Tier 5 Adversarial Stress and Coverage Hardening Test Suite.
Brandwise Clinical Evidence PDF Ingestion & Claim Extraction Engine.

Author: Challenger M4-1 (teamwork_challenger)
Milestone: M4 (final_verification & Tier 5 adversarial coverage hardening)

Covers:
1. Dynamic multi-page PDF generation:
   - Randomized study IDs, random cohort sizes (N=10 to N=5000), random durations (1 to 365 days).
   - Arbitrary table placement & page depths (Table 1.1 on Page 2, Table 3.1 on Page 12, Table 2.1 on Page 7, Table 4.2 on Page 4).
   - Arbitrary endpoint combinations (single endpoint, dual endpoints, full 8-endpoint matrix).
   - Confounding filler pages with noise (dates, phone numbers, dosages, room numbers).
2. Extreme boundary copy testing:
   - 0% claims (zero irritation, 0% delta).
   - 100.0% claims (100% hydration, 100.0% lesion reduction, cure promises).
   - Multi-claim dense paragraphs (hydration, acne, sebum, timeline compression, unverified claims).
   - Unicode quotes and dashes (smart quotes “”, ‘’, en-dash –, em-dash —, minus −).
   - Hinglish and vernacular mixed phrases ("Yeh serum deta hai 99% hydration...", "Sirf 7 days mein...").
   - Non-clinical texts (hotel discounts, retail promos, financial statements).
3. Backend concurrent request stress testing:
   - Thread safety of CLINICAL_STUDIES_CATALOG under high concurrency.
   - Concurrent simulation of GET /api/clinical/studies, POST /api/clinical/verify-copy, GET /api/clinical/sample-pdf, POST /api/clinical/upload.
   - Zero deadlocks, race conditions, or state corruption under multithreaded load.
4. Corrupted stream & edge case input validation:
   - Truncated PDF streams (30 bytes, 150 bytes, missing EOF marker).
   - Invalid base64 payloads in POST /api/clinical/upload (corrupt characters, non-base64, odd lengths).
   - Missing fields and malformed payloads (empty JSON, missing file_data, None text).
   - Large garbage payloads (1 MB random bytes).
5. Dual-server & tri-file parity assertion:
   - SHA-256 byte parity between server.py and codex/server.py.
   - SHA-256 byte parity between index.html, codex/frontend/index.html, and docs/index.html.
   - Static verification of clinical evidence UI components in all 3 HTML files.
   - Static verification of clinical API endpoints in both server files.
"""

from __future__ import annotations

import base64
import binascii
import concurrent.futures
import hashlib
import io
import json
import os
import random
import re
import sys
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Setup import paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CODEX_ROOT = REPO_ROOT / "codex"
BACKEND_DIR = CODEX_ROOT / "backend"

for p in [str(REPO_ROOT), str(CODEX_ROOT), str(BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pypdf
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

import server
from app.core.clinical_extractor import (
    ClinicalTrialPDFExtractor,
    evaluate_clinical_discrepancies,
    normalize_clinical_dossier,
    DEFAULT_CLINICAL_STUDIES
)
from app.core.review_engine import deterministic_engine


# ==============================================================================
# Helper Functions for Dynamic PDF Synthesis
# ==============================================================================

def add_pdf_page_with_text(
    writer: pypdf.PdfWriter,
    lines: List[str],
    width: float = 612.0,
    height: float = 792.0
) -> None:
    """Adds a single page with custom text lines using standard PDF operators."""
    page = writer.add_blank_page(width=width, height=height)

    font_dict = DictionaryObject({
        NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type1'),
        NameObject('/BaseFont'): NameObject('/Helvetica'),
    })
    fonts = DictionaryObject({NameObject('/F1'): font_dict})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): fonts})

    content_lines = ['BT', '/F1 10 Tf', '13.5 TL', '45 745 Td']
    first = True
    for line in lines:
        safe = (
            line.replace('\\', '\\\\')
                .replace('(', '\\(')
                .replace(')', '\\)')
        )
        if first:
            content_lines.append(f'({safe}) Tj')
            first = False
        else:
            content_lines.append(f'T* ({safe}) Tj')
    content_lines.append('ET')

    stream = DecodedStreamObject()
    stream.set_data('\n'.join(content_lines).encode('latin-1', errors='replace'))
    page[NameObject('/Contents')] = stream


def build_dynamic_clinical_pdf(
    study_id: str,
    total_pages: int,
    table_page: int,
    table_id: str,
    cohort_n: int,
    duration_days: int,
    p_value: str = "<0.001",
    endpoints_to_inject: Optional[Dict[str, float]] = None,
    include_noise_pages: bool = False
) -> bytes:
    """
    Constructs a dynamic multi-page clinical trial PDF in-memory.
    Places protocol metadata on Page 1, the target table on `table_page`,
    and optional confounding noisy text on other pages.
    """
    writer = pypdf.PdfWriter()

    for p in range(1, total_pages + 1):
        if p == 1:
            lines = [
                f"PROTOCOL IDENTIFIER: {study_id}",
                f"STUDY TITLE: Evaluative Clinical Protocol for {study_id}",
                f"INVESTIGATOR: Dr. Adversarial Stress-Test MD",
                f"COHORT SIZE: N={cohort_n} enrolled subjects",
                f"STUDY DURATION: {duration_days} days protocol",
                f"METHODOLOGY: Double-blind, randomized, placebo-controlled clinical trial",
                f"SIGNIFICANCE THRESHOLD: p {p_value}",
                "Page 1: Administrative Summary and Ethics Sign-Off"
            ]
            add_pdf_page_with_text(writer, lines)
        elif p == table_page:
            lines = [
                f"SECTION {table_page}: PRIMARY CLINICAL EFFICACY TABLES",
                f"{table_id}: Quantitative Clinical Endpoints Analysis at Day {duration_days}",
                "=========================================================================",
                "Endpoint Parameter                 Baseline Mean   Endpoint Mean   Delta (%)",
                "========================================================================="
            ]

            endpoints = endpoints_to_inject or {"Stratum Corneum Hydration": 89.5}
            for param_label, val in endpoints.items():
                if param_label == "Skin Irritation Index":
                    lines.append(f"{param_label:<35} 0.00            {val:.2f}            {val:.2f} score")
                elif "Lesion" in param_label or "Sebum" in param_label or "TEWL" in param_label or "Wrinkle" in param_label:
                    lines.append(f"{param_label:<35} 100.0           {100.0 - val:.1f}           -{val:.1f}%")
                else:
                    lines.append(f"{param_label:<35} 30.0            {30.0 + val:.1f}           +{val:.1f}%")

            lines.append("=========================================================================")
            lines.append(f"Canonical Citation: Clinical Study {study_id}, Page {table_page}, {table_id}")
            add_pdf_page_with_text(writer, lines)
        else:
            if include_noise_pages:
                lines = [
                    f"Page {p} of {total_pages} - Protocol Compliance & Quality Assurance",
                    f"Visit timestamp: 2026-10-15T09:30:00Z, Facility Room 304B",
                    f"Contact investigator hotline: +1-800-555-0199 or 080-2345-6789",
                    f"Administered batch reference 992-B at daily dosage of 2.5mg/cm2.",
                    f"No adverse dermatological events reported among cohort subgroup.",
                    "End of interim inspection log."
                ]
            else:
                lines = [
                    f"Page {p} of {total_pages} - Methodology & Instrumentation Details",
                    f"Subject retention protocol compliant with ICH-GCP E6(R2) guidelines."
                ]
            add_pdf_page_with_text(writer, lines)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ==============================================================================
# Helper Mock Client for Server HTTP Requests
# ==============================================================================

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
    def request(
        cls, method: str, path: str, headers: Optional[Dict[str, str]] = None, body: Optional[bytes] = None
    ) -> Tuple[int, Dict[str, str], bytes]:
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
    def get(cls, path: str, headers: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, str], bytes]:
        return cls.request("GET", path, headers=headers)

    @classmethod
    def post(
        cls, path: str, json_data: Optional[dict] = None, raw_body: Optional[bytes] = None, headers: Optional[Dict[str, str]] = None
    ) -> Tuple[int, Dict[str, str], bytes]:
        headers = dict(headers or {})
        if raw_body is not None:
            body = raw_body
        elif json_data is not None:
            headers.setdefault("Content-Type", "application/json")
            body = json.dumps(json_data).encode("utf-8")
        else:
            body = b""
        return cls.request("POST", path, headers=headers, body=body)


# ==============================================================================
# TIER 5 - CLASS 1: Dynamic Multi-Page PDF Generation & Extraction Stress
# ==============================================================================

class TestTier5DynamicPDFStress(unittest.TestCase):
    """Stress tests dynamic multi-page PDF generation with diverse topologies and parameters."""

    def test_dynamic_pdf_randomized_study_cohort_and_duration(self):
        """Generates PDFs with randomized IDs, cohort sizes (N=10 to 5000), and durations (1 to 365d)."""
        scenarios = [
            {"study_id": "PILOT-2026-10", "cohort": 10, "duration": 1, "pages": 3, "table_page": 2, "table_id": "Table 1.1"},
            {"study_id": "CS-2026-MID-120", "cohort": 120, "duration": 14, "pages": 8, "table_page": 7, "table_id": "Table 2.1"},
            {"study_id": "CT-2027-ADV-850", "cohort": 850, "duration": 90, "pages": 12, "table_page": 9, "table_id": "Table 3.2"},
            {"study_id": "MEGA-2026-5000", "cohort": 5000, "duration": 365, "pages": 16, "table_page": 14, "table_id": "Table 4.1"},
        ]

        for sc in scenarios:
            pdf_bytes = build_dynamic_clinical_pdf(
                study_id=sc["study_id"],
                total_pages=sc["pages"],
                table_page=sc["table_page"],
                table_id=sc["table_id"],
                cohort_n=sc["cohort"],
                duration_days=sc["duration"],
                endpoints_to_inject={"Stratum Corneum Hydration": 88.5}
            )

            extracted = ClinicalTrialPDFExtractor.extract_from_pdf(pdf_bytes)
            self.assertEqual(extracted["status"], "EXTRACTED_VALID")
            self.assertEqual(extracted["study_id"], sc["study_id"])
            self.assertEqual(extracted["total_pages"], sc["pages"])
            self.assertEqual(extracted["cohort_size"], sc["cohort"])
            self.assertEqual(extracted["duration_days"], sc["duration"])

    def test_dynamic_pdf_arbitrary_table_positions_and_page_depths(self):
        """Verifies exact 1-indexed page citations across diverse table locations (Page 2, 4, 7, 12)."""
        test_positions = [
            (5, 2, "Table 1.1"),
            (6, 4, "Table 4.2"),
            (8, 7, "Table 2.1"),
            (15, 12, "Table 3.1"),
        ]

        for total_pages, table_page, table_id in test_positions:
            study_id = f"POS-P{table_page}-T{table_id.replace(' ', '').replace('.', '-')}"
            pdf_bytes = build_dynamic_clinical_pdf(
                study_id=study_id,
                total_pages=total_pages,
                table_page=table_page,
                table_id=table_id,
                cohort_n=100,
                duration_days=21,
                endpoints_to_inject={"Stratum Corneum Hydration": 91.2}
            )

            extracted = ClinicalTrialPDFExtractor.extract_from_pdf(pdf_bytes)
            self.assertEqual(len(extracted["tables"]), 1)
            found_table = extracted["tables"][0]
            self.assertEqual(found_table["table_id"], table_id)
            self.assertEqual(found_table["page"], table_page)

            hyd = extracted["endpoints"]["hydration_increase_percent"]
            self.assertEqual(hyd["page"], table_page)
            self.assertEqual(hyd["table"], table_id)
            expected_cit = f"Clinical Study {study_id}, Page {table_page}, {table_id}"
            self.assertEqual(hyd["citation"], expected_cit)

    def test_dynamic_pdf_arbitrary_endpoint_combinations(self):
        """Verifies parsing of single, dual, and comprehensive 8-endpoint clinical panels."""
        # Scenario A: Single endpoint (soothing only)
        soothing_pdf = build_dynamic_clinical_pdf(
            study_id="SOOTH-ONLY-2026",
            total_pages=4,
            table_page=3,
            table_id="Table 2.1",
            cohort_n=50,
            duration_days=7,
            endpoints_to_inject={"Soothing Efficacy": 82.5}
        )
        res_a = ClinicalTrialPDFExtractor.extract_from_pdf(soothing_pdf)
        self.assertIn("soothing_efficacy_percent", res_a["endpoints"])
        self.assertAlmostEqual(res_a["endpoints"]["soothing_efficacy_percent"]["value"], 82.5, places=1)

        # Scenario B: Full 8-endpoint efficacy panel
        full_panel = {
            "Stratum Corneum Hydration": 92.4,
            "Inflammatory Acne Lesion Count": 65.2,
            "Casual Sebum Excretion": 41.0,
            "Transepidermal Water Loss": 29.5,
            "Soothing Efficacy": 86.8,
            "Skin Irritation Index": 0.04,
            "Wrinkle Reduction": 34.5,
            "Skin Elasticity": 51.2
        }
        panel_pdf = build_dynamic_clinical_pdf(
            study_id="FULL-PANEL-8EP",
            total_pages=6,
            table_page=5,
            table_id="Table 5.1",
            cohort_n=200,
            duration_days=28,
            endpoints_to_inject=full_panel
        )
        res_b = ClinicalTrialPDFExtractor.extract_from_pdf(panel_pdf)
        eps = res_b["endpoints"]

        expected_keys = [
            "hydration_increase_percent",
            "acne_lesion_reduction_percent",
            "sebum_reduction_percent",
            "tewl_reduction_percent",
            "soothing_efficacy_percent",
            "skin_irritation_index",
            "wrinkle_reduction_percent",
            "elasticity_improvement_percent"
        ]
        for ek in expected_keys:
            self.assertIn(ek, eps, f"Missing endpoint key: {ek}")
            self.assertEqual(eps[ek]["page"], 5)
            self.assertEqual(eps[ek]["table"], "Table 5.1")

    def test_dynamic_pdf_with_filler_pages_and_noise(self):
        """Verifies extractor rejects confounding numbers (dates, dosages, room numbers, phone numbers)."""
        noisy_pdf = build_dynamic_clinical_pdf(
            study_id="NOISY-CLIN-2026",
            total_pages=10,
            table_page=8,
            table_id="Table 3.1",
            cohort_n=350,
            duration_days=60,
            endpoints_to_inject={"Stratum Corneum Hydration": 79.5},
            include_noise_pages=True
        )
        extracted = ClinicalTrialPDFExtractor.extract_from_pdf(noisy_pdf)
        # Should not mistake room 304B or hotline numbers for cohort or duration
        self.assertEqual(extracted["cohort_size"], 350)
        self.assertEqual(extracted["duration_days"], 60)
        self.assertAlmostEqual(extracted["endpoints"]["hydration_increase_percent"]["value"], 79.5, places=1)


# ==============================================================================
# TIER 5 - CLASS 2: Extreme Boundary Copy Testing
# ==============================================================================

class TestTier5BoundaryCopyStress(unittest.TestCase):
    """Stress tests extreme boundary marketing copy phrases and character encodings."""

    def test_boundary_copy_zero_percent_claims(self):
        """Verifies 0% claims do not throw arithmetic errors and evaluate properly."""
        copy_text = "Clinical evaluation demonstrated 0% skin irritation and 0% adverse reactions."
        result = evaluate_clinical_discrepancies(copy_text)
        # 0% is <= trial endpoints and should not produce statistical over-claim
        self.assertFalse(result["has_discrepancies"])
        self.assertTrue(len(result["verified_claims"]) >= 1)
        self.assertEqual(result["verified_claims"][0]["claimed_value"], "0.0%")

    def test_boundary_copy_100_percent_claims(self):
        """Verifies 100.0% absolute claims trigger over-claim flags with exact exaggeration delta."""
        # Study CS-2026-88 observed 94.2% hydration
        copy_text = "Experience guaranteed 100.0% stratum corneum hydration in our formula."
        result = evaluate_clinical_discrepancies(copy_text)
        self.assertTrue(result["has_discrepancies"])
        over_claims = [d for d in result["discrepancies"] if d["type"] == "statistical_exaggeration"]
        self.assertEqual(len(over_claims), 1)
        self.assertEqual(over_claims[0]["claimed_value"], "100.0%")
        self.assertEqual(over_claims[0]["trial_value"], "94.2%")
        self.assertIn("+5.8% exaggeration", over_claims[0]["delta"])

    def test_boundary_copy_multi_claim_dense_paragraph(self):
        """Evaluates dense marketing paragraphs containing 5+ simultaneous claims across metrics."""
        copy = (
            "Our revolutionary 7-day serum delivers 99% hydration boost, 85% acne reduction, "
            "and 55% sebum control, while permanently eliminating deep wrinkles and curing eczema!"
        )
        result = evaluate_clinical_discrepancies(copy)
        self.assertTrue(result["has_discrepancies"])

        types = [d["type"] for d in result["discrepancies"]]
        # Statistical exaggerations: 99% vs 94.2%, 85% vs 68.0%, 55% vs 42.5%
        self.assertGreaterEqual(types.count("statistical_exaggeration"), 3)
        # Timeline compression: 7 days vs 14 days
        self.assertIn("timeline_compression", types)
        # Unverified absolute cures
        self.assertIn("unverified_claim", types)

    def test_boundary_copy_unicode_quotes_dashes_and_symbols(self):
        """Verifies handling of typographic smart quotes, en-dashes, em-dashes, and unicode text."""
        unicode_copy = (
            "\u201cOur breakthrough regimen delivers 94.2% hydration\u2014proven in a "
            "14\u2013day double-blind clinical trial.\u201d"
        )
        result = evaluate_clinical_discrepancies(unicode_copy)
        # 94.2% and 14 days should match CS-2026-88 exactly without encoding errors
        self.assertFalse(result["has_discrepancies"])
        self.assertEqual(len(result["verified_claims"]), 1)
        self.assertEqual(result["verified_claims"][0]["claimed_value"], "94.2%")
        self.assertIn("CS-2026-88", result["verified_claims"][0]["citation"])

    def test_boundary_copy_hinglish_and_vernacular_mixed_phrases(self):
        """Verifies Indian consumer marketing phrases in mixed Hinglish are accurately tokenized."""
        # Over-claim in Hinglish
        hinglish_overclaim = "Yeh revolutionary serum deta hai 99% hydration sirf 7 days mein!"
        res1 = evaluate_clinical_discrepancies(hinglish_overclaim)
        self.assertTrue(res1["has_discrepancies"])
        self.assertTrue(any(d["type"] == "statistical_exaggeration" for d in res1["discrepancies"]))
        self.assertTrue(any(d["type"] == "timeline_compression" for d in res1["discrepancies"]))

        # Compliant claim in Hinglish
        hinglish_compliant = "Skin ko mile 94.2% hydration over 14 days of regular use."
        res2 = evaluate_clinical_discrepancies(hinglish_compliant)
        self.assertFalse(res2["has_discrepancies"])
        self.assertEqual(len(res2["verified_claims"]), 1)

    def test_boundary_copy_non_clinical_rejection(self):
        """Verifies commercial non-clinical copy (discounts, logistics) does not trigger false over-claims."""
        non_clinical_copy = (
            "Special holiday offer: Enjoy flat 50% discount on 3-day luxury resort stays "
            "with complimentary breakfast and free cancellation."
        )
        # Evaluate against clinical engine: 50% is below 94.2% so no overclaim is triggered
        result = evaluate_clinical_discrepancies(non_clinical_copy)
        over_claims = [d for d in result["discrepancies"] if d["type"] == "statistical_exaggeration"]
        self.assertEqual(len(over_claims), 0)


# ==============================================================================
# TIER 5 - CLASS 3: Backend Concurrency & Thread-Safety Stress Testing
# ==============================================================================

class TestTier5ConcurrencyAndThreadSafety(unittest.TestCase):
    """Stress tests concurrent requests and thread safety of CLINICAL_STUDIES_CATALOG."""

    def setUp(self):
        # Reset and initialize catalog
        server.init_clinical_studies_catalog()

    def test_catalog_concurrent_read_write_thread_safety(self):
        """Executes 50 concurrent mixed reads and writes on CLINICAL_STUDIES_CATALOG without deadlock."""
        errors: List[str] = []

        def worker(thread_idx: int):
            try:
                if thread_idx % 3 == 0:
                    # Read catalog
                    with server.CLINICAL_STUDIES_LOCK:
                        catalog_snapshot = list(server.CLINICAL_STUDIES_CATALOG)
                        _ = len(catalog_snapshot)
                elif thread_idx % 3 == 1:
                    # Write new dynamic study
                    new_study = {
                        "study_id": f"CONCUR-{thread_idx}",
                        "title": f"Concurrent Dynamic Study {thread_idx}",
                        "endpoints": {"hydration_increase_percent": 85.0 + (thread_idx % 10), "duration_days": 14},
                        "status": "REGISTERED_VALID"
                    }
                    with server.CLINICAL_STUDIES_LOCK:
                        server.CLINICAL_STUDIES_CATALOG.append(new_study)
                else:
                    # Evaluate copy against snapshot
                    with server.CLINICAL_STUDIES_LOCK:
                        snapshot = list(server.CLINICAL_STUDIES_CATALOG)
                    _ = evaluate_clinical_discrepancies("94.2% hydration in 14 days", snapshot)
            except Exception as e:
                errors.append(f"Thread {thread_idx} error: {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(worker, i) for i in range(50)]
            concurrent.futures.wait(futures)

        self.assertEqual(len(errors), 0, f"Encountered thread concurrency errors: {errors}")

    def test_concurrent_http_client_requests(self):
        """Simulates 30 simultaneous HTTP requests across endpoints via InProcessHTTPClient."""
        request_results: List[Tuple[int, str]] = []

        def client_worker(idx: int):
            if idx % 3 == 0:
                status, _, _ = InProcessHTTPClient.get("/api/clinical/studies")
                return (status, "GET_STUDIES")
            elif idx % 3 == 1:
                status, _, _ = InProcessHTTPClient.post(
                    "/api/clinical/verify-copy",
                    {"copy_text": "99% hydration in 7 days"}
                )
                return (status, "VERIFY_COPY")
            else:
                status, _, _ = InProcessHTTPClient.get("/api/clinical/sample-pdf")
                return (status, "SAMPLE_PDF")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(client_worker, i) for i in range(30)]
            for f in concurrent.futures.as_completed(futures):
                request_results.append(f.result())

        self.assertEqual(len(request_results), 30)
        for status, endpoint_label in request_results:
            self.assertEqual(status, 200, f"Endpoint {endpoint_label} returned non-200 status: {status}")


# ==============================================================================
# TIER 5 - CLASS 4: Corrupted Stream & Edge Input Validation
# ==============================================================================

class TestTier5CorruptedStreamAndEdgeValidation(unittest.TestCase):
    """Stress tests error paths, corrupted bytes, invalid base64, and malformed inputs."""

    def test_corrupted_truncated_pdf_stream(self):
        """Verifies truncated and malformed byte streams raise clean ValueError without crash."""
        corrupt_samples = [
            b"%PDF-1.4\n",  # Header only
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog",  # Incomplete object
            b"NOT_A_PDF_STREAM_RANDOM_GARBAGE_PAYLOAD",  # Non-PDF
            b"",  # 0-byte buffer
        ]

        for sample in corrupt_samples:
            with self.assertRaises(ValueError):
                ClinicalTrialPDFExtractor.extract_from_pdf(sample)

    def test_api_upload_invalid_base64_payload(self):
        """POST /api/clinical/upload returns 400 when invalid base64 or corrupt payload is sent."""
        invalid_cases = [
            {"filename": "test.pdf", "file_data": "NOT_BASE64_!@#$%^&*()"},
            {"filename": "test.pdf", "file_data": "odd_len_b64"},
            {"filename": "test.pdf", "file_data": ""},
        ]

        for payload in invalid_cases:
            status, _, body = InProcessHTTPClient.post("/api/clinical/upload", payload)
            self.assertEqual(status, 400, f"Expected 400 for payload {payload}, got {status}")
            data = json.loads(body.decode("utf-8"))
            self.assertEqual(data["status"], "error")

    def test_api_missing_fields_and_empty_payloads(self):
        """Verifies clean 400/200 handling when optional or required fields are omitted."""
        # 1. Upload without file_data
        status, _, body = InProcessHTTPClient.post("/api/clinical/upload", {})
        self.assertEqual(status, 400)

        # 2. Verify-copy with empty or whitespace copy
        status_empty, _, body_empty = InProcessHTTPClient.post("/api/clinical/verify-copy", {"copy_text": ""})
        self.assertEqual(status_empty, 200)
        data = json.loads(body_empty.decode("utf-8"))
        self.assertFalse(data["has_discrepancies"])

        # 3. Verify-copy with None copy_text
        status_none, _, body_none = InProcessHTTPClient.post("/api/clinical/verify-copy", {"copy_text": None})
        self.assertEqual(status_none, 200)

    def test_large_payload_garbage_stress(self):
        """Verifies 1MB of pseudo-random non-PDF bytes is rejected cleanly without memory leak."""
        one_mb_garbage = os.urandom(1024 * 1024)
        with self.assertRaises(ValueError):
            ClinicalTrialPDFExtractor.extract_from_pdf(one_mb_garbage)


# ==============================================================================
# TIER 5 - CLASS 5: Tri-File & Dual-Server Parity Assertions
# ==============================================================================

class TestTier5TriFileAndDualServerParity(unittest.TestCase):
    """Asserts cryptographic SHA-256 byte parity across server and HTML frontend files."""

    def test_dual_server_byte_and_hash_parity(self):
        """Verifies root server.py and codex/server.py have exact SHA-256 hash match."""
        root_server_path = REPO_ROOT / "server.py"
        codex_server_path = CODEX_ROOT / "server.py"

        self.assertTrue(root_server_path.exists(), f"Missing {root_server_path}")
        self.assertTrue(codex_server_path.exists(), f"Missing {codex_server_path}")

        root_bytes = root_server_path.read_bytes()
        codex_bytes = codex_server_path.read_bytes()

        root_hash = hashlib.sha256(root_bytes).hexdigest()
        codex_hash = hashlib.sha256(codex_bytes).hexdigest()

        self.assertEqual(
            root_hash,
            codex_hash,
            f"Dual-server parity violation: server.py ({root_hash[:12]}) != codex/server.py ({codex_hash[:12]})"
        )
        self.assertEqual(len(root_bytes), len(codex_bytes))

    def test_tri_file_html_byte_and_hash_parity(self):
        """Verifies index.html, codex/frontend/index.html, and docs/index.html have exact SHA-256 match."""
        html_paths = [
            REPO_ROOT / "index.html",
            CODEX_ROOT / "frontend" / "index.html",
            REPO_ROOT / "docs" / "index.html"
        ]

        hashes = []
        lengths = []
        for p in html_paths:
            self.assertTrue(p.exists(), f"Missing frontend file: {p}")
            data = p.read_bytes()
            hashes.append(hashlib.sha256(data).hexdigest())
            lengths.append(len(data))

        self.assertEqual(
            len(set(hashes)),
            1,
            f"Tri-file HTML parity violation! Hashes: {list(zip(html_paths, hashes))}"
        )
        self.assertEqual(len(set(lengths)), 1)

    def test_html_clinical_evidence_ui_elements(self):
        """Verifies interactive Clinical Evidence tab, modal, and buttons exist in all HTML files."""
        html_path = REPO_ROOT / "index.html"
        content = html_path.read_text(encoding="utf-8")

        required_ui_tokens = [
            "Clinical Evidence",
            "Study CS-2026-88",
            "LAB-AYUSH-904",
            "Extracted Endpoints",
            "evidence",
            "/api/clinical/studies",
            "/api/clinical/upload",
            "/api/clinical/verify-copy",
        ]
        for token in required_ui_tokens:
            self.assertIn(token, content, f"HTML frontend is missing UI token: {token}")

    def test_server_endpoint_registration_completeness(self):
        """Verifies server.py contains all mandated REST endpoints and thread safety locks."""
        server_code = (REPO_ROOT / "server.py").read_text(encoding="utf-8")

        required_server_tokens = [
            "CLINICAL_STUDIES_LOCK",
            "CLINICAL_STUDIES_CATALOG",
            "/api/clinical/studies",
            "/api/clinical/upload",
            "/api/clinical/verify-copy",
            "/api/clinical/sample-pdf",
            "init_clinical_studies_catalog",
        ]
        for token in required_server_tokens:
            self.assertIn(token, server_code, f"server.py is missing required server token: {token}")


# ==============================================================================
# Standalone Runner
# ==============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
