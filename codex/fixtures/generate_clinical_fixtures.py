"""
Synthetic Clinical Trial PDF Fixture Generator for Brandwise.

Generates offline, deterministic multi-page clinical trial PDFs and lab assay certificates
using Python's standard pypdf library without external cloud dependencies.

Fixtures generated:
1. Study_CS-2026-88.pdf: 8 pages, Protocol CS-2026-88, N=120 cohort, 14-day duration,
   Table 2.1 on Page 7 with 94.2% hydration increase, 68.0% acne lesion reduction,
   42.5% sebum reduction, p < 0.001.
2. LAB-AYUSH-904.pdf: 4 pages, Assay LAB-AYUSH-904, N=85 cohort, 7-day duration,
   Table 4.1 on Page 3 with 89.4% soothing efficacy, skin irritation index 0.02, p < 0.01.
"""

import io
import os
import sys
from pathlib import Path
import pypdf
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def _create_page_with_text(writer: pypdf.PdfWriter, lines: list[str], width: float = 612.0, height: float = 792.0):
    """Adds a page with specified text lines to a PdfWriter using standard PDF operators."""
    page = writer.add_blank_page(width=width, height=height)

    # Standard Type 1 font (Helvetica)
    font_dict = DictionaryObject({
        NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type1'),
        NameObject('/BaseFont'): NameObject('/Helvetica'),
    })
    fonts = DictionaryObject({NameObject('/F1'): font_dict})
    resources = DictionaryObject({NameObject('/Font'): fonts})
    page[NameObject('/Resources')] = resources

    # Layout text stream with font size 10 and 13.5pt leading
    content_lines = [
        'BT',
        '/F1 10 Tf',
        '13.5 TL',
        '45 745 Td'
    ]
    first = True
    for line in lines:
        # Escape parenthesis and backslashes per PDF specification
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


def generate_study_cs_2026_88(output_path: str | Path | None = None) -> bytes:
    """
    Generates an 8-page clinical study PDF dossier for Protocol CS-2026-88.
    Table 2.1 is positioned on Page 7 with quantitative endpoints.
    """
    writer = pypdf.PdfWriter()

    # --- Page 1: Cover & Protocol Identification ---
    p1_lines = [
        "================================================================================",
        "DERMACARE CLINICAL RESEARCH LABORATORIES - CLINICAL STUDY DOSSIER",
        "================================================================================",
        "",
        "PROTOCOL IDENTIFIER: CS-2026-88",
        "STUDY TITLE: 14-Day Stratum Corneum Hydration & Sebum Control Trial",
        "INVESTIGATIONAL PRODUCT: Brandwise Advanced Hydrating & Sebum Balance Serum (Formula B-88)",
        "SPONSOR: Dermacare Clinical Research Laboratories Inc., Global Dermatology Division",
        "PRINCIPAL INVESTIGATOR: Dr. Arvind Swamy, MD, DNB (Dermatology)",
        "CO-INVESTIGATORS: Dr. Maya Sengupta, PhD; Dr. Robert Vance, MD",
        "DOCUMENT TYPE: Final Clinical Study Report (CSR) - Regulatory Dossier",
        "STUDY PHASE: Phase II/III Randomized Efficacy Evaluation",
        "DATE OF ISSUE: February 15, 2026",
        "ETHICAL COMMITTEE APPROVAL: IEC/DCL/2026/014-A",
        "GCP COMPLIANCE: Conducted under ICH-GCP Consolidated Guidelines (E6 R2)",
        "CONFIDENTIALITY: Strictly Confidential - Proprietary Clinical Evidence",
        "",
        "--------------------------------------------------------------------------------",
        "CANONICAL CITATION FORMAT: Clinical Study CS-2026-88, Page 7, Table 2.1",
        "--------------------------------------------------------------------------------",
        "",
        "Page 1 of 8"
    ]
    _create_page_with_text(writer, p1_lines)

    # --- Page 2: Executive Summary & Clinical Objectives ---
    p2_lines = [
        "PROTOCOL CS-2026-88 | CLINICAL STUDY REPORT",
        "--------------------------------------------------------------------------------",
        "SECTION 1: EXECUTIVE SUMMARY & OBJECTIVES",
        "--------------------------------------------------------------------------------",
        "",
        "1.1 Study Background & Rationale",
        "Impaired stratum corneum barrier function and dysregulated sebum excretion are cardinal",
        "pathophysiological hallmarks of mild-to-moderate acne vulgaris and dehydrated facial skin.",
        "Formula B-88 is an advanced topical formulation containing biomimetic ceramides,",
        "hyaluronic acid multi-molecular complex, and 2% zinc PCA.",
        "",
        "1.2 Primary Efficacy Objectives",
        "1. To evaluate quantitative change in stratum corneum hydration over a 14-day duration.",
        "2. To measure reduction in facial sebum excretion rate (ug/cm2) on the forehead and T-zone.",
        "3. To determine reduction in inflammatory and non-inflammatory acne lesion counts.",
        "",
        "1.3 Secondary Safety Objectives",
        "1. To determine cutaneous tolerance, erythema index, and adverse reaction profile.",
        "2. To verify transepidermal water loss (TEWL) reduction as a barrier integrity surrogate.",
        "",
        "Page 2 of 8"
    ]
    _create_page_with_text(writer, p2_lines)

    # --- Page 3: Study Design & Methodology ---
    p3_lines = [
        "PROTOCOL CS-2026-88 | CLINICAL STUDY REPORT",
        "--------------------------------------------------------------------------------",
        "SECTION 2: STUDY DESIGN & METHODOLOGY",
        "--------------------------------------------------------------------------------",
        "",
        "2.1 Study Methodology",
        "Double-blind, randomized, placebo-controlled clinical trial with parallel-group design.",
        "Eligible subjects were randomly allocated (1:1) to twice-daily topical application of",
        "Formula B-88 active serum or vehicle placebo for an uninterrupted 14-day study period.",
        "",
        "2.2 Blinding & Randomization",
        "Both active serum and vehicle control were packaged in identical opaque airless dispensers",
        "bearing unique randomization codes generated via permuted block algorithm (block size of 4).",
        "Both study participants and investigative dermatologists remained blinded throughout.",
        "",
        "2.3 Inclusion & Exclusion Criteria",
        "- Healthy male and female subjects aged 18 to 55 years.",
        "- Presence of mild-to-moderate facial dehydration (Corneometer baseline < 40 a.u.).",
        "- Baseline casual sebum level >= 150 ug/cm2 (Sebumeter SM 815).",
        "- Minimum of 15 facial inflammatory/comedonal acne lesions at screening.",
        "- Exclusion: Concomitant topical/systemic retinoids or corticosteroids within 30 days.",
        "",
        "Page 3 of 8"
    ]
    _create_page_with_text(writer, p3_lines)

    # --- Page 4: Subject Cohort & Demographics ---
    p4_lines = [
        "PROTOCOL CS-2026-88 | CLINICAL STUDY REPORT",
        "--------------------------------------------------------------------------------",
        "SECTION 3: SUBJECT COHORT & DEMOGRAPHICS",
        "--------------------------------------------------------------------------------",
        "",
        "3.1 Enrolled Cohort Population",
        "A total cohort of N=120 subjects were enrolled, consented, and randomized:",
        "- Active Treatment Group (Formula B-88): n = 60 subjects",
        "- Vehicle Placebo Group: n = 60 subjects",
        "",
        "3.2 Protocol Adherence & Analysis Populations",
        "- Enrolled Population (ITT): N=120 subjects",
        "- Per-Protocol (PP) Population: N=118 subjects (98.3% protocol compliance)",
        "- Dropouts / Discontinuations: 2 subjects (1 relocation, 1 unrelated personal illness)",
        "",
        "3.3 Baseline Demographic Distribution",
        "- Gender Distribution: 65 Female (54.2%), 55 Male (45.8%)",
        "- Age Range: 18 - 54 years (Mean: 29.4 +/- 6.8 years)",
        "- Fitzpatrick Skin Phototypes: Types III (38%), IV (42%), V (20%)",
        "- Baseline Stratum Corneum Hydration: Active 31.4 +/- 4.2 | Placebo 31.8 +/- 4.0 a.u.",
        "- Baseline Casual Sebum Excretion: Active 188.2 +/- 22.5 | Placebo 186.4 +/- 21.0 ug/cm2",
        "- Baseline Inflammatory Acne Count: Active 25.0 +/- 3.8 | Placebo 24.6 +/- 3.5 lesions",
        "",
        "Page 4 of 8"
    ]
    _create_page_with_text(writer, p4_lines)

    # --- Page 5: Study Duration & Timeline Protocol ---
    p5_lines = [
        "PROTOCOL CS-2026-88 | CLINICAL STUDY REPORT",
        "--------------------------------------------------------------------------------",
        "SECTION 4: TIMELINE & EVALUATION SCHEDULE",
        "--------------------------------------------------------------------------------",
        "",
        "4.1 Duration of Clinical Study",
        "The mandated clinical trial duration was exactly 14 days (Day 0 baseline to Day 14 final).",
        "Claims promising clinical significance before the 14-day protocol completion are unsubstantiated.",
        "",
        "4.2 Visit Schedule & Milestones",
        "- Visit 1 (Day 0 - Baseline): Comprehensive biophysical measurements and product dispensing.",
        "- Visit 2 (Day 3 - Interim): Early tolerance and compliance check (non-significant endpoint).",
        "- Visit 3 (Day 7 - Midpoint): Interim barrier function and sebum assessment.",
        "- Visit 4 (Day 14 - Study Endpoint): Final primary endpoint assessment and lesion counts.",
        "",
        "4.3 Product Application Protocol",
        "Subjects applied 3 to 4 drops of test formulation to the entire facial area twice daily",
        "(morning and evening) immediately after washing with a neutral cleansing syndet.",
        "",
        "Page 5 of 8"
    ]
    _create_page_with_text(writer, p5_lines)

    # --- Page 6: Bio-Analytical Instrumentation ---
    p6_lines = [
        "PROTOCOL CS-2026-88 | CLINICAL STUDY REPORT",
        "--------------------------------------------------------------------------------",
        "SECTION 5: INSTRUMENTATION & STATISTICAL METHODOLOGY",
        "--------------------------------------------------------------------------------",
        "",
        "5.1 Non-Invasive Cutaneous Bio-Engineering Probes",
        "- Corneometer CM 825 (Courage + Khazaka electronic GmbH, Cologne, Germany):",
        "  Capacitance measurement of the dielectric constant of stratum corneum.",
        "- Sebumeter SM 815 (Courage + Khazaka electronic GmbH):",
        "  Photometric grease-spot measurement of casual sebum excretion.",
        "- Tewameter TM 300: Transepidermal water loss (TEWL) open chamber method.",
        "- Global Acne Grading System (GAGS) and High-Resolution Digital Dermatological Imaging.",
        "",
        "5.2 Statistical Analysis Plan",
        "- Continuous variables are expressed as Mean +/- Standard Deviation (SD).",
        "- Within-group differences from baseline were analyzed using Paired Student t-test.",
        "- Between-group comparisons were evaluated using Two-Way Repeated Measures ANOVA.",
        "- Statistical significance threshold: alpha = 0.05. High significance: p < 0.001.",
        "",
        "Page 6 of 8"
    ]
    _create_page_with_text(writer, p6_lines)

    # --- Page 7: Primary Efficacy Results & Quantitative Tables (CORE PAGE) ---
    p7_lines = [
        "PROTOCOL CS-2026-88 | CLINICAL STUDY REPORT",
        "--------------------------------------------------------------------------------",
        "SECTION 6: STATISTICAL RESULTS & QUANTITATIVE CLINICAL ENDPOINTS",
        "--------------------------------------------------------------------------------",
        "",
        "Table 2.1: Quantitative Clinical Endpoints at Day 14",
        "=================================================================================================",
        "Endpoint Parameter                  Baseline Mean (SD)  Day 14 Mean (SD)  Mean Delta (%)   p-value",
        "=================================================================================================",
        "Stratum Corneum Hydration (%)       31.4 (4.2)          61.0 (5.1)        +94.2%           p < 0.001",
        "Inflammatory Acne Lesion Count      25.0 (3.8)          8.0 (2.1)         -68.0%           p < 0.001",
        "Casual Sebum Excretion (ug/cm2)     188.2 (22.5)        108.2 (16.4)      -42.5%           p < 0.001",
        "Transepidermal Water Loss (TEWL)    18.5 (2.9)          12.6 (2.2)        -31.9%           p < 0.01",
        "=================================================================================================",
        "",
        "Statistical Summary Narrative:",
        "At Day 14, subjects treated with Formula B-88 demonstrated a statistically significant",
        "94.2% hydration increase (p < 0.001), 68.0% acne lesion reduction (p < 0.001), and",
        "42.5% sebum reduction (p < 0.001) compared to baseline values across the N=120 cohort.",
        "",
        "Regulatory Citation Reference:",
        "All advertising claims citing this trial must reference: Clinical Study CS-2026-88, Page 7, Table 2.1.",
        "Over-claims exceeding 94.2% hydration increase or promising results in less than 14 days",
        "are scientifically invalid and breach advertising substantiation standards.",
        "",
        "Page 7 of 8"
    ]
    _create_page_with_text(writer, p7_lines)

    # --- Page 8: Safety Profile, Conclusion & Certification ---
    p8_lines = [
        "PROTOCOL CS-2026-88 | CLINICAL STUDY REPORT",
        "--------------------------------------------------------------------------------",
        "SECTION 7: SAFETY, TOLERANCE & INVESTIGATOR CERTIFICATION",
        "--------------------------------------------------------------------------------",
        "",
        "7.1 Adverse Events & Cutaneous Tolerance",
        "- Serious Adverse Events (SAE): 0 reported throughout the 14-day study.",
        "- Cutaneous Irritation Index: 0.00 (Classified as non-irritating, hypoallergenic).",
        "- Tolerability: Rated 'Excellent' or 'Good' by 97.5% of active cohort participants.",
        "",
        "7.2 Investigator Clinical Conclusion",
        "Formula B-88 achieved its designated primary efficacy endpoints at Day 14 with robust",
        "statistical significance (p < 0.001). Observed efficacy: 94.2% hydration increase,",
        "68.0% acne lesion reduction, and 42.5% sebum reduction.",
        "",
        "7.3 Sign-Off & Regulatory Seal",
        "Principal Investigator: Dr. Arvind Swamy, MD, DNB (Dermatology)",
        "Signature: [Electronically Validated & Sealed on 2026-02-15]",
        "Institutional Seal: Dermacare Clinical Research Laboratories, Mumbai & London",
        "Canonical Citation: Clinical Study CS-2026-88, Page 7, Table 2.1",
        "",
        "Page 8 of 8"
    ]
    _create_page_with_text(writer, p8_lines)

    # Set PDF Metadata
    writer.add_metadata({
        "/Title": "14-Day Stratum Corneum Hydration & Sebum Control Trial",
        "/Subject": "Clinical Trial Efficacy Report CS-2026-88",
        "/Author": "Dermacare Clinical Research Laboratories Inc.",
        "/Producer": "Brandwise Synthetic Fixture Generator",
        "/Keywords": "CS-2026-88, hydration, sebum, acne, clinical trial"
    })

    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pdf_bytes)

    return pdf_bytes


def generate_lab_ayush_904(output_path: str | Path | None = None) -> bytes:
    """
    Generates a 4-page laboratory assay certificate PDF for Protocol LAB-AYUSH-904.
    Table 4.1 is positioned on Page 3 with soothing efficacy and skin irritation index.
    """
    writer = pypdf.PdfWriter()

    # --- Page 1: Certificate of Analysis Header ---
    p1_lines = [
        "================================================================================",
        "AYUSH BIO-ANALYTICAL TESTING LABORATORIES - CERTIFICATE OF ANALYSIS",
        "================================================================================",
        "",
        "CERTIFICATE / ASSAY ID: LAB-AYUSH-904",
        "REPORT TITLE: Independent Dermatological Patch Test & Efficacy Certificate",
        "TEST FACILITY: Ayush Central Bio-Analytical Testing Laboratory, New Delhi",
        "SPONSOR / APPLICANT: Brandwise Compliance Validation Group",
        "TEST PRODUCT: Botanical Calming & Soothing Complex",
        "COHORT SIZE: N=85 human subjects",
        "TESTING METHODOLOGY: Standardized ISO 10993-10 dermatological patch evaluation",
        "STUDY DURATION: 7 days",
        "DATE OF COMPLETION: January 20, 2026",
        "ISO ACCREDITATION: NABL ISO/IEC 17025:2017 Certified (TC-8821)",
        "",
        "CANONICAL CITATION: Ayush Bio-Analytical Assay LAB-904, Page 3, Section 4",
        "",
        "Page 1 of 4"
    ]
    _create_page_with_text(writer, p1_lines)

    # --- Page 2: Test Methodology & Protocol ---
    p2_lines = [
        "LAB-AYUSH-904 | DERMATOLOGICAL ASSAY CERTIFICATE",
        "--------------------------------------------------------------------------------",
        "SECTION 2: ASSAY METHODOLOGY & STUDY POPULATION",
        "--------------------------------------------------------------------------------",
        "",
        "2.1 Study Methodology",
        "Standardized ISO 10993-10 dermatological patch evaluation with repeat insult occlusive",
        "patch application on healthy human subjects (N=85).",
        "",
        "2.2 Test Procedure",
        "- Occlusive Finn Chambers applied to infrascapular dorsal skin for 48 hours.",
        "- Evaluation of erythema and edema at 30 minutes, 24 hours, and 48 hours post-removal.",
        "- Extended 7-day topical soothing bio-assay on SLS-induced irritated skin sites.",
        "",
        "Page 2 of 4"
    ]
    _create_page_with_text(writer, p2_lines)

    # --- Page 3: Quantitative Findings & Table (Section 4) ---
    p3_lines = [
        "LAB-AYUSH-904 | DERMATOLOGICAL ASSAY CERTIFICATE",
        "--------------------------------------------------------------------------------",
        "SECTION 4: QUANTITATIVE DERMAL TOLERANCE & SOOTHING BIO-ASSAY RESULTS",
        "--------------------------------------------------------------------------------",
        "",
        "Table 4.1: Dermal Tolerance and Soothing Bio-Assay Results at Day 7",
        "=================================================================================================",
        "Assay Parameter                     Observed Value      Standard Threshold   Outcome / Status     p-value",
        "=================================================================================================",
        "Skin Irritation Index               0.02                < 0.10               Hypoallergenic       p < 0.01",
        "Soothing Efficacy (% erythema red.) 89.4%               >= 50.0%             Significant Relief   p < 0.01",
        "Duration of Evaluation              7 days              7 days               Protocol Satisfied   p < 0.01",
        "=================================================================================================",
        "",
        "Quantitative Assay Findings:",
        "Across the N=85 subject cohort evaluated over 7 days, the product achieved an 89.4% soothing",
        "efficacy reduction in erythema (p < 0.01) and exhibited a skin irritation index of 0.02,",
        "satisfying all criteria for hypoallergenic non-irritating topical formulation certification.",
        "",
        "Regulatory Reference:",
        "Ayush Bio-Analytical Assay LAB-904, Page 3, Section 4",
        "",
        "Page 3 of 4"
    ]
    _create_page_with_text(writer, p3_lines)

    # --- Page 4: Quality Assurance Approval & Signatures ---
    p4_lines = [
        "LAB-AYUSH-904 | DERMATOLOGICAL ASSAY CERTIFICATE",
        "--------------------------------------------------------------------------------",
        "SECTION 5: QUALITY ASSURANCE & LABORATORY ATTESTATION",
        "--------------------------------------------------------------------------------",
        "",
        "The analytical data in this certificate has been reviewed and certified compliant with",
        "ISO/IEC 17025 standards and CDSCO cosmetics regulatory testing guidelines.",
        "",
        "Authorized Signatory: Dr. Sunita Rao, Head of Bio-Analytical Testing",
        "Quality Assurance Manager: Rajesh Kumar, QA/QC Lead",
        "Ayush Bio-Analytical Testing Laboratories, Central Testing Facility",
        "Citation: Ayush Bio-Analytical Assay LAB-904, Page 3, Section 4",
        "",
        "Page 4 of 4"
    ]
    _create_page_with_text(writer, p4_lines)

    writer.add_metadata({
        "/Title": "Independent Dermatological Patch Test & Efficacy Certificate",
        "/Subject": "Assay Certificate LAB-AYUSH-904",
        "/Author": "Ayush Bio-Analytical Testing Laboratories",
        "/Producer": "Brandwise Synthetic Fixture Generator"
    })

    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pdf_bytes)

    return pdf_bytes


def generate_corrupted_pdf_bytes() -> bytes:
    """Returns malformed byte sequence mimicking corrupted PDF file."""
    return b"%PDF-1.4\n%Malformed corrupted bytes without EOF marker or catalog dictionary\x00\xff\xfe"


def generate_empty_pdf_bytes() -> bytes:
    """Returns completely 0-byte payload."""
    return b""


def generate_all_fixtures(output_dir: str | Path) -> dict[str, Path]:
    """Generates all standard clinical PDF fixtures into target directory."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    cs_path = target / "Study_CS-2026-88.pdf"
    lab_path = target / "LAB-AYUSH-904.pdf"

    generate_study_cs_2026_88(cs_path)
    generate_lab_ayush_904(lab_path)

    print(f"[FIXTURE] Generated Study CS-2026-88: {cs_path} ({cs_path.stat().st_size} bytes)")
    print(f"[FIXTURE] Generated LAB-AYUSH-904:    {lab_path} ({lab_path.stat().st_size} bytes)")

    return {
        "CS-2026-88": cs_path,
        "LAB-AYUSH-904": lab_path
    }


if __name__ == "__main__":
    default_dir = Path(__file__).resolve().parent
    generated = generate_all_fixtures(default_dir)
    print("All synthetic clinical trial PDF fixtures successfully generated!")
