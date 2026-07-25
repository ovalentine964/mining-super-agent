"""
Hallucination Prevention — 5-Layer Defense System
==================================================
Layer 1: Structured confidence output (calibrated, not hardcoded)
Layer 2: Multi-agent consistency checks
Layer 3: NLI-based evidence grounding
Layer 4: Chain-of-Verification
Layer 5: Domain-specific rules

CRITICAL: Image-based mineral ID capped at 65% confidence.
          Economic minerals ALWAYS require expert review.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ── Constants ──────────────────────────────────────────────────────────────────
IMAGE_ID_MAX_CONFIDENCE = 0.65
ECONOMIC_MINERALS = {"gold", "copper", "galena", "sphalerite", "pyrite"}
MIN_CONFIDENCE_FOR_RESPONSE = 0.15
EXPERT_REVIEW_THRESHOLD = 0.50
NLI_ENTAILMENT_THRESHOLD = 0.70


class ConfidenceLevel(Enum):
    """Structured confidence levels."""
    VERY_LOW = "very_low"      # < 15%
    LOW = "low"                # 15-30%
    MODERATE = "moderate"      # 30-50%
    HIGH = "high"              # 50-75%
    VERY_HIGH = "very_high"    # > 75% (only with lab data)


class VerificationStatus(Enum):
    """Chain-of-verification status."""
    PASSES = "passes"
    PARTIALLY_VERIFIED = "partially_verified"
    FAILS = "fails"
    NOT_VERIFIABLE = "not_verifiable"


@dataclass
class ConfidenceReport:
    """Layer 1: Structured confidence output."""
    raw_confidence: float
    calibrated_confidence: float
    capped_confidence: float
    level: ConfidenceLevel
    source_type: str              # "image", "xrf", "spectroscopy", "lab"
    cap_applied: bool
    cap_reason: Optional[str] = None


@dataclass
class ConsistencyCheck:
    """Layer 2: Multi-agent consistency result."""
    agent_predictions: Dict[str, str]   # agent_name → predicted mineral
    is_consistent: bool
    conflicts: List[str]
    agreement_ratio: float               # 0.0 to 1.0


@dataclass
class NLIBreakdown:
    """Layer 3: NLI evidence grounding."""
    claim: str
    evidence: str
    entailment_score: float               # 0.0 to 1.0
    contradiction_score: float            # 0.0 to 1.0
    neutral_score: float                  # 0.0 to 1.0
    is_grounded: bool


@dataclass
class VerificationChain:
    """Layer 4: Chain-of-Verification."""
    original_claim: str
    sub_questions: List[str]
    sub_answers: List[str]
    verification_status: VerificationStatus
    failed_checks: List[str]


@dataclass
class DomainRuleResult:
    """Layer 5: Domain rule check."""
    rule_name: str
    passed: bool
    message: str
    severity: str   # "info", "warning", "critical"


@dataclass
class HallucinationReport:
    """Complete 5-layer hallucination prevention report."""
    confidence_report: ConfidenceReport
    consistency_check: Optional[ConsistencyCheck]
    nli_results: List[NLIBreakdown]
    verification_chain: Optional[VerificationChain]
    domain_rules: List[DomainRuleResult]
    overall_safe: bool
    warnings: List[str]
    recommendations: List[str]

    def to_dict(self) -> dict:
        return {
            "confidence": {
                "raw": self.confidence_report.raw_confidence,
                "calibrated": self.confidence_report.calibrated_confidence,
                "capped": self.confidence_report.capped_confidence,
                "level": self.confidence_report.level.value,
                "source_type": self.confidence_report.source_type,
                "cap_applied": self.confidence_report.cap_applied,
            },
            "consistency": {
                "is_consistent": self.consistency_check.is_consistent if self.consistency_check else None,
                "agreement_ratio": self.consistency_check.agreement_ratio if self.consistency_check else None,
                "conflicts": self.consistency_check.conflicts if self.consistency_check else [],
            },
            "nli_grounded": all(r.is_grounded for r in self.nli_results) if self.nli_results else None,
            "verification": self.verification_chain.verification_status.value if self.verification_chain else None,
            "domain_rules_passed": all(r.passed for r in self.domain_rules),
            "overall_safe": self.overall_safe,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
        }


class HallucinationPrevention:
    """
    5-layer hallucination prevention system for mining AI.

    Every mineral identification goes through all 5 layers before
    being presented to the user.
    """

    def __init__(self, nli_model_name: Optional[str] = None):
        self.nli_model_name = nli_model_name or "cross-encoder/nli-deberta-v3-base"
        self._nli_model = None
        self._nli_tokenizer = None

    # ── Layer 1: Structured Confidence ──────────────────────────────────────

    def check_confidence(
        self,
        raw_confidence: float,
        source_type: str = "image",
        mineral: str = "",
    ) -> ConfidenceReport:
        """
        Layer 1: Structure and cap confidence based on source type.

        Rules:
        - Image-only: capped at 65%
        - XRF data: capped at 85%
        - Lab analysis: up to 99%
        """
        cap = IMAGE_ID_MAX_CONFIDENCE
        cap_reason = None

        if source_type == "xrf":
            cap = 0.85
            cap_reason = "XRF data provides elemental composition but not mineral structure"
        elif source_type == "spectroscopy":
            cap = 0.90
            cap_reason = "Spectroscopy provides mineral identification with high confidence"
        elif source_type == "lab":
            cap = 0.99
        elif source_type == "image":
            cap = IMAGE_ID_MAX_CONFIDENCE
            cap_reason = "Image-only identification cannot exceed 65% confidence"

        capped = min(raw_confidence, cap)
        cap_applied = capped < raw_confidence

        # Determine confidence level
        if capped < 0.15:
            level = ConfidenceLevel.VERY_LOW
        elif capped < 0.30:
            level = ConfidenceLevel.LOW
        elif capped < 0.50:
            level = ConfidenceLevel.MODERATE
        elif capped < 0.75:
            level = ConfidenceLevel.HIGH
        else:
            level = ConfidenceLevel.VERY_HIGH

        return ConfidenceReport(
            raw_confidence=raw_confidence,
            calibrated_confidence=raw_confidence,  # Actual calibration happens in the model
            capped_confidence=capped,
            level=level,
            source_type=source_type,
            cap_applied=cap_applied,
            cap_reason=cap_reason,
        )

    # ── Layer 2: Multi-Agent Consistency ────────────────────────────────────

    def check_consistency(
        self,
        predictions: Dict[str, str],
        confidences: Optional[Dict[str, float]] = None,
    ) -> ConsistencyCheck:
        """
        Layer 2: Check if multiple agents/models agree on identification.

        Args:
            predictions: {agent_name: predicted_mineral}
            confidences: {agent_name: confidence_score}
        """
        if not predictions:
            return ConsistencyCheck(
                agent_predictions=predictions,
                is_consistent=True,
                conflicts=[],
                agreement_ratio=1.0,
            )

        # Count votes
        from collections import Counter
        votes = Counter(predictions.values())
        most_common, most_count = votes.most_common(1)[0]
        agreement_ratio = most_count / len(predictions)

        # Identify conflicts
        conflicts = []
        for agent, pred in predictions.items():
            if pred != most_common:
                conflicts.append(
                    f"{agent} predicted '{pred}' but majority says '{most_common}'"
                )

        is_consistent = agreement_ratio >= 0.6  # 60% agreement threshold

        return ConsistencyCheck(
            agent_predictions=predictions,
            is_consistent=is_consistent,
            conflicts=conflicts,
            agreement_ratio=agreement_ratio,
        )

    # ── Layer 3: NLI Evidence Grounding ─────────────────────────────────────

    def check_nli_grounding(
        self,
        claim: str,
        evidence: str,
    ) -> NLIBreakdown:
        """
        Layer 3: Check if a claim is grounded in evidence using NLI.
        Uses a cross-encoder NLI model to verify entailment.
        """
        try:
            return self._run_nli(claim, evidence)
        except Exception as exc:
            logger.warning("NLI check failed: %s", exc)
            # Conservative fallback: assume not grounded
            return NLIBreakdown(
                claim=claim,
                evidence=evidence,
                entailment_score=0.0,
                contradiction_score=0.0,
                neutral_score=1.0,
                is_grounded=False,
            )

    def _run_nli(self, claim: str, evidence: str) -> NLIBreakdown:
        """Run NLI model on claim-evidence pair."""
        if self._nli_model is None:
            self._load_nli_model()

        import torch

        inputs = self._nli_tokenizer(
            evidence, claim,
            padding=True, truncation=True,
            max_length=512, return_tensors="pt",
        )

        with torch.no_grad():
            outputs = self._nli_model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1).squeeze().numpy()

        # DeBERTa NLI: [contradiction, neutral, entailment]
        if len(probs) == 3:
            contradiction, neutral, entailment = probs
        else:
            # Binary NLI
            entailment = probs[1]
            contradiction = probs[0]
            neutral = 0.0

        is_grounded = entailment >= NLI_ENTAILMENT_THRESHOLD

        return NLIBreakdown(
            claim=claim,
            evidence=evidence,
            entailment_score=float(entailment),
            contradiction_score=float(contradiction),
            neutral_score=float(neutral),
            is_grounded=is_grounded,
        )

    def _load_nli_model(self):
        """Lazy-load NLI model."""
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Loading NLI model: %s", self.nli_model_name)

        self._nli_tokenizer = AutoTokenizer.from_pretrained(self.nli_model_name)
        self._nli_model = AutoModelForSequenceClassification.from_pretrained(
            self.nli_model_name
        ).to(device)
        self._nli_model.eval()

    # ── Layer 4: Chain-of-Verification ──────────────────────────────────────

    def chain_of_verification(
        self,
        mineral: str,
        confidence: float,
        evidence: str = "",
        image_context: str = "",
    ) -> VerificationChain:
        """
        Layer 4: Generate and answer verification sub-questions.

        Creates specific verification questions and checks each one.
        """
        claim = f"The mineral is {mineral} (confidence: {confidence:.1%})"

        # Generate verification questions based on the mineral
        sub_questions = self._generate_verification_questions(mineral, confidence)
        sub_answers = []
        failed_checks = []

        for question in sub_questions:
            answer = self._answer_verification_question(
                question, mineral, confidence, evidence, image_context
            )
            sub_answers.append(answer)

            if answer.startswith("NO") or answer.startswith("UNCERTAIN"):
                failed_checks.append(f"Q: {question} → A: {answer}")

        # Determine overall verification status
        if not failed_checks:
            status = VerificationStatus.PASSES
        elif len(failed_checks) < len(sub_questions) / 2:
            status = VerificationStatus.PARTIALLY_VERIFIED
        else:
            status = VerificationStatus.FAILS

        return VerificationChain(
            original_claim=claim,
            sub_questions=sub_questions,
            sub_answers=sub_answers,
            verification_status=status,
            failed_checks=failed_checks,
        )

    def _generate_verification_questions(self, mineral: str, confidence: float) -> List[str]:
        """Generate mineral-specific verification questions."""
        questions = [
            f"Does the described color match known {mineral} samples?",
            f"Is the described luster consistent with {mineral}?",
            f"Are the crystal habits described consistent with {mineral}?",
        ]

        # Add look-alike specific questions
        if mineral == "gold":
            questions.extend([
                "Could this be pyrite (fool's gold) instead of gold?",
                "Has a streak test been performed? Gold has a golden streak, pyrite has black.",
                "Is the hardness consistent with gold (2.5-3 Mohs) rather than pyrite (6-6.5)?",
            ])
        elif mineral == "pyrite":
            questions.extend([
                "Is the cubic crystal form present, distinguishing it from gold?",
                "Does the sample have a metallic luster with brass-yellow color?",
            ])
        elif mineral in {"chalcopyrite", "pyrite"}:
            questions.append(
                "Can chalcopyrite be distinguished from pyrite by its deeper yellow and iridescent tarnish?"
            )

        if confidence > IMAGE_ID_MAX_CONFIDENCE:
            questions.append(
                f"Is the confidence ({confidence:.1%}) justified without laboratory analysis?"
            )

        return questions

    def _answer_verification_question(
        self,
        question: str,
        mineral: str,
        confidence: float,
        evidence: str,
        image_context: str,
    ) -> str:
        """
        Answer a verification question based on available information.
        Returns: "YES", "NO", "UNCERTAIN", or "NOT_VERIFIABLE"
        """
        question_lower = question.lower()

        # If confidence is very low, most answers are uncertain
        if confidence < MIN_CONFIDENCE_FOR_RESPONSE:
            return "UNCERTAIN — Confidence too low for reliable verification"

        # Pyrite vs gold checks
        if "pyrite" in question_lower and "gold" in question_lower:
            if mineral == "gold" and confidence < 0.5:
                return "NO — Cannot reliably distinguish gold from pyrite at this confidence level"
            return "NOT_VERIFIABLE — Physical testing required"

        # Confidence justification
        if "confidence" in question_lower and "justified" in question_lower:
            if confidence > IMAGE_ID_MAX_CONFIDENCE:
                return "NO — Confidence exceeds image-only cap of 65%"
            return "YES — Confidence within calibrated range"

        # If we have evidence, check against it
        if evidence:
            # Simple keyword matching for basic verification
            mineral_keywords = {mineral.lower()}
            if any(kw in evidence.lower() for kw in mineral_keywords):
                return "YES — Supported by evidence"
            return "UNCERTAIN — Evidence does not clearly confirm or deny"

        return "NOT_VERIFIABLE — Insufficient information for verification"

    # ── Layer 5: Domain-Specific Rules ──────────────────────────────────────

    def check_domain_rules(
        self,
        mineral: str,
        confidence: float,
        source_type: str = "image",
        has_xrf: bool = False,
        has_lab: bool = False,
        location: Optional[str] = None,
    ) -> List[DomainRuleResult]:
        """
        Layer 5: Apply domain-specific safety rules.

        Rules:
        1. Image ID confidence capped at 65%
        2. Economic minerals require expert review
        3. Gold requires physical verification
        4. High-value minerals need multiple data sources
        5. Location context should be provided
        """
        results = []

        # Rule 1: Image ID cap
        if source_type == "image" and confidence > IMAGE_ID_MAX_CONFIDENCE:
            results.append(DomainRuleResult(
                rule_name="image_confidence_cap",
                passed=False,
                message=f"Image-only confidence ({confidence:.1%}) exceeds {IMAGE_ID_MAX_CONFIDENCE:.0%} cap. "
                        f"Must be adjusted.",
                severity="critical",
            ))
        else:
            results.append(DomainRuleResult(
                rule_name="image_confidence_cap",
                passed=True,
                message="Confidence within acceptable range",
                severity="info",
            ))

        # Rule 2: Economic minerals need expert
        if mineral.lower() in ECONOMIC_MINERALS:
            results.append(DomainRuleResult(
                rule_name="economic_mineral_expert_review",
                passed=False,  # Always triggers
                message=f"{mineral.upper()} is an economic mineral. "
                        f"Professional geological assessment required before any decisions.",
                severity="critical",
            ))

        # Rule 3: Gold requires physical verification
        if mineral.lower() == "gold" and not has_xrf and not has_lab:
            results.append(DomainRuleResult(
                rule_name="gold_physical_verification",
                passed=False,
                message="Gold identification from images alone is unreliable. "
                        "Mandatory: streak test, acid test, XRF analysis.",
                severity="critical",
            ))

        # Rule 4: High-value minerals need multiple sources
        if mineral.lower() in {"gold", "copper", "galena"}:
            data_sources = sum([source_type == "image", has_xrf, has_lab])
            if data_sources < 2:
                results.append(DomainRuleResult(
                    rule_name="multiple_sources_required",
                    passed=False,
                    message=f"{mineral.upper()} valuation requires multiple independent data sources. "
                            f"Currently have: {data_sources}/3",
                    severity="warning",
                ))

        # Rule 5: Location context
        if not location and mineral.lower() in ECONOMIC_MINERALS:
            results.append(DomainRuleResult(
                rule_name="location_context",
                passed=False,
                message="Location context missing. Geological context is essential for "
                        "mineral identification in the Kenyan mining context.",
                severity="warning",
            ))

        return results

    # ── Full Pipeline ───────────────────────────────────────────────────────

    def full_check(
        self,
        mineral: str,
        confidence: float,
        source_type: str = "image",
        evidence: str = "",
        image_context: str = "",
        agent_predictions: Optional[Dict[str, str]] = None,
        has_xrf: bool = False,
        has_lab: bool = False,
        location: Optional[str] = None,
    ) -> HallucinationReport:
        """
        Run all 5 layers of hallucination prevention.

        Returns a comprehensive report with warnings and recommendations.
        """
        warnings = []
        recommendations = []

        # Layer 1: Confidence
        conf_report = self.check_confidence(confidence, source_type, mineral)
        if conf_report.cap_applied:
            warnings.append(
                f"Confidence capped from {conf_report.raw_confidence:.1%} to "
                f"{conf_report.capped_confidence:.1%} ({conf_report.cap_reason})"
            )

        # Layer 2: Consistency
        consistency = None
        if agent_predictions:
            consistency = self.check_consistency(agent_predictions)
            if not consistency.is_consistent:
                warnings.append(
                    f"Agent disagreement: {len(consistency.conflicts)} conflicts. "
                    f"Agreement ratio: {consistency.agreement_ratio:.0%}"
                )
                recommendations.append("Review conflicting agent predictions before presenting result")

        # Layer 3: NLI grounding
        nli_results = []
        if evidence:
            claim = f"The mineral sample is {mineral}"
            nli = self.check_nli_grounding(claim, evidence)
            nli_results.append(nli)
            if not nli.is_grounded:
                warnings.append(
                    f"Claim not grounded in evidence. Entailment: {nli.entailment_score:.1%}"
                )
                recommendations.append("Provide additional evidence or lower confidence")

        # Layer 4: Verification chain
        verification = self.chain_of_verification(
            mineral, conf_report.capped_confidence, evidence, image_context
        )
        if verification.failed_checks:
            warnings.append(
                f"Verification chain has {len(verification.failed_checks)} failures"
            )
            for fc in verification.failed_checks:
                warnings.append(f"  - {fc}")

        # Layer 5: Domain rules
        domain_rules = self.check_domain_rules(
            mineral, conf_report.capped_confidence, source_type,
            has_xrf, has_lab, location,
        )
        critical_failures = [r for r in domain_rules if not r.passed and r.severity == "critical"]
        for rule in critical_failures:
            warnings.append(f"DOMAIN RULE [{rule.rule_name}]: {rule.message}")

        # Overall safety assessment
        overall_safe = (
            not critical_failures
            and conf_report.capped_confidence >= MIN_CONFIDENCE_FOR_RESPONSE
            and (verification.verification_status != VerificationStatus.FAILS)
        )

        if not overall_safe:
            recommendations.append(
                "Result should NOT be presented as a reliable identification. "
                "Escalate to human expert."
            )

        return HallucinationReport(
            confidence_report=conf_report,
            consistency_check=consistency,
            nli_results=nli_results,
            verification_chain=verification,
            domain_rules=domain_rules,
            overall_safe=overall_safe,
            warnings=warnings,
            recommendations=recommendations,
        )
