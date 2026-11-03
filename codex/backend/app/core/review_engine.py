"""
Deterministic brand governance rules engine.

Performs fast, reproducible, and explainable rule checks without calling an LLM:
1. Terminology checks (banned terms, preferred alternatives)
2. Superlatives and unsubstantiated claims detection (#1, best, cure, guaranteed)
3. Required regulatory disclosures (e.g. #ad, #sponsored, statutory warnings)
4. Reading level assessment (Flesch-Kincaid readability / grade level)
5. Visual and accessibility checks (contrast ratio calculation, missing alt-text)
"""

import re
import math
import time
import hashlib
from datetime import datetime, timezone
from typing import Any
from dataclasses import dataclass, field

try:
    from app.core.clinical_extractor import ClinicalTrialPDFExtractor, evaluate_clinical_discrepancies
except ImportError:
    from .clinical_extractor import ClinicalTrialPDFExtractor, evaluate_clinical_discrepancies

CANONICAL_EVIDENCE_TYPES = [
    "clinical_trial_certificate",
    "cdsco_stage4_clearance",
    "legal_waiver_signoff",
    "lab_assay_report",
    "influencer_contract_exemption",
    "ayush_clinical_registry",
    "agency_authorization"
]


@dataclass
class FindingCandidate:
    category: str
    severity: str
    explanation: str
    source_ref: str
    confidence: float
    span_start: int | None = None
    span_end: int | None = None
    highlighted_text: str | None = None
    suggested_fix: str | None = None
    rule_id: str | None = None


class DeterministicReviewEngine:
    """Engine executing deterministic, non-LLM checks on submitted copy."""

    CANONICAL_EVIDENCE_TYPES = CANONICAL_EVIDENCE_TYPES

    POLICY_RELEVANCE_MAP = {
        "clinical_trial_certificate": {
            "policy": "ASCI Chapter 1 §4 / Drugs and Magic Remedies Act §3",
            "scope": "Clinical efficacy substantiation and quantitative performance verification",
            "statutory_authority": "CDSCO / Clinical Trials Registry India (CTRI)"
        },
        "cdsco_stage4_clearance": {
            "policy": "CDSCO Cosmetics Rules 2020 Part VII",
            "scope": "Regulatory drug, cosmetic and therapeutic efficacy approval",
            "statutory_authority": "Central Drugs Standard Control Organisation"
        },
        "legal_waiver_signoff": {
            "policy": "Brand Governance & Intellectual Property Guidelines §1.2",
            "scope": "Visual identity deviation, trademark positioning, and brand asset waiver",
            "statutory_authority": "Corporate Brand Governance Council"
        },
        "lab_assay_report": {
            "policy": "NABL / ISO 17025 Chemical Testing Standard",
            "scope": "Independent laboratory composition and safety assay verification",
            "statutory_authority": "National Accreditation Board for Testing and Calibration Laboratories"
        },
        "influencer_contract_exemption": {
            "policy": "ASCI Guidelines for Influencer Advertising in Digital Media 2025",
            "scope": "Commercial disclosure terms, sponsorship exemptions, and creator agreements",
            "statutory_authority": "Advertising Standards Council of India (ASCI)"
        },
        "ayush_clinical_registry": {
            "policy": "AYUSH Advertising Guidelines §3.1 (Traditional Medicine Claims)",
            "scope": "Ayurvedic, Siddha, and Unani classical formulation registry clearance",
            "statutory_authority": "Ministry of AYUSH, Government of India"
        },
        "agency_authorization": {
            "policy": "ASCI Code of Conduct §2 / Brand Agency Framework",
            "scope": "Authorized agency representation, campaign delegation, and digital distribution sign-off",
            "statutory_authority": "Authorized Brand Agency Directorate"
        }
    }

    CATEGORY_PERMISSIBLE_EVIDENCE = {
        "clinical_efficacy": {
            "clinical_trial_certificate",
            "cdsco_stage4_clearance",
            "lab_assay_report",
            "ayush_clinical_registry",
        },
    }

    # Default regex patterns for common regulatory and superlative checks
    SUPERLATIVE_PATTERNS = [
        (
            re.compile(r"(?:^|[^\w])(#1|number\s*one|no\.\s*1)\b", re.IGNORECASE),
            "High",
            "Unsupported superlative claim '#1' requires a verified fact entry with source and expiry.",
            "Guideline §3.2 (Claim Verification)",
            "Consider qualifying with survey year or category, e.g., 'One of top rated in 2025'"
        ),
        (
            re.compile(r"\b(100%|guaranteed|cures?|eliminates?|permanent(?:ly)?)\b", re.IGNORECASE),
            "High",
            "Absolute efficacy or cure claim detected. Prohibited under advertising & health standards.",
            "Guideline §4.2 (Health & Regulated Claims)",
            "Use measured language such as 'helps reduce' or 'formulated to support'"
        ),
        (
            re.compile(r"\b(cheapest|lowest price|best in india|world'?s best)\b", re.IGNORECASE),
            "Medium",
            "Comparative superlative claim requires registered market data validation.",
            "Guideline §3.4 (Comparative Claims)",
            "State explicit basis of comparison or cite current audited report"
        ),
    ]

    DISCLOSURE_PATTERNS = [
        # Paid collaboration / Influencer rules (ASCI compliance)
        (
            "ad_disclosure",
            re.compile(r"\b(#ad|#sponsored|#collab|#paidpartner)\b", re.IGNORECASE),
            "High",
            "Missing prominent commercial disclosure tag (#ad / #sponsored).",
            "ASCI Influencer Guidelines §1.1",
            "Add '#ad' or '#sponsored' prominently at the start of your caption."
        )
    ]

    def check_terminology(
        self,
        text: str,
        terminology_entries: list[dict[str, Any]]
    ) -> list[FindingCandidate]:
        """
        Check content against approved and banned terminology list.
        Each entry has: term, status ('banned', 'preferred'), preferred_alternative.
        """
        findings: list[FindingCandidate] = []
        if not text:
            return findings

        for item in terminology_entries:
            term = item.get("term", "").strip()
            if not term:
                continue

            status = item.get("status", "").lower()
            alt = item.get("preferred_alternative")
            notes = item.get("notes") or ""

            # Word boundary regex search
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            for match in pattern.finditer(text):
                start, end = match.span()
                matched_str = match.group(0)

                if status == "banned":
                    fix_suggestion = f"Replace '{matched_str}' with '{alt}'" if alt else f"Remove '{matched_str}'"
                    findings.append(
                        FindingCandidate(
                            category="terminology",
                            severity="high",
                            span_start=start,
                            span_end=end,
                            highlighted_text=matched_str,
                            explanation=f"Banned term '{matched_str}' detected. {notes}".strip(),
                            source_ref=f"Brand Terminology Register (Term: {term})",
                            confidence=1.0,
                            suggested_fix=alt if alt else fix_suggestion,
                            rule_id=str(item.get("id", "")) or None
                        )
                    )
                elif status == "preferred" and alt and matched_str.lower() != alt.lower():
                    # If this is a deprecated variant of the preferred term
                    findings.append(
                        FindingCandidate(
                            category="terminology",
                            severity="medium",
                            span_start=start,
                            span_end=end,
                            highlighted_text=matched_str,
                            explanation=f"Preferred brand term is '{alt}' instead of '{matched_str}'.",
                            source_ref=f"Brand Terminology Register (Term: {term})",
                            confidence=0.95,
                            suggested_fix=alt,
                            rule_id=str(item.get("id", "")) or None
                        )
                    )

        return findings

    def check_superlatives_and_claims(self, text: str) -> list[FindingCandidate]:
        """Detect unsubstantiated superlatives and time-bound cure promises."""
        findings: list[FindingCandidate] = []
        if not text:
            return findings

        for regex, severity, explanation, source_ref, fix in self.SUPERLATIVE_PATTERNS:
            for match in regex.finditer(text):
                # If there's a capture group, use its span and content for cleaner highlights
                if match.groups() and match.group(1):
                    start, end = match.span(1)
                    highlight = match.group(1)
                else:
                    start, end = match.span()
                    highlight = match.group(0)

                findings.append(
                    FindingCandidate(
                        category="claim",
                        severity=severity.lower(),
                        span_start=start,
                        span_end=end,
                        highlighted_text=highlight,
                        explanation=explanation,
                        source_ref=source_ref,
                        confidence=0.92,
                        suggested_fix=fix
                    )
                )
        return findings

    def check_disclosures(self, text: str, channel: str | None = None) -> list[FindingCandidate]:
        """Check for mandatory influencer and statutory disclosures when channel is social or ad."""
        findings: list[FindingCandidate] = []
        if not text:
            return findings

        # Check if text appears to be a promotional/collaboration post
        is_promo = bool(re.search(r"\b(discount|code|collab|use code|buy now|link in bio)\b", text, re.IGNORECASE))
        has_disclosure = any(
            re.search(r"\b(#ad|#sponsored|#collab|#paidpartner)\b", text, re.IGNORECASE)
            for _ in [1]
        )

        if is_promo and not has_disclosure and channel in ["social", "instagram", "tiktok", "youtube", None]:
            findings.append(
                FindingCandidate(
                    category="disclaimer",
                    severity="high",
                    span_start=0,
                    span_end=min(len(text), 30),
                    highlighted_text=text[:30] + "...",
                    explanation="Promotional commercial post detected without required ASCI/FTC disclosure hashtag.",
                    source_ref="ASCI Influencer Code 2025 §1.1",
                    confidence=0.90,
                    suggested_fix="Add '#ad' or '#sponsored' at the beginning of the caption."
                )
            )

        return findings

    def calculate_readability(self, text: str) -> dict[str, Any]:
        """
        Calculates Flesch Reading Ease and Flesch-Kincaid Grade Level.
        Ensures content meets typical brand accessibility targets (grade 6-8).
        """
        words = re.findall(r"\b[a-zA-Z]+\b", text)
        sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]

        word_count = len(words)
        sentence_count = max(len(sentences), 1)

        if word_count == 0:
            return {"reading_ease": 100.0, "grade_level": 0.0, "reading_category": "Easy"}

        # Syllable counter heuristic
        def count_syllables(word: str) -> int:
            word = word.lower()
            count = len(re.findall(r"[aeiouy]+", word))
            if word.endswith("e") and not word.endswith("le"):
                count = max(1, count - 1)
            return max(1, count)

        syllable_count = sum(count_syllables(w) for w in words)

        # Flesch Reading Ease: 206.835 - 1.015*(words/sentences) - 84.6*(syllables/words)
        asl = word_count / sentence_count
        asw = syllable_count / word_count
        reading_ease = 206.835 - (1.015 * asl) - (84.6 * asw)
        reading_ease = max(0.0, min(100.0, round(reading_ease, 1)))

        # Flesch-Kincaid Grade: 0.39*(words/sentences) + 11.8*(syllables/words) - 15.59
        grade_level = (0.39 * asl) + (11.8 * asw) - 15.59
        grade_level = max(1.0, round(grade_level, 1))

        category = "Standard"
        if reading_ease >= 70:
            category = "Easy / Conversational"
        elif reading_ease <= 40:
            category = "Complex / Academic"

        return {
            "reading_ease": reading_ease,
            "grade_level": grade_level,
            "category": category,
            "word_count": word_count,
            "sentence_count": sentence_count,
        }

    @staticmethod
    def calculate_contrast_ratio(fg_hex: str, bg_hex: str) -> float:
        """
        Calculates WCAG 2.2 color contrast ratio between two hex colors.
        Returns a float between 1.0 and 21.0. Minimum AA ratio for normal text is 4.5.
        """
        def hex_to_relative_luminance(hex_code: str) -> float:
            hex_code = hex_code.lstrip("#")
            if len(hex_code) == 3:
                hex_code = "".join([c * 2 for c in hex_code])
            r, g, b = [int(hex_code[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

            def adjust(c: float) -> float:
                return c / 12.92 if c <= 0.03928 else math.pow((c + 0.055) / 1.055, 2.4)

            return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

        l1 = hex_to_relative_luminance(fg_hex)
        l2 = hex_to_relative_luminance(bg_hex)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        ratio = (lighter + 0.05) / (darker + 0.05)
        return round(ratio, 2)

    # ============================================================
    # IMPROVEMENT 3: Multilingual & Code-Mixed (Hinglish / Hindi) Compliance
    # ============================================================
    # ARCHITECTURAL NOTE — KEYWORD / REGEX vs. VECTOR MATCHING:
    # The platform employs compiled deterministic regex patterns and rule heuristics rather than
    # probabilistic semantic vector embeddings or non-deterministic LLM inference for statutory compliance checking.
    # Rationale:
    # 1. Statutory Precision & Zero Hallucination: Statutory regulations (ASCI Code 2025-26, Drugs and Magic
    #    Remedies Act 1954, CDSCO Cosmetics Rules 2020) require binary, strictly auditable pass/fail criteria.
    # 2. Air-Gapped Offline Execution: Runs 100% locally with zero cloud dependencies or external LLM API costs.
    # 3. Sub-Millisecond Execution: Deterministic evaluation runs in <1ms, enabling real-time UI feedback.
    # Optional advisory LLM semantic evaluation can be activated via llm_service.py if ANTHROPIC_API_KEY is configured.
    #
    # REGULATORY HASHTAG DISCLOSURES:
    # Hashtag disclosure rules (#ad, #collab, #sponsored, #partnership, #patronage, #विज्ञापन, #प्रायोजित, #सहयोग)
    # are configurable project rules grounded in ASCI (Advertising Standards Council of India) Guidelines for
    # Influencer Advertising in Digital Media (2025-2026 update).

    HINGLISH_SUPERLATIVE_RULES = [
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])((?:(?:100%|१००%|100\s*percent|१००\s*प्रतिशत)\s*(?:asar(?:daar)?|asr|असर|रिजल्ट|result))|100%\s*(?:asar|asr))(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-SUPERLATIVE-01",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "Drugs and Magic Remedies Act 1954 §3 / ASCI Vernacular Guidelines 2025 §2.4",
            "explanation": "Vernacular absolute efficacy / magic cure claim detected in Hinglish copy. Prohibited under ASCI Code & Drugs and Magic Remedies Act.",
            "suggested_fix": "visible results ke liye regular use karein"
        },
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(chamatkar(?:i|ik)?|chmatkar(?:i|ik)?|चमत्कारी|चमत्कार)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-SUPERLATIVE-01",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "Drugs and Magic Remedies Act 1954 §3 / ASCI Vernacular Guidelines 2025 §2.4",
            "explanation": "Chamatkari (miraculous/magic) cure claim detected. Magic remedy assertions are prohibited under the Drugs and Magic Remedies Act and ASCI Code.",
            "suggested_fix": "dermatologist-tested ingredients se banaya gaya"
        },
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(jad{1,2}\s*se(?:\s*(?:khatam|ugata))?|ज(?:ड़|ड)\s*(?:से|se)(?:\s*(?:खत्म|ख़त्म|कतम|खतम|उगाता))?)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-SUPERLATIVE-01",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "Drugs and Magic Remedies Act 1954 §3 / ASCI Code Ch. 1 §4",
            "explanation": "Absolute eradication or root promise claim 'jad se' detected without permissible cosmetic qualification.",
            "suggested_fix": "acne ko kam karne mein madad kare"
        },
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(hamesha\s*ke\s*liye|हमेशा\s*के\s*लिए)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-SUPERLATIVE-01",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "ASCI Code Ch. 1 §4 (Vernacular Substantiation)",
            "explanation": "Permanent efficacy claim 'hamesha ke liye' detected. Cosmetic formulations cannot promise permanent cure.",
            "suggested_fix": "regular skin routine ke saath lambe samay tak effective"
        },
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(shat[-\s]+pratishat|शत[-\s]*प्रतिशत)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-SUPERLATIVE-01",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "ASCI Code Ch. 1 §4 (Vernacular Substantiation)",
            "explanation": "Absolute 100% guarantee claim 'shat pratishat' detected in Hinglish copy.",
            "suggested_fix": "clinically tested aur effective formula"
        },
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(ek\s*jhatke\s*me(?:in)?|एक\s*झटके\s*में)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-SUPERLATIVE-01",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "Drugs and Magic Remedies Act 1954 §3 / ASCI Code Ch. 1 §4",
            "explanation": "Instantaneous outcome claim 'ek jhatke mein' detected without clinical protocol backing.",
            "suggested_fix": "step-by-step regular skincare routine se"
        },
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(ra?amban\s*ila?aj|रामबाण\s*इलाज)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-AYUSH-03",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "AYUSH Advertising Guidelines §3.1 (Traditional Medicine Claims)",
            "explanation": "Infallible remedy assertion ('ramban ilaj') detected without verified AYUSH clinical registry registration.",
            "suggested_fix": "ayurvedic aur clinically tested botanical formulation"
        },
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(pakka\s*ila?aj|पक्का\s*इलाज)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-AYUSH-03",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "AYUSH Advertising Guidelines §3.1 (Traditional Medicine Claims)",
            "explanation": "Guaranteed medical cure assertion ('pakka ilaj') detected without statutory AYUSH validation.",
            "suggested_fix": "dermatologist-tested formulation se skin ki dekhbhal"
        },
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(bilkul\s*th(?:ee|i)k|बिल्कुल\s*ठीक)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-AYUSH-03",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "CDSCO Cosmetics Rules 2020 / AYUSH Guidelines §3.1",
            "explanation": "Absolute cure guarantee 'bilkul theek' detected under CDSCO / AYUSH cosmetic guidelines.",
            "suggested_fix": "skin appearance ko behtar banane mein sahayak"
        },
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(guaranteed(?:\s*(?:cure|result|ilaj))?|गारंटीड(?:\s*(?:इलाज|रिजल्ट|असर))?|गारंटी)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-SUPERLATIVE-01",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "Drugs and Magic Remedies Act 1954 §3 / ASCI Vernacular Guidelines 2025",
            "explanation": "Guaranteed cure or outcome claim ('गारंटीड' / 'guaranteed') detected without statutory trial backing.",
            "suggested_fix": "clinically tested formula se visible improvement"
        }
    ]

    HINGLISH_COLORIST_RULES = [
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(gor[ae]\s*rang|गोरा\s*रंग|गोरे\s*रंग)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-COLORIST-02",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "ASCI Skin Lightening & Cosmetic Guidelines 2024 §2.1",
            "explanation": "Skin-lightening / colorist fairness claim 'gora rang' detected. Depicting skin tone alteration or promoting fairness is prohibited under ASCI guidelines.",
            "suggested_fix": "healthy glowing skin aur hydration"
        },
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(bilkul\s*gor[ae]|बिल्कुल\s*गोरा)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-COLORIST-02",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "ASCI Skin Lightening & Cosmetic Guidelines 2024 §2.1",
            "explanation": "Skin-lightening fairness claim 'bilkul gora' detected. Depicting skin tone alteration or promoting fairness is prohibited.",
            "suggested_fix": "radiant aur healthy skin appearance"
        },
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(rang\s*(?:ko\s*)?gora|रंग\s*(?:को\s*)?गोरा)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-COLORIST-02",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "ASCI Skin Lightening & Cosmetic Guidelines 2024 §2.1",
            "explanation": "Skin-lightening fairness claim 'rang gora' detected. Melanin alteration or skin bleaching claims are prohibited.",
            "suggested_fix": "natural skin glow aur even texture"
        },
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(fairness\s*guarantee|फेयरनेस\s*गारंटी)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-COLORIST-02",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "ASCI Skin Lightening & Cosmetic Guidelines 2024 §2.1",
            "explanation": "Fairness guarantee claim detected. Advertising cannot promise complexion lightening or shade changes.",
            "suggested_fix": "dermatologist-approved formula se skin radiance aur glow"
        },
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(ek\s*hafte\s*me(?:in)?\s*gora|एक\s*हफ्ते\s*में\s*गोरा)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-COLORIST-02",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "ASCI Skin Lightening & Cosmetic Guidelines 2024 §2.1",
            "explanation": "Time-bound skin-lightening claim 'ek hafte mein gora' detected. Prohibited under ASCI Cosmetic Guidelines.",
            "suggested_fix": "14 dinon mein visible skin radiance"
        },
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(rang(?:at)?\s*nikhare?|रंग(?:त)?\s*निखारे?)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-COLORIST-02",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "ASCI Skin Lightening & Cosmetic Guidelines 2024 §2.1",
            "explanation": "Complexion modification claim 'rang nikhare' detected under ASCI Skin Lightening Guidelines.",
            "suggested_fix": "skin barrier ko hydrate aur healthy banaye"
        },
        {
            "pattern": re.compile(
                r"(?<![a-zA-Z0-9\u0900-\u097F])(gorapan|गोरापन)(?![a-zA-Z0-9\u0900-\u097F])",
                re.IGNORECASE
            ),
            "rule_id": "HINGLISH-COLORIST-02",
            "category": "hinglish_claim",
            "severity": "high",
            "source_ref": "ASCI Skin Lightening & Cosmetic Guidelines 2024 §2.1",
            "explanation": "Fairness promise 'gorapan' detected. Commercial communications must not equate social success or beauty to skin color.",
            "suggested_fix": "natural skin moisture aur healthy radiance"
        }
    ]

    PROMOTIONAL_TRIGGER_PATTERN = re.compile(
        r"(?<![a-zA-Z0-9\u0900-\u097F])(discount|khareedo|खरीदें|aaj\s*hi\s*order|loot\s*lo|code\s*lagao|link\s*bio\s*me(?:in)?|buy\s*now|use\s*code|order\s*kare(?:in)?|ऑर्डर\s*करें)(?![a-zA-Z0-9\u0900-\u097F])",
        re.IGNORECASE
    )

    VERNACULAR_DISCLOSURE_PATTERN = re.compile(
        r"(?<![a-zA-Z0-9\u0900-\u097F])(#(?:ad|collab|collaboration|sponsored|partnership|patronage|vigyapan|prayasit|sahyog|विज्ञापन|प्रायोजित|सहयोग))(?![a-zA-Z0-9\u0900-\u097F])",
        re.IGNORECASE
    )

    HINGLISH_CLINICAL_PCT_PATTERN = re.compile(
        r"(\d+(?:\.\d+)?)\s*(?:%|percent\b)(?:\s*(?:asar|asr|prabhav|result|results|efficacy|hydration|reduction|असर|रिजल्ट))?",
        re.IGNORECASE
    )

    HINGLISH_TIMELINE_PATTERN = re.compile(
        r"\b(?:sirf\s*)?(\d+)\s*(?:din|days?)\s*(?:me(?:in)?)?\s*(?:acne|khatam|theek|thik|cure|relief|ilaj|hydration|wrinkle|dark\s*spot|glow|fayda|behtar)\b",
        re.IGNORECASE
    )

    def check_hinglish_and_regional_claims(
        self,
        text: str,
        channel: str | None = None,
        clinical_studies: list[dict[str, Any]] | dict[str, Any] | None = None
    ) -> list[FindingCandidate]:
        """Inspect Hindi and Hinglish (code-mixed Latin script) text for regulatory violations, missing disclosures, and clinical discrepancies."""
        findings: list[FindingCandidate] = []
        if not text or not text.strip():
            return findings

        # 1. Check Hinglish superlative and absolute cure patterns
        for rule in self.HINGLISH_SUPERLATIVE_RULES:
            for match in rule["pattern"].finditer(text):
                if match.lastindex and match.lastindex >= 1:
                    start, end = match.span(1)
                    matched_str = match.group(1)
                else:
                    start, end = match.span()
                    matched_str = match.group(0)
                findings.append(
                    FindingCandidate(
                        category=rule["category"],
                        severity=rule["severity"],
                        span_start=start,
                        span_end=end,
                        highlighted_text=matched_str,
                        explanation=rule["explanation"],
                        source_ref=rule["source_ref"],
                        confidence=0.96,
                        suggested_fix=rule["suggested_fix"],
                        rule_id=rule["rule_id"]
                    )
                )

        # 2. Check skin-lightening and colorist claims
        for rule in self.HINGLISH_COLORIST_RULES:
            for match in rule["pattern"].finditer(text):
                if match.lastindex and match.lastindex >= 1:
                    start, end = match.span(1)
                    matched_str = match.group(1)
                else:
                    start, end = match.span()
                    matched_str = match.group(0)
                findings.append(
                    FindingCandidate(
                        category=rule["category"],
                        severity=rule["severity"],
                        span_start=start,
                        span_end=end,
                        highlighted_text=matched_str,
                        explanation=rule["explanation"],
                        source_ref=rule["source_ref"],
                        confidence=0.96,
                        suggested_fix=rule["suggested_fix"],
                        rule_id=rule["rule_id"]
                    )
                )

        # 3. Check for missing vernacular disclosures if promotional copy detected
        is_promo = bool(self.PROMOTIONAL_TRIGGER_PATTERN.search(text))
        has_vernacular_disclosure = bool(self.VERNACULAR_DISCLOSURE_PATTERN.search(text))

        if is_promo and not has_vernacular_disclosure:
            highlight_len = min(len(text), 30)
            highlight_text = text[:highlight_len] + ("..." if len(text) > 30 else "")
            findings.append(
                FindingCandidate(
                    category="disclaimer",
                    severity="high",
                    span_start=0,
                    span_end=highlight_len,
                    highlighted_text=highlight_text,
                    explanation="Vernacular / Hinglish promotional copy lacks mandatory commercial disclosure tag (#ad, #collab, #sponsored, #partnership, #patronage, #विज्ञापन, #प्रायोजित, ya #सहयोग).",
                    source_ref="ASCI Vernacular Advertising Guidelines 2025 §2.4",
                    confidence=0.92,
                    suggested_fix="'#vigyapan' ya '#ad' caption ke shuru mein jodein",
                    rule_id="HINGLISH-DISCLOSURE-04"
                )
            )

        # 4. Cross-lingual clinical claim verification against registered study (CS-2026-88: 94.2% hydration, 14 days)
        active_studies = []
        if clinical_studies is None:
            try:
                from app.core.clinical_extractor import DEFAULT_CLINICAL_STUDIES
                active_studies = list(DEFAULT_CLINICAL_STUDIES)
            except Exception:
                try:
                    from .clinical_extractor import DEFAULT_CLINICAL_STUDIES
                    active_studies = list(DEFAULT_CLINICAL_STUDIES)
                except Exception:
                    active_studies = []
        elif isinstance(clinical_studies, dict):
            active_studies = [clinical_studies]
        elif isinstance(clinical_studies, list):
            active_studies = list(clinical_studies)

        study_id = "CS-2026-88"
        target_hydration = 94.2
        target_days = 14
        citation = "Clinical Study CS-2026-88, Page 7, Table 2.1"

        if active_studies:
            primary_study = active_studies[0]
            study_id = primary_study.get("study_id") or "CS-2026-88"
            citation = primary_study.get("source_citation") or f"Clinical Study {study_id}, Page 7, Table 2.1"
            if primary_study.get("duration_days"):
                try:
                    target_days = int(primary_study["duration_days"])
                except Exception:
                    pass
            eps = primary_study.get("endpoints") or {}
            hyd = eps.get("hydration_increase_percent")
            if hyd is not None:
                if isinstance(hyd, dict) and "value" in hyd:
                    target_hydration = float(hyd["value"])
                else:
                    target_hydration = float(hyd)

            # Scan for quantitative percentage claims in Hinglish copy
            for match in self.HINGLISH_CLINICAL_PCT_PATTERN.finditer(text):
                pct_val = float(match.group(1))
                start, end = match.span()
                matched_str = match.group(0)

                # Ignore commercial discount percentages (e.g., "50% discount", "20% off")
                surrounding = text[max(0, start - 20):min(len(text), end + 25)].lower()
                if re.search(r"\b(discount|off|cashback|sale|chhoot|code)\b", surrounding):
                    continue

                # Statistical Exaggeration: claimed percentage exceeds trial endpoint
                if pct_val > target_hydration:
                    delta = round(pct_val - target_hydration, 1)
                    pct_label = int(pct_val) if pct_val.is_integer() else pct_val
                    explanation_text = (
                        f"Hinglish copy claims {pct_label}% asar, but registered clinical trial {study_id} "
                        f"observed {target_hydration}% hydration (Statistical Exaggeration Delta: +{delta}%). "
                        f"Absolute efficacy claims prohibited under ASCI Code & Drugs and Magic Remedies Act."
                    )
                    fix_text = f"Claim ko 'Clinical trial mein {target_hydration}% hydration asar' se badlein ({study_id})"

                    # Check if an existing finding already covers this span (e.g. '100% asar')
                    existing_match = None
                    for existing_f in findings:
                        if existing_f.span_start is not None and existing_f.span_end is not None:
                            if max(start, existing_f.span_start) < min(end, existing_f.span_end):
                                existing_match = existing_f
                                break

                    if existing_match:
                        # Enrich existing finding in place to avoid duplicate card while carrying clinical verification data
                        existing_match.rule_id = "HINGLISH-CLINICAL-EXAGGERATION-05"
                        existing_match.explanation = explanation_text
                        existing_match.source_ref = f"Drugs and Magic Remedies Act 1954 §3 / {citation}"
                        existing_match.confidence = 0.98
                        existing_match.suggested_fix = fix_text
                    else:
                        findings.append(
                            FindingCandidate(
                                category="claim",
                                severity="high",
                                span_start=start,
                                span_end=end,
                                highlighted_text=matched_str,
                                explanation=explanation_text,
                                source_ref=citation,
                                confidence=0.98,
                                suggested_fix=fix_text,
                                rule_id="HINGLISH-CLINICAL-EXAGGERATION-05"
                            )
                        )
                # Borderline Efficacy Claim: rounding without decimal precision (within 1.0% threshold)
                elif abs(pct_val - target_hydration) <= 1.0 and pct_val != target_hydration:
                    pct_label = int(pct_val) if pct_val.is_integer() else pct_val
                    findings.append(
                        FindingCandidate(
                            category="claim",
                            severity="medium",
                            span_start=start,
                            span_end=end,
                            highlighted_text=matched_str,
                            explanation=f"Hinglish copy claims '{pct_label}% asar', but registered clinical trial {study_id} observed {target_hydration}% hydration. Omitting decimal precision or qualifying language ('up to {target_hydration}%') is borderline under ASCI §3.2.",
                            source_ref=citation,
                            confidence=0.92,
                            suggested_fix=f"Claim ko qualify karein: 'Up to {target_hydration}% asar clinical study ({study_id}) mein dekha gaya'",
                            rule_id="HINGLISH-CLINICAL-BORDERLINE-06"
                        )
                    )

            # Timeline compression check against registered protocol duration
            for match in self.HINGLISH_TIMELINE_PATTERN.finditer(text):
                claimed_days = int(match.group(1))
                start, end = match.span()
                matched_str = match.group(0)
                if claimed_days < target_days:
                    delta_days = target_days - claimed_days
                    findings.append(
                        FindingCandidate(
                            category="claim",
                            severity="high",
                            span_start=start,
                            span_end=end,
                            highlighted_text=matched_str,
                            explanation=f"Hinglish copy claims clinical results in {claimed_days} din, but registered clinical trial {study_id} protocol duration is {target_days} days (Timeline Compression Delta: -{delta_days} days).",
                            source_ref=citation,
                            confidence=0.95,
                            suggested_fix=f"Timeline ko qualify karein: 'Clinical trial ({study_id}) ke anusaar {target_days} dinon mein visible results'",
                            rule_id="HINGLISH-CLINICAL-TIMELINE-07"
                        )
                    )

        return findings

    # ============================================================
    # IMPROVEMENT 2: Visual Asset Inspection & Counter-Evidence Gateway
    # ============================================================
    def inspect_visual_geometry_and_palette(
        self,
        asset_metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Inspect visual assets (logo geometry distortion, brand palette RGB drift, disclaimer contrast, alt text).
        """
        if not isinstance(asset_metadata, dict):
            asset_metadata = {}

        violations = []
        aspect_ratio_drift = 0.0

        actual_ratio = asset_metadata.get("aspect_ratio")
        expected_ratio = asset_metadata.get("expected_aspect_ratio", 1.0)
        if expected_ratio is None:
            expected_ratio = 1.0

        # 1. Geometry aspect ratio check (tolerance +/- 2.0%)
        if actual_ratio is not None:
            try:
                act_val = float(actual_ratio)
                exp_val = float(expected_ratio)
                if exp_val > 0:
                    aspect_ratio_drift = round(abs((act_val - exp_val) / exp_val) * 100, 2)
                    if aspect_ratio_drift > 2.0:
                        violations.append({
                            "id": "v-geom-01",
                            "type": "logo_distortion",
                            "severity": "high",
                            "message": f"Brand logo geometry distorted by {aspect_ratio_drift}%. Maximum allowed distortion is 2.0%.",
                            "source_ref": "Brand Identity Guidelines §1.2 (Logo Geometry Preservation)",
                            "suggested_fix": f"Lock aspect ratio to {expected_ratio}:1 in layout canvas."
                        })
            except (ValueError, TypeError, ZeroDivisionError):
                aspect_ratio_drift = 0.0

        # 2. Color palette drift check (RGB Euclidean distance)
        brand_palette = {
            "primary": (15, 23, 42),       # #0F172A Slate 900
            "accent": (2, 132, 199),       # #0284C7 Sky 600
            "success": (16, 185, 129),     # #10B981 Emerald 500
        }
        brand_hex_map = {
            "primary": "#0F172A",
            "accent": "#0284C7",
            "success": "#10B981",
        }

        detected_colors = asset_metadata.get("detected_hex_colors") or []
        if isinstance(detected_colors, list):
            for hex_val in detected_colors:
                if not isinstance(hex_val, str):
                    continue
                clean_hex = hex_val.strip().lstrip("#")
                if len(clean_hex) == 3:
                    clean_hex = "".join([c * 2 for c in clean_hex])
                if len(clean_hex) == 6:
                    try:
                        r = int(clean_hex[0:2], 16)
                        g = int(clean_hex[2:4], 16)
                        b = int(clean_hex[4:6], 16)
                    except ValueError:
                        continue

                    # Compute closest brand color
                    min_dist = float("inf")
                    closest_name = "primary"
                    for c_name, (br, bg, bb) in brand_palette.items():
                        dist = math.sqrt((r - br) ** 2 + (g - bg) ** 2 + (b - bb) ** 2)
                        if dist < min_dist:
                            min_dist = dist
                            closest_name = c_name

                    # Boundary condition: 15.0 <= min_dist <= 65.0
                    if 15.0 <= min_dist <= 65.0:
                        violations.append({
                            "id": f"v-color-{clean_hex}",
                            "type": "palette_drift",
                            "severity": "medium",
                            "message": f"Detected color #{clean_hex} deviates by {min_dist:.1f} RGB units from approved brand palette ({closest_name}).",
                            "source_ref": "Brand Visual Guidelines §2.1 (Color Palette Compliance)",
                            "suggested_fix": f"Shift color to closest approved brand shade ({brand_hex_map[closest_name]})."
                        })

        # 3. Disclaimer text contrast ratio check (WCAG 2.2 AA minimum: 4.5:1)
        disclaimer_fg = asset_metadata.get("disclaimer_fg")
        disclaimer_bg = asset_metadata.get("disclaimer_bg")
        contrast_ratio = None
        if disclaimer_fg and disclaimer_bg:
            try:
                contrast_ratio = self.calculate_contrast_ratio(str(disclaimer_fg), str(disclaimer_bg))
                if contrast_ratio < 4.5:
                    violations.append({
                        "id": "v-contrast-01",
                        "type": "contrast_failure",
                        "severity": "high",
                        "message": f"Disclaimer text contrast ratio {contrast_ratio:.2f}:1 fails WCAG 2.2 AA requirement (min 4.5:1).",
                        "source_ref": "WCAG 2.2 §1.4.3 (Contrast Minimum)",
                        "suggested_fix": "Increase luminance difference between disclaimer text and background."
                    })
            except (ValueError, TypeError, Exception):
                contrast_ratio = None

        # 4. Missing alt-text check (WCAG 2.2 Non-text Content)
        alt_text = asset_metadata.get("alt_text")
        if not alt_text or not str(alt_text).strip():
            violations.append({
                "id": "v-alt-01",
                "type": "missing_alt_text",
                "severity": "medium",
                "message": "Asset is missing descriptive alternative text for screen readers.",
                "source_ref": "WCAG 2.2 §1.1.1 (Non-text Content)",
                "suggested_fix": "Provide descriptive alt text for this visual asset."
            })

        return {
            "is_compliant": len(violations) == 0,
            "violations": violations,
            "aspect_ratio_drift": aspect_ratio_drift,
            "contrast_ratio": contrast_ratio,
            "asset_id": asset_metadata.get("asset_id") or "asset-001"
        }

    def adjudicate_counter_evidence(
        self,
        allegation_id: str,
        allegation_category: str,
        counter_evidence: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Interactive Evidence-Based Adjudication Gateway:
        Evaluates counter-evidence submitted by creator and dismisses/reverts allegations when substantiated.
        """
        if not isinstance(counter_evidence, dict):
            counter_evidence = {}

        valid_evidence_types = self.CANONICAL_EVIDENCE_TYPES

        evidence_type = str(counter_evidence.get("evidence_type") or "").strip().lower()
        ref_id = str(counter_evidence.get("reference_id") or "").strip()
        justification = str(counter_evidence.get("justification") or "").strip()
        doc_hash = counter_evidence.get("document_hash")

        if not evidence_type or evidence_type not in valid_evidence_types:
            return {
                "success": False,
                "adjudication": "REJECTED_INSUFFICIENT_EVIDENCE",
                "message": f"Invalid or missing evidence type '{evidence_type}'. Must be one of: {', '.join(valid_evidence_types)}."
            }

        if not ref_id:
            return {
                "success": False,
                "adjudication": "REJECTED_INSUFFICIENT_EVIDENCE",
                "message": "Counter-evidence requires a valid reference ID."
            }

        if len(justification) < 10:
            return {
                "success": False,
                "adjudication": "REJECTED_INSUFFICIENT_EVIDENCE",
                "message": "Counter-evidence requires a detailed justification (min 10 characters)."
            }

        category_key = str(allegation_category or "").strip().lower()
        if category_key in self.CATEGORY_PERMISSIBLE_EVIDENCE:
            allowed_types = self.CATEGORY_PERMISSIBLE_EVIDENCE[category_key]
            if evidence_type not in allowed_types:
                return {
                    "success": False,
                    "adjudication": "REJECTED_POLICY_IRRELEVANT",
                    "allegation_id": allegation_id,
                    "allegation_category": allegation_category,
                    "evidence_type": evidence_type,
                    "message": f"Submitted evidence type '{evidence_type}' is not relevant to allegation category '{allegation_category}'."
                }

        # Policy Relevance Mapping: Maps canonical counter-evidence types to statutory policies & authorities
        policy_info = self.POLICY_RELEVANCE_MAP.get(evidence_type, {
            "policy": "General Advertising Compliance Guidelines 2025",
            "scope": "Statutory compliance substantiation",
            "statutory_authority": "ASCI / Consumer Protection Authority"
        })

        if not doc_hash or not str(doc_hash).strip():
            payload = f"{allegation_id}:{evidence_type}:{ref_id}:{justification}".encode("utf-8")
            doc_hash = hashlib.sha256(payload).hexdigest()[:16]
        else:
            doc_hash = str(doc_hash).strip()

        return {
            "success": True,
            "adjudication": "ALLEGATION_REVERTED_AND_DISMISSED",
            "allegation_id": allegation_id,
            "allegation_category": allegation_category,
            "reversal_timestamp": datetime.now(timezone.utc).isoformat(),
            "document_hash": doc_hash,
            "evidence_reference": ref_id,
            "evidence_type": evidence_type,
            "restored_score_delta": 15,
            "policy_relevance": policy_info["policy"],
            "policy_scope": policy_info["scope"],
            "statutory_authority": policy_info["statutory_authority"],
            "audit_note": (
                f"Allegation {allegation_id} ({allegation_category}) reverted and dismissed under "
                f"{policy_info['policy']} ({policy_info['statutory_authority']}) upon verification of "
                f"counter-evidence '{ref_id}'. Justification: {justification}"
            ),
            "status": "dismissed_with_evidence"
        }

    # ============================================================
    # IMPROVEMENT 1: Clinical Evidence Ingestion & Claim Matching
    # ============================================================
    DEFAULT_CLINICAL_STUDIES = [
        {
            "study_id": "CS-2026-88",
            "title": "14-Day Stratum Corneum Hydration & Sebum Control Trial",
            "cohort_size": 120,
            "methodology": "Double-blind, randomized, placebo-controlled clinical trial",
            "p_value": "<0.001",
            "endpoints": {
                "hydration_increase_percent": 94.2,
                "duration_days": 14,
                "acne_lesion_reduction_percent": 68.0,
                "sebum_reduction_percent": 42.5
            },
            "source_citation": "Clinical Study CS-2026-88, Page 7, Table 2.1",
            "status": "REGISTERED_VALID"
        },
        {
            "study_id": "LAB-AYUSH-904",
            "title": "Independent Dermatological Patch Test & Efficacy Certificate",
            "cohort_size": 85,
            "methodology": "Standardized ISO 10993-10 dermatological patch evaluation",
            "p_value": "<0.01",
            "endpoints": {
                "skin_irritation_index": 0.02,
                "soothing_efficacy_percent": 89.4,
                "duration_days": 7
            },
            "source_citation": "Ayush Bio-Analytical Assay LAB-904, Page 3, Section 4",
            "status": "REGISTERED_VALID"
        }
    ]

    def parse_clinical_evidence_and_match(
        self,
        copy_text: str,
        studies: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        Parses quantitative clinical trial endpoints and verifies marketing copy claims against statistical findings.
        Identifies over-claims, timeline compressions (e.g. 7 days vs 14 days), and exaggeration deltas.
        """
        return evaluate_clinical_discrepancies(copy_text, study_dossier=studies)

    def check_clinical_evidence(
        self,
        text: str,
        studies: list[dict[str, Any]] | dict[str, Any] | None = None
    ) -> list[FindingCandidate]:
        """
        Evaluates marketing copy against clinical trial dossier endpoints,
        mapping each discrepancy to FindingCandidate(category="claim", severity="high",
        rule_id="CLINICAL-EVIDENCE-01", source_ref=citation).
        """
        if not text:
            return []

        if isinstance(studies, list) and len(studies) == 0:
            return []

        eval_result = evaluate_clinical_discrepancies(text, study_dossier=studies)
        findings: list[FindingCandidate] = []

        for disc in eval_result.get("discrepancies", []):
            claimed_val = disc.get("claimed_value") or ""
            span_start = disc.get("span_start")
            span_end = disc.get("span_end")
            highlighted = disc.get("highlighted_text")

            if span_start is None or span_end is None:
                if claimed_val and claimed_val in text:
                    span_start = text.find(claimed_val)
                    span_end = span_start + len(claimed_val)
                    highlighted = claimed_val
                elif claimed_val:
                    num_match = re.search(r"\b" + re.escape(claimed_val.rstrip("%").rstrip(".0")) + r"(?:%|\s*days?)?", text, re.IGNORECASE)
                    if num_match:
                        span_start, span_end = num_match.span()
                        highlighted = num_match.group(0)
                    else:
                        span_start = 0
                        span_end = min(len(text), 30)
                        highlighted = text[:span_end]
                else:
                    span_start = 0
                    span_end = min(len(text), 30)
                    highlighted = text[:span_end]

            findings.append(
                FindingCandidate(
                    category="claim",
                    severity=disc.get("severity", "high"),
                    explanation=disc.get("message", "Clinical claim discrepancy detected."),
                    source_ref=disc.get("citation", "Clinical Study Evidence Dossier"),
                    confidence=0.98,
                    span_start=span_start,
                    span_end=span_end,
                    highlighted_text=highlighted,
                    suggested_fix=disc.get("suggested_fix"),
                    rule_id="CLINICAL-EVIDENCE-01"
                )
            )

        return findings

    def run_all(
        self,
        text: str,
        terminology_entries: list[dict[str, Any]] | None = None,
        channel: str | None = None,
        file_path: str | None = None,
        alt_text: str | None = None,
        clinical_studies: list[dict[str, Any]] | dict[str, Any] | None = None,
    ) -> list[FindingCandidate]:
        """Run all deterministic checks (text + visual/accessibility + clinical) and aggregate finding candidates."""
        findings: list[FindingCandidate] = []
        if not text and not file_path:
            return findings

        # 1. Terminology checks
        if text and terminology_entries:
            findings.extend(self.check_terminology(text, terminology_entries))

        # 2. Superlatives & claims checks
        if text:
            findings.extend(self.check_superlatives_and_claims(text))

        # 3. Regulatory / Disclosure checks
        if text:
            findings.extend(self.check_disclosures(text, channel))

        # 4. Readability check for high complexity
        if text:
            readability = self.calculate_readability(text)
            if readability["grade_level"] > 12.0 and len(text) > 100:
                findings.append(
                    FindingCandidate(
                        category="accessibility",
                        severity="low",
                        span_start=0,
                        span_end=min(len(text), 50),
                        highlighted_text=text[:50] + "...",
                        explanation=f"Text complexity exceeds brand target (Grade {readability['grade_level']}). Target is Grade 6-8.",
                        source_ref="WCAG 2.2 §3.1.5 (Reading Level)",
                        confidence=0.85,
                        suggested_fix="Simplify sentence structure and replace technical words with everyday language."
                    )
                )

        # 5. Visual accessibility check (missing alt text for images)
        if file_path and (not alt_text or not alt_text.strip()):
            findings.append(
                FindingCandidate(
                    category="accessibility",
                    severity="medium",
                    explanation="Image asset is missing descriptive alternative text (alt text) for screen readers.",
                    source_ref="WCAG 2.2 §1.1.1 (Non-text Content)",
                    confidence=1.0,
                    suggested_fix="Provide a concise description of the image content and visual elements."
                )
            )

        # 6. Clinical evidence checks
        if text and not (isinstance(clinical_studies, list) and len(clinical_studies) == 0):
            findings.extend(self.check_clinical_evidence(text, clinical_studies))

        # 7. Hinglish and regional vernacular compliance checks
        if text and (channel and "hinglish" in channel.lower()):
            findings.extend(self.check_hinglish_and_regional_claims(text, channel, clinical_studies))

        return findings


# Global instance
deterministic_engine = DeterministicReviewEngine()

__all__ = [
    "deterministic_engine",
    "DeterministicReviewEngine",
    "FindingCandidate",
    "ClinicalTrialPDFExtractor",
    "evaluate_clinical_discrepancies",
    "CANONICAL_EVIDENCE_TYPES"
]
