"""Tests for hallucination prevention system."""

import pytest
from src.ml.hallucination_prevention import HallucinationPrevention, ConfidenceLevel


@pytest.fixture
def hp():
    return HallucinationPrevention()


class TestConfidenceCheck:
    def test_image_confidence_cap(self, hp):
        report = hp.check_confidence(0.90, source_type="image")
        assert report.cap_applied is True
        assert report.capped_confidence == 0.65

    def test_xrf_higher_cap(self, hp):
        report = hp.check_confidence(0.90, source_type="xrf")
        assert report.capped_confidence == 0.85
        assert report.cap_applied is True

    def test_lab_no_cap(self, hp):
        report = hp.check_confidence(0.95, source_type="lab")
        assert report.capped_confidence == 0.95
        assert report.cap_applied is False

    def test_confidence_levels(self, hp):
        report = hp.check_confidence(0.10, source_type="image")
        assert report.level == ConfidenceLevel.VERY_LOW

        report = hp.check_confidence(0.40, source_type="image")
        assert report.level == ConfidenceLevel.LOW

        report = hp.check_confidence(0.60, source_type="image")
        assert report.level == ConfidenceLevel.HIGH  # capped at 0.65, which is HIGH


class TestConsistencyCheck:
    def test_consistent_agents(self, hp):
        check = hp.check_consistency({"a": "gold", "b": "gold", "c": "gold"})
        assert check.is_consistent is True
        assert check.agreement_ratio == 1.0

    def test_inconsistent_agents(self, hp):
        check = hp.check_consistency({"a": "gold", "b": "pyrite", "c": "gold"})
        assert check.is_consistent is True  # 66% agreement
        assert len(check.conflicts) == 1

    def test_no_predictions(self, hp):
        check = hp.check_consistency({})
        assert check.is_consistent is True


class TestDomainRules:
    def test_economic_mineral_always_flagged(self, hp):
        rules = hp.check_domain_rules("gold", 0.5, source_type="xrf")
        expert_rule = [r for r in rules if r.rule_name == "economic_mineral_expert"]
        assert len(expert_rule) == 1
        assert expert_rule[0].passed is False

    def test_non_economic_mineral(self, hp):
        rules = hp.check_domain_rules("quartz", 0.5, source_type="image")
        expert_rule = [r for r in rules if r.rule_name == "economic_mineral_expert"]
        assert len(expert_rule) == 0


class TestFullCheck:
    def test_safe_result(self, hp):
        report = hp.full_check("quartz", 0.60, source_type="image")
        assert report.overall_safe is True

    def test_economic_mineral_not_safe(self, hp):
        report = hp.full_check("gold", 0.50, source_type="image")
        # Gold is economic mineral — should have critical failures
        assert len(report.warnings) > 0
