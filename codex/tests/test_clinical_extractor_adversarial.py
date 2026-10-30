"""
Adversarial and Empirical Challenge Test Suite for ClinicalTrialPDFExtractor.

Milestone M1 Verification:
Tests dynamic multi-page PDF generation, dynamic table placement, custom endpoint values,
exact 1-indexed page citations, and edge case streams (empty, corrupted, encrypted).
"""

import io
import sys
import unittest
from pathlib import Path

# Setup sys.path for backend imports
BASE_DIR = Path(__file__).resolve().parent.parent  # codex/
BACKEND_DIR = BASE_DIR / "backend"
FIXTURES_DIR = BASE_DIR / "fixtures"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(FIXTURES_DIR) not in sys.path:
    sys.path.insert(0, str(FIXTURES_DIR))

import pypdf
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from app.core.clinical_extractor import ClinicalTrialPDFExtractor


def create_pdf_page_with_text(writer: pypdf.PdfWriter, lines: list[str], width: float = 612.0, height: float = 792.0):
    """Adds a page with specified text lines to a PdfWriter using standard PDF operators."""
    page = writer.add_blank_page(width=width, height=height)

    font_dict = DictionaryObject({
        NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type1'),
        NameObject('/BaseFont'): NameObject('/Helvetica'),
    })
    fonts = DictionaryObject({NameObject('/F1'): font_dict})
    resources = DictionaryObject({NameObject('/Font'): fonts})
    page[NameObject('/Resources')] = resources

    content_lines = [
        'BT',
        '/F1 10 Tf',
        '13.5 TL',
        '45 745 Td'
    ]
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
    return page


def build_dynamic_cs_pdf(
    total_pages: int,
    table_page: int,
    study_id: str = "CS-2026-DYNAMIC",
    hydration_val: float = 88.5,
    acne_val: float = 54.3,
    sebum_val: float = 38.1,
    tewl_val: float = 22.4,
    cohort_n: int = 150,
    duration_days: int = 21,
) -> bytes:
    """
    Builds a dynamic multi-page clinical trial PDF with Table 2.1 placed on `table_page`.
    Injected numeric values are custom and distinct from default constants.
    """
    writer = pypdf.PdfWriter()

    for p in range(1, total_pages + 1):
        if p == table_page:
            lines = [
                f"PROTOCOL IDENTIFIER: {study_id}",
                f"STUDY TITLE: Dynamic Clinical Trial {study_id}",
                "SECTION 6: STATISTICAL RESULTS & QUANTITATIVE CLINICAL ENDPOINTS",
                "Table 2.1: Quantitative Clinical Endpoints at Endpoint Visit",
                "=================================================================================",
                "Endpoint Parameter                  Baseline Mean       Endpoint Mean   Mean Delta (%)  p-value",
                "=================================================================================",
                f"Stratum Corneum Hydration (%)       30.0 (3.5)          56.5 (4.2)      +{hydration_val}%        p < 0.001",
                f"Inflammatory Acne Lesion Count      28.0 (4.1)          12.8 (2.5)      -{acne_val}%        p < 0.001",
                f"Casual Sebum Excretion (ug/cm2)     195.0 (20.0)        120.7 (15.2)    -{sebum_val}%        p < 0.001",
                f"Transepidermal Water Loss (TEWL)    20.0 (3.0)          15.5 (2.0)      -{tewl_val}%        p < 0.01",
                "=================================================================================",
                f"Canonical Citation: Clinical Study {study_id}, Page {table_page}, Table 2.1",
                f"Page {p} of {total_pages}"
            ]
        elif p == 1:
            lines = [
                "================================================================================",
                f"CLINICAL STUDY DOSSIER - PROTOCOL {study_id}",
                "================================================================================",
                f"PROTOCOL IDENTIFIER: {study_id}",
                "STUDY TITLE: Dynamic Randomized Clinical Trial",
                "SPONSOR: Dermacare Global Research",
                f"COHORT SIZE: N={cohort_n} enrolled subjects",
                f"STUDY DURATION: {duration_days} days",
                "TESTING METHODOLOGY: Double-blind, randomized, placebo-controlled clinical trial",
                "STATISTICAL SIGNIFICANCE: p < 0.001",
                f"Page 1 of {total_pages}"
            ]
        else:
            lines = [
                f"PROTOCOL {study_id} | INTERMEDIATE SECTION",
                f"--------------------------------------------------------------------------------",
                f"Section content for page {p}.",
                "Clinical monitoring and standard safety protocols.",
                f"Page {p} of {total_pages}"
            ]
        create_pdf_page_with_text(writer, lines)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def build_dynamic_ayush_pdf(
    total_pages: int,
    table_page: int,
    assay_id: str = "LAB-AYUSH-555",
    soothing_val: float = 78.9,
    irritation_val: float = 0.04,
    cohort_n: int = 95,
    duration_days: int = 10,
) -> bytes:
    """
    Builds a dynamic multi-page assay certificate PDF with Table 4.1 placed on `table_page`.
    """
    writer = pypdf.PdfWriter()

    for p in range(1, total_pages + 1):
        if p == table_page:
            lines = [
                f"CERTIFICATE / ASSAY ID: {assay_id}",
                f"REPORT TITLE: Bio-Assay Tolerance Evaluation {assay_id}",
                "SECTION 4: QUANTITATIVE DERMAL TOLERANCE & SOOTHING BIO-ASSAY RESULTS",
                "Table 4.1: Dermal Tolerance and Soothing Bio-Assay Results",
                "=================================================================================",
                "Assay Parameter                     Observed Value      Standard Threshold   Outcome / Status   p-value",
                "=================================================================================",
                f"Skin Irritation Index               {irritation_val}                < 0.10               Hypoallergenic     p < 0.01",
                f"Soothing Efficacy (% erythema red.) {soothing_val}%               >= 50.0%             Significant Relief p < 0.01",
                f"Duration of Evaluation              {duration_days} days              {duration_days} days               Protocol Satisfied p < 0.01",
                "=================================================================================",
                f"Canonical Citation: Ayush Bio-Analytical Assay {assay_id.replace('LAB-', '')}, Page {table_page}, Section 4",
                f"Page {p} of {total_pages}"
            ]
        elif p == 1:
            lines = [
                "================================================================================",
                f"AYUSH BIO-ANALYTICAL TESTING LABORATORIES - CERTIFICATE OF ANALYSIS",
                "================================================================================",
                f"CERTIFICATE / ASSAY ID: {assay_id}",
                "REPORT TITLE: Bio-Assay Tolerance Evaluation",
                "SPONSOR / APPLICANT: Brandwise Compliance Validation Group",
                f"COHORT SIZE: N={cohort_n} human subjects",
                f"STUDY DURATION: {duration_days} days",
                "TESTING METHODOLOGY: Standardized ISO 10993-10 dermatological patch evaluation",
                f"Page 1 of {total_pages}"
            ]
        else:
            lines = [
                f"{assay_id} | INTERMEDIATE ASSAY DATA",
                f"--------------------------------------------------------------------------------",
                f"Analytical procedures on page {p}.",
                f"Page {p} of {total_pages}"
            ]
        create_pdf_page_with_text(writer, lines)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class TestClinicalExtractorAdversarial(unittest.TestCase):
    """Adversarial stress-testing of ClinicalTrialPDFExtractor."""

    # ==========================================================================
    # CHALLENGE TASK 1 & 2: Dynamic Multi-Page PDFs & Accurate Dynamic Extraction
    # ==========================================================================

    def test_dynamic_pdf_5_pages_table_on_page_3(self):
        """Dynamic 5-page PDF with Table 2.1 on Page 3 and custom numeric endpoints."""
        pdf_bytes = build_dynamic_cs_pdf(
            total_pages=5,
            table_page=3,
            study_id="CS-DYNAMIC-5P",
            hydration_val=77.3,
            acne_val=51.8,
            sebum_val=33.4,
            tewl_val=19.2,
            cohort_n=140,
            duration_days=21
        )
        res = ClinicalTrialPDFExtractor.extract_from_pdf(pdf_bytes)

        # 1. Total page count
        self.assertEqual(res["total_pages"], 5, "Total pages should be exactly 5")
        self.assertEqual(res["study_id"], "CS-DYNAMIC-5P")
        self.assertEqual(res["cohort_size"], 140)
        self.assertEqual(res["duration_days"], 21)

        # 2. Table location
        self.assertEqual(len(res["tables"]), 1)
        self.assertEqual(res["tables"][0]["page"], 3, "Table 2.1 must be detected on Page 3")
        self.assertEqual(res["tables"][0]["table_id"], "Table 2.1")

        # 3. Dynamic endpoint values (MUST NOT default to 94.2, 68.0, 42.5)
        endpoints = res["endpoints"]
        self.assertEqual(endpoints["hydration_increase_percent"]["value"], 77.3)
        self.assertEqual(endpoints["acne_lesion_reduction_percent"]["value"], 51.8)
        self.assertEqual(endpoints["sebum_reduction_percent"]["value"], 33.4)
        self.assertEqual(endpoints["tewl_reduction_percent"]["value"], 19.2)

        # 4. Exact 1-indexed page in endpoint citation
        expected_citation = "Clinical Study CS-DYNAMIC-5P, Page 3, Table 2.1"
        self.assertEqual(endpoints["hydration_increase_percent"]["page"], 3)
        self.assertEqual(endpoints["hydration_increase_percent"]["citation"], expected_citation)
        self.assertEqual(endpoints["acne_lesion_reduction_percent"]["citation"], expected_citation)
        self.assertEqual(res["source_citation"], expected_citation)

    def test_dynamic_pdf_10_pages_table_on_page_9(self):
        """Dynamic 10-page PDF with Table 4.1 on Page 9 and custom assay values."""
        pdf_bytes = build_dynamic_ayush_pdf(
            total_pages=10,
            table_page=9,
            assay_id="LAB-AYUSH-999",
            soothing_val=72.4,
            irritation_val=0.03,
            cohort_n=90,
            duration_days=10
        )
        res = ClinicalTrialPDFExtractor.extract_from_pdf(pdf_bytes)

        # 1. Total page count
        self.assertEqual(res["total_pages"], 10, "Total pages should be exactly 10")
        self.assertEqual(res["study_id"], "LAB-AYUSH-999")
        self.assertEqual(res["cohort_size"], 90)

        # 2. Table location
        self.assertEqual(len(res["tables"]), 1)
        self.assertEqual(res["tables"][0]["page"], 9, "Table 4.1 must be detected on Page 9")

        # 3. Dynamic endpoint values (MUST NOT default to 89.4 or 0.02)
        endpoints = res["endpoints"]
        self.assertEqual(endpoints["soothing_efficacy_percent"]["value"], 72.4)
        self.assertEqual(endpoints["skin_irritation_index"]["value"], 0.03)

        # 4. Exact 1-indexed page in citation
        expected_citation = "Ayush Bio-Analytical Assay AYUSH-999, Page 9, Section 4"
        self.assertEqual(endpoints["soothing_efficacy_percent"]["page"], 9)
        self.assertEqual(endpoints["soothing_efficacy_percent"]["citation"], expected_citation)
        self.assertEqual(res["source_citation"], expected_citation)

    def test_dynamic_pdf_15_pages_table_on_page_12(self):
        """Dynamic 15-page PDF with Table 2.1 on Page 12 and custom endpoint values."""
        pdf_bytes = build_dynamic_cs_pdf(
            total_pages=15,
            table_page=12,
            study_id="CS-2026-LONG15",
            hydration_val=98.6,
            acne_val=71.2,
            sebum_val=46.8,
            tewl_val=35.0,
            cohort_n=200,
            duration_days=28
        )
        res = ClinicalTrialPDFExtractor.extract_from_pdf(pdf_bytes)

        # 1. Total page count
        self.assertEqual(res["total_pages"], 15, "Total pages should be exactly 15")
        self.assertEqual(res["study_id"], "CS-2026-LONG15")

        # 2. Table location
        self.assertEqual(res["tables"][0]["page"], 12, "Table 2.1 must be detected on Page 12")

        # 3. Dynamic endpoint values
        endpoints = res["endpoints"]
        self.assertEqual(endpoints["hydration_increase_percent"]["value"], 98.6)
        self.assertEqual(endpoints["acne_lesion_reduction_percent"]["value"], 71.2)
        self.assertEqual(endpoints["sebum_reduction_percent"]["value"], 46.8)
        self.assertEqual(endpoints["tewl_reduction_percent"]["value"], 35.0)

        # 4. Exact canonical citation reflecting Page 12
        expected_citation = "Clinical Study CS-2026-LONG15, Page 12, Table 2.1"
        self.assertEqual(endpoints["hydration_increase_percent"]["page"], 12)
        self.assertEqual(endpoints["hydration_increase_percent"]["citation"], expected_citation)
        self.assertEqual(res["source_citation"], expected_citation)

    def test_dynamic_pdf_table_on_page_1_boundary(self):
        """Boundary: Table 2.1 placed immediately on Page 1 of a 3-page document."""
        pdf_bytes = build_dynamic_cs_pdf(
            total_pages=3,
            table_page=1,
            study_id="CS-PAGE1-TABLE",
            hydration_val=81.0,
            acne_val=50.0,
            sebum_val=30.0,
            tewl_val=15.0
        )
        res = ClinicalTrialPDFExtractor.extract_from_pdf(pdf_bytes)
        self.assertEqual(res["total_pages"], 3)
        self.assertEqual(res["tables"][0]["page"], 1)
        self.assertEqual(res["endpoints"]["hydration_increase_percent"]["page"], 1)
        self.assertEqual(res["endpoints"]["hydration_increase_percent"]["value"], 81.0)
        self.assertEqual(res["endpoints"]["hydration_increase_percent"]["citation"], "Clinical Study CS-PAGE1-TABLE, Page 1, Table 2.1")

    def test_dynamic_pdf_table_on_last_page(self):
        """Boundary: Table 2.1 placed on the very last page of a 20-page document."""
        pdf_bytes = build_dynamic_cs_pdf(
            total_pages=20,
            table_page=20,
            study_id="CS-PAGE20-LAST",
            hydration_val=91.5
        )
        res = ClinicalTrialPDFExtractor.extract_from_pdf(pdf_bytes)
        self.assertEqual(res["total_pages"], 20)
        self.assertEqual(res["tables"][0]["page"], 20)
        self.assertEqual(res["endpoints"]["hydration_increase_percent"]["page"], 20)
        self.assertEqual(res["endpoints"]["hydration_increase_percent"]["value"], 91.5)
        self.assertEqual(res["endpoints"]["hydration_increase_percent"]["citation"], "Clinical Study CS-PAGE20-LAST, Page 20, Table 2.1")

    # ==========================================================================
    # CHALLENGE TASK 3: Edge Case PDF Streams
    # ==========================================================================

    def test_edge_case_empty_buffer_bytes(self):
        """0-byte buffer: Must raise clean ValueError."""
        with self.assertRaises(ValueError) as ctx:
            ClinicalTrialPDFExtractor.extract_from_pdf(b"")
        self.assertIn("0-byte", str(ctx.exception))

    def test_edge_case_empty_bytearray(self):
        """0-byte bytearray: Must raise clean ValueError."""
        with self.assertRaises(ValueError) as ctx:
            ClinicalTrialPDFExtractor.extract_from_pdf(bytearray())
        self.assertIn("0-byte", str(ctx.exception))

    def test_edge_case_empty_bytesio_stream(self):
        """0-byte BytesIO stream: Must raise clean ValueError."""
        with self.assertRaises(ValueError) as ctx:
            ClinicalTrialPDFExtractor.extract_from_pdf(io.BytesIO(b""))
        self.assertIn("0-byte", str(ctx.exception))

    def test_edge_case_empty_file_on_disk(self, tmp_path=None):
        """0-byte physical file on disk: Must raise clean ValueError."""
        temp_file = BASE_DIR / "tests" / "_temp_empty_0byte.pdf"
        try:
            temp_file.write_bytes(b"")
            with self.assertRaises(ValueError) as ctx:
                ClinicalTrialPDFExtractor.extract_from_pdf(temp_file)
            self.assertIn("0-byte", str(ctx.exception))
        finally:
            if temp_file.exists():
                temp_file.unlink()

    def test_edge_case_corrupted_header_stream(self):
        """Corrupted PDF header stream (no %PDF): Must raise clean ValueError."""
        bad_header = b"NOT_A_PDF_STREAM_MALFORMED_HEADER\x00\x01\x02\x03"
        with self.assertRaises(ValueError) as ctx:
            ClinicalTrialPDFExtractor.extract_from_pdf(bad_header)
        self.assertIn("Corrupted or invalid PDF payload", str(ctx.exception))

    def test_edge_case_truncated_pdf_stream(self):
        """Valid header but truncated / incomplete stream: Must raise clean ValueError."""
        truncated = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
        with self.assertRaises(ValueError) as ctx:
            ClinicalTrialPDFExtractor.extract_from_pdf(truncated)
        self.assertIn("Corrupted or invalid PDF payload", str(ctx.exception))

    def test_edge_case_password_protected_pdf(self):
        """Password protected encrypted PDF: Must return ERROR_ENCRYPTED status without crash."""
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.encrypt("topsecret123")
        buf = io.BytesIO()
        writer.write(buf)

        res = ClinicalTrialPDFExtractor.extract_from_pdf(buf.getvalue())
        self.assertEqual(res["status"], "ERROR_ENCRYPTED")
        self.assertEqual(res["total_pages"], 0)
        self.assertIn("encrypted", res["error"].lower())

    def test_edge_case_none_source(self):
        """None passed as source: Must raise clean ValueError."""
        with self.assertRaises(ValueError):
            ClinicalTrialPDFExtractor.extract_from_pdf(None)

    def test_edge_case_nonexistent_file(self):
        """Non-existent file path: Must raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            ClinicalTrialPDFExtractor.extract_from_pdf("non_existent_file_path_12345.pdf")

    def test_edge_case_unsupported_type(self):
        """Unsupported object type: Must raise TypeError."""
        with self.assertRaises(TypeError):
            ClinicalTrialPDFExtractor.extract_from_pdf(12345)

    def test_prose_fallback_extraction_when_no_tables(self):
        """Adversarial: PDF with NO efficacy table, but quantitative endpoints in prose on Page 4."""
        writer = pypdf.PdfWriter()
        for p in range(1, 6):
            if p == 1:
                lines = [
                    "CLINICAL DOSSIER - PROTOCOL CS-PROSE-99",
                    "PROTOCOL IDENTIFIER: CS-PROSE-99",
                    "STUDY TITLE: Narrative Clinical Evaluation Without Structured Tables",
                    "Page 1 of 5"
                ]
            elif p == 4:
                lines = [
                    "SECTION 6: NARRATIVE EFFICACY DISCUSSION",
                    "After completing the trial, subjects demonstrated an impressive",
                    "82.5% hydration increase compared to baseline measurements.",
                    "Furthermore, a 58.4% acne lesion reduction was noted across cohorts.",
                    "Page 4 of 5"
                ]
            else:
                lines = [f"Background discussion on page {p}.", f"Page {p} of 5"]
            create_pdf_page_with_text(writer, lines)

        buf = io.BytesIO()
        writer.write(buf)
        res = ClinicalTrialPDFExtractor.extract_from_pdf(buf.getvalue())

        self.assertEqual(res["total_pages"], 5)
        self.assertEqual(res["study_id"], "CS-PROSE-99")
        # Endpoints should be captured from prose
        endpoints = res["endpoints"]
        self.assertIn("hydration_increase_percent", endpoints)
        self.assertEqual(endpoints["hydration_increase_percent"]["value"], 82.5)
        self.assertEqual(endpoints["hydration_increase_percent"]["page"], 4)
        self.assertEqual(endpoints["hydration_increase_percent"]["table"], "Prose Summary")
        self.assertEqual(endpoints["hydration_increase_percent"]["citation"], "Clinical Study CS-PROSE-99, Page 4, Section 6")

        self.assertIn("acne_lesion_reduction_percent", endpoints)
        self.assertEqual(endpoints["acne_lesion_reduction_percent"]["value"], 58.4)
        self.assertEqual(endpoints["acne_lesion_reduction_percent"]["page"], 4)

    def test_multi_table_cataloging_across_pages(self):
        """Adversarial: Document with multiple tables on different pages (Table 1.1 on P2, Table 2.1 on P5, Table 3.1 on P8)."""
        writer = pypdf.PdfWriter()
        for p in range(1, 10):
            if p == 1:
                lines = ["PROTOCOL CS-MULTI-TBL", "PROTOCOL IDENTIFIER: CS-MULTI-TBL", "Page 1 of 9"]
            elif p == 2:
                lines = [
                    "Table 1.1: Baseline Subject Demographics",
                    "Age Distribution and Gender Balance",
                    "Page 2 of 9"
                ]
            elif p == 5:
                lines = [
                    "Table 2.1: Quantitative Clinical Endpoints at Endpoint Visit",
                    "Endpoint Parameter                  Baseline Mean       Endpoint Mean   Mean Delta (%)  p-value",
                    "Stratum Corneum Hydration (%)       30.0 (3.5)          57.0 (4.2)      +90.0%          p < 0.001",
                    "Inflammatory Acne Lesion Count      28.0 (4.1)          10.0 (2.5)      -64.2%          p < 0.001",
                    "Casual Sebum Excretion (ug/cm2)     195.0 (20.0)        117.0 (15.2)    -40.0%          p < 0.001",
                    "Transepidermal Water Loss (TEWL)    20.0 (3.0)          14.0 (2.0)      -30.0%          p < 0.01",
                    "Page 5 of 9"
                ]
            elif p == 8:
                lines = [
                    "Table 3.1: Adverse Event Summary",
                    "Zero Serious Adverse Events Reported",
                    "Page 8 of 9"
                ]
            else:
                lines = [f"Interim prose on page {p}.", f"Page {p} of 9"]
            create_pdf_page_with_text(writer, lines)

        buf = io.BytesIO()
        writer.write(buf)
        res = ClinicalTrialPDFExtractor.extract_from_pdf(buf.getvalue())

        self.assertEqual(res["total_pages"], 9)
        table_ids = [t["table_id"] for t in res["tables"]]
        self.assertIn("Table 1.1", table_ids)
        self.assertIn("Table 2.1", table_ids)
        self.assertIn("Table 3.1", table_ids)

        t11 = next(t for t in res["tables"] if t["table_id"] == "Table 1.1")
        t21 = next(t for t in res["tables"] if t["table_id"] == "Table 2.1")
        t31 = next(t for t in res["tables"] if t["table_id"] == "Table 3.1")

        self.assertEqual(t11["page"], 2)
        self.assertEqual(t21["page"], 5)
        self.assertEqual(t31["page"], 8)
        self.assertEqual(res["endpoints"]["hydration_increase_percent"]["page"], 5)
        self.assertEqual(res["endpoints"]["hydration_increase_percent"]["citation"], "Clinical Study CS-MULTI-TBL, Page 5, Table 2.1")

    def test_file_input_signatures_parity(self):
        """Verifies parity across str path, Path object, bytes, and BytesIO stream."""
        pdf_bytes = build_dynamic_cs_pdf(total_pages=4, table_page=2, study_id="CS-PARITY-TEST", hydration_val=84.6)
        temp_file = BASE_DIR / "tests" / "_temp_parity_test.pdf"
        try:
            temp_file.write_bytes(pdf_bytes)

            from app.core.clinical_extractor import extract_clinical_trial_pdf
            res_path_obj = extract_clinical_trial_pdf(temp_file)
            res_str_path = extract_clinical_trial_pdf(str(temp_file))
            res_bytes = extract_clinical_trial_pdf(pdf_bytes)
            res_stream = extract_clinical_trial_pdf(io.BytesIO(pdf_bytes))

            self.assertEqual(res_path_obj["study_id"], "CS-PARITY-TEST")
            self.assertEqual(res_str_path["study_id"], "CS-PARITY-TEST")
            self.assertEqual(res_bytes["study_id"], "CS-PARITY-TEST")
            self.assertEqual(res_stream["study_id"], "CS-PARITY-TEST")

            self.assertEqual(res_path_obj["endpoints"]["hydration_increase_percent"]["value"], 84.6)
            self.assertEqual(res_str_path["endpoints"]["hydration_increase_percent"]["value"], 84.6)
            self.assertEqual(res_bytes["endpoints"]["hydration_increase_percent"]["value"], 84.6)
            self.assertEqual(res_stream["endpoints"]["hydration_increase_percent"]["value"], 84.6)
        finally:
            if temp_file.exists():
                temp_file.unlink()


if __name__ == "__main__":
    unittest.main()

