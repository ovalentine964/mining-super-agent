"""Tests for agent system."""

import pytest
from src.agents.base import calibrate_confidence, ConfidenceLevel, ToolDefinition


def test_confidence_calibration():
    # High evidence, reliable source
    score = calibrate_confidence(0.9, evidence_count=5, source_reliability=0.9)
    assert 0.5 < score < 0.98

    # No evidence
    score = calibrate_confidence(0.5, evidence_count=0, source_reliability=0.5, method_limitation=0.3)
    assert score < 0.5

    # Never returns 0 or 1
    score = calibrate_confidence(0.0, evidence_count=0, source_reliability=0.0)
    assert score >= 0.05

    score = calibrate_confidence(1.0, evidence_count=100, source_reliability=1.0)
    assert score <= 0.98


def test_confidence_levels():
    assert ConfidenceLevel.from_score(0.1) == ConfidenceLevel.VERY_LOW
    assert ConfidenceLevel.from_score(0.4) == ConfidenceLevel.LOW
    assert ConfidenceLevel.from_score(0.6) == ConfidenceLevel.MODERATE
    assert ConfidenceLevel.from_score(0.8) == ConfidenceLevel.HIGH
    assert ConfidenceLevel.from_score(0.95) == ConfidenceLevel.VERY_HIGH


def test_tool_definition_to_openai():
    tool = ToolDefinition(
        name="test_tool",
        description="A test tool",
        parameters={"type": "object", "properties": {"x": {"type": "string"}}},
    )
    openai_format = tool.to_openai_function()
    assert openai_format["type"] == "function"
    assert openai_format["function"]["name"] == "test_tool"
