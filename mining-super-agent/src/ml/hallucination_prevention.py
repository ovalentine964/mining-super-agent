"""
5-Layer Hallucination Prevention System.
Layer 1: Structured confidence output
Layer 2: Multi-agent consistency checks
Layer 3: NLI-based evidence grounding
Layer 4: Chain-of-Verification
Layer 5: Domain-specific rules
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

IMAGE_ID_MAX_CONFIDENCE = 0.65
ECONOMIC_MINERALS = {"gold", "copper", "galena", "sphalerite", "pyrite"}
MIN_CONFIDENCE_FOR_RESPONSE = 0.15


class ConfidenceLevel(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class VerificationStatus(Enum):
    PASSES = "passes"
    PARTIALLY_VERIFIED = "partially_verified"
    FAILS = "fails"
    NOT_VERIFIABLE = "not_verifiable"


@dataclass
class ConfidenceReport:
    raw_confidence: float
    calibrated_confidence: float
    capped_confidence: float
    level: ConfidenceLevel
    source_type: str
    cap_applied: bool
    cap_reason: Optional[str] = None


@dataclass
class ConsistencyCheck:
    agent_predictions: Dict[str, str]
    is_consistent: bool
    conflicts: List[str]
    agreement_ratio: float


@dataclass
class NLIBreakdown:
    claim: str
    evidence: str
    entailment_score: float
    contradiction_score: float
    neutral_score: float
    is_grounded: bool


@dataclass
class VerificationChain:
    original_claim: str
    sub_questions: List[str]
    sub_answers: List[str]
    verification_status: VerificationStatus
    failed_checks: List[str]


@dataclass
class DomainRuleResult:
    rule_name: str
    passed: bool
    message: str
    severity: str


@dataclass
class HallucinationReport:
    confidence_report: ConfidenceReport
    consistency_check: Optional[ConsistencyCheck]
    nli_results: List[NLIBreakdown]
    verification_chain: Optional[VerificationChain]
    domain_rules: List[DomainRuleResult]
    overall_safe: bool
    warnings: List[str]
    recommendations: List[str]


class HallucinationPrevention:
    """5-layer hallucination prevention for mining AI."""

    def __init__(self):
        self._nli_model = None
        self._nli_tokenizer = None

    def check_confidence(self, raw_confidence: float, source_type: str = "image", mineral: str = "") -> ConfidenceReport:
        caps = {"image": 0.65, "xrf": 0.85, "spectroscopy": 0.90, "lab": 0.99}
        cap = caps.get(source_type, 0.65)
        cap_reason = f"{source_type}-only identification cannot exceed {cap:.0%} confidence" if source_type != "lab" else None
        capped = min(raw_confidence, cap)
        cap_applied = capped < raw_confidence

        if capped < 0.15: level = ConfidenceLevel.VERY_LOW
        elif capped < 0.30: level = ConfidenceLevel.LOW
        elif capped < 0.50: level = ConfidenceLevel.MODERATE
        elif capped < 0.75: level = ConfidenceLevel.HIGH
        else: level = ConfidenceLevel.VERY_HIGH

        return ConfidenceReport(
            raw_confidence=raw_confidence, calibrated_confidence=raw_confidence,
            capped_confidence=capped, level=level, source_type=source_type,
            cap_applied=cap_applied, cap_reason=cap_reason,
        )

    def check_consistency(self, predictions: Dict[str, str]) -> ConsistencyCheck:
        if not predictions:
            return ConsistencyCheck(agent_predictions=predictions, is_consistent=True, conflicts=[], agreement_ratio=1.0)

        from collections import Counter
        votes = Counter(predictions.values())
        most_common, most_count = votes.most_common(1)[0]
        agreement_ratio = most_count / len(predictions)
        conflicts = [f"{a} predicted '{p}' but majority says '{most_common}'" for a, p in predictions.items() if p != most_common]

        return ConsistencyCheck(
            agent_predictions=predictions, is_consistent=agreement_ratio >= 0.6,
            conflicts=conflicts, agreement_ratio=agreement_ratio,
        )

    def check_nli_grounding(self, claim: str, evidence: str) -> NLIBreakdown:
        try:
            return self._run_nli(claim, evidence)
        except Exception as exc:
            logger.warning("NLI check failed: %s", exc)
            return NLIBreakdown(
                claim=claim, evidence=evidence, entailment_score=0.0,
                contradiction_score=0.0, neutral_score=1.0, is_grounded=False,
            )

    def _run_nli(self, claim: str, evidence: str) -> NLIBreakdown:
        if self._nli_model is None:
            self._load_nli_model()

        import torch
        inputs = self._nli_tokenizer(evidence, claim, padding=True, truncation=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            outputs = self._nli_model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1).squeeze().numpy()

        if len(probs) == 3:
            contradiction, neutral, entailment = probs
        else:
            entailment, contradiction, neutral = probs[1], probs[0], 0.0

        return NLIBreakdown(
            claim=claim, evidence=evidence, entailment_score=float(entailment),
            contradiction_score=float(contradiction), neutral_score=float(neutral),
            is_grounded=float(entailment) >= 0.70,
        )

    def _load_nli_model(self):
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self._nli_tokenizer = AutoTokenizer.from_pretrained("cross-encoder/nli-deberta-v3-base")
        self._nli_model = AutoModelForSequenceClassification.from_pretrained("cross-encoder/nli-deberta-v3-base").to(device)
        self._nli_model.eval()

    def chain_of_verification(self, mineral: str, confidence: float, evidence: str = "") -> VerificationChain:
        claim = f"The mineral is {mineral} (confidence: {confidence:.1%})"
        sub_questions = [
            f"Does the described color match known {mineral} samples?",
            f"Is the described luster consistent with {mineral}?",
        ]
        if mineral == "gold":
            sub_questions.append("Could this be pyrite instead of gold?")

        sub_answers = []
        failed_checks = []
        for q in sub_questions:
            answer = "NOT_VERIFIABLE — Physical testing required" if "pyrite" in q.lower() else "NOT_VERIFIABLE — Insufficient information"
            sub_answers.append(answer)
            if answer.startswith("NO") or answer.startswith("UNCERTAIN"):
                failed_checks.append(f"Q: {q} → A: {answer}")

        status = VerificationStatus.PASSES if not failed_checks else (
            VerificationStatus.PARTIALLY_VERIFIED if len(failed_checks) < len(sub_questions) / 2
            else VerificationStatus.FAILS
        )
        return VerificationChain(original_claim=claim, sub_questions=sub_questions, sub_answers=sub_answers, verification_status=status, failed_checks=failed_checks)

    def check_domain_rules(self, mineral: str, confidence: float, source_type: str = "image") -> List[DomainRuleResult]:
        results = []
        if source_type == "image" and confidence > IMAGE_ID_MAX_CONFIDENCE:
            results.append(DomainRuleResult(rule_name="image_confidence_cap", passed=False, message=f"Confidence {confidence:.1%} exceeds 65% cap", severity="critical"))
        else:
            results.append(DomainRuleResult(rule_name="image_confidence_cap", passed=True, message="OK", severity="info"))

        if mineral.lower() in ECONOMIC_MINERALS:
            results.append(DomainRuleResult(rule_name="economic_mineral_expert", passed=False, message=f"{mineral.upper()} requires expert review", severity="critical"))

        return results

    def full_check(self, mineral: str, confidence: float, source_type: str = "image", evidence: str = "", agent_predictions: Optional[Dict[str, str]] = None) -> HallucinationReport:
        warnings, recommendations = [], []

        conf_report = self.check_confidence(confidence, source_type, mineral)
        if conf_report.cap_applied:
            warnings.append(f"Confidence capped from {conf_report.raw_confidence:.1%} to {conf_report.capped_confidence:.1%}")

        consistency = None
        if agent_predictions:
            consistency = self.check_consistency(agent_predictions)
            if not consistency.is_consistent:
                warnings.append(f"Agent disagreement: {len(consistency.conflicts)} conflicts")

        nli_results = []
        if evidence:
            nli = self.check_nli_grounding(f"The mineral sample is {mineral}", evidence)
            nli_results.append(nli)
            if not nli.is_grounded:
                warnings.append("Claim not grounded in evidence")

        verification = self.chain_of_verification(mineral, conf_report.capped_confidence, evidence)
        domain_rules = self.check_domain_rules(mineral, conf_report.capped_confidence, source_type)
        critical_failures = [r for r in domain_rules if not r.passed and r.severity == "critical"]

        overall_safe = not critical_failures and conf_report.capped_confidence >= MIN_CONFIDENCE_FOR_RESPONSE

        return HallucinationReport(
            confidence_report=conf_report, consistency_check=consistency,
            nli_results=nli_results, verification_chain=verification,
            domain_rules=domain_rules, overall_safe=overall_safe,
            warnings=warnings, recommendations=recommendations,
        )
