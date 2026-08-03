"""
Tests for financial tools — _npv, _irr, calculate_npv, estimate_value.
"""

import math
import pytest

from src.tools.financial import _npv, _irr, calculate_npv, estimate_value


# ── _npv() ──────────────────────────────────────────────────────────

class TestNPV:
    def test_npv_known_values(self):
        """NPV of [-1000, 500, 500, 500] at 10% should be ~243.43."""
        cash_flows = [-1000, 500, 500, 500]
        result = _npv(0.10, cash_flows)
        # Manual: -1000 + 500/1.1 + 500/1.21 + 500/1.331
        expected = -1000 + 500 / 1.1 + 500 / 1.21 + 500 / 1.331
        assert abs(result - expected) < 0.01

    def test_npv_zero_rate(self):
        """At 0% discount, NPV is sum of cash flows."""
        cash_flows = [-100, 50, 60, 70]
        result = _npv(0.0, cash_flows)
        assert result == 80.0

    def test_npv_all_zeros(self):
        """All zero cash flows → NPV = 0."""
        cash_flows = [0, 0, 0, 0]
        result = _npv(0.10, cash_flows)
        assert result == 0.0

    def test_npv_single_cash_flow(self):
        """Single negative cash flow at t=0."""
        cash_flows = [-500]
        result = _npv(0.05, cash_flows)
        assert result == -500.0

    def test_npv_high_discount_rate(self):
        """Very high discount rate should make future cash flows negligible."""
        cash_flows = [-1000, 500, 500]
        result = _npv(100.0, cash_flows)  # 10000% discount
        # At 100x discount: -1000 + 500/101 + 500/10201 ≈ -1000 + 4.95 + 0.049
        assert result < -990  # Almost all future value is gone


# ── _irr() ──────────────────────────────────────────────────────────

class TestIRR:
    def test_irr_known_values(self):
        """IRR of [-1000, 500, 500, 500] should be ~23.4%."""
        cash_flows = [-1000, 500, 500, 500]
        result = _irr(cash_flows)
        assert result is not None
        # Should be between 0.20 and 0.30
        assert 0.20 < result < 0.30

    def test_irr_simple_two_period(self):
        """IRR of [-100, 121] should be ~0.1 (10%)."""
        cash_flows = [-100, 121]
        result = _irr(cash_flows)
        assert result is not None
        assert abs(result - 0.21) < 0.01  # 121/100 - 1 = 0.21

    def test_irr_no_convergence_returns_none(self):
        """Cash flows that never cross zero NPV → None."""
        # All positive → NPV always positive in [-0.5, 5.0]
        cash_flows = [100, 200, 300]
        result = _irr(cash_flows, max_iter=50)
        assert result is None

    def test_irr_all_zeros(self):
        """All zeros → NPV is always 0, should converge immediately."""
        cash_flows = [0, 0, 0]
        result = _irr(cash_flows)
        # NPV = 0 at any rate → should find it
        assert result is not None

    def test_irr_negative_outflow_only(self):
        """Only negative cash flows → NPV always negative → None."""
        cash_flows = [-100, -200, -300]
        result = _irr(cash_flows, max_iter=50)
        assert result is None


# ── calculate_npv() ─────────────────────────────────────────────────

class TestCalculateNPV:
    @pytest.mark.asyncio
    async def test_returns_expected_structure(self):
        result = await calculate_npv(
            mineral="gold",
            annual_production_kg=100,
            price_per_kg=60000,  # ~$60k/kg gold
            capex=500000,
            opex_annual=100000,
            mine_life_years=10,
            discount_rate=0.15,
            recovery_rate=0.75,
        )
        # Check all expected keys
        expected_keys = [
            "mineral", "npv", "irr", "payback_years",
            "annual_revenue", "annual_profit", "capex", "opex_annual",
            "mine_life_years", "discount_rate", "recovery_rate",
            "sensitivity", "assumptions", "disclaimer", "disclaimer_en",
            "swahili_summary",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_npv_positive_for_profitable_project(self):
        result = await calculate_npv(
            mineral="gold",
            annual_production_kg=1000,
            price_per_kg=60000,
            capex=100000,
            opex_annual=10000,
            mine_life_years=10,
        )
        assert result["npv"] > 0

    @pytest.mark.asyncio
    async def test_npv_negative_for_bad_project(self):
        result = await calculate_npv(
            mineral="gravel",
            annual_production_kg=1,
            price_per_kg=10,
            capex=10000000,
            opex_annual=100000,
            mine_life_years=5,
        )
        assert result["npv"] < 0

    @pytest.mark.asyncio
    async def test_sensitivity_analysis_has_expected_keys(self):
        result = await calculate_npv(
            mineral="copper",
            annual_production_kg=500,
            price_per_kg=8,
            capex=200000,
            opex_annual=50000,
            mine_life_years=8,
        )
        sensitivity = result["sensitivity"]
        assert "price_-20%" in sensitivity
        assert "price_-10%" in sensitivity
        assert "price_0%" in sensitivity
        assert "price_10%" in sensitivity
        assert "price_20%" in sensitivity

    @pytest.mark.asyncio
    async def test_annual_revenue_calculation(self):
        result = await calculate_npv(
            mineral="gold",
            annual_production_kg=100,
            price_per_kg=60000,
            capex=0,
            opex_annual=0,
            recovery_rate=0.80,
        )
        # effective = 100 * 0.80 = 80 kg, revenue = 80 * 60000 = 4,800,000
        assert result["annual_revenue"] == 4800000.0

    @pytest.mark.asyncio
    async def test_disclaimer_present(self):
        result = await calculate_npv(
            mineral="gold",
            annual_production_kg=100,
            price_per_kg=60000,
            capex=500000,
            opex_annual=100000,
        )
        assert result["disclaimer"] != ""
        assert result["disclaimer_en"] != ""


# ── estimate_value() ────────────────────────────────────────────────

class TestEstimateValue:
    @pytest.mark.asyncio
    async def test_scales_by_confidence(self):
        """Effective kg = estimated_kg * confidence."""
        result = await estimate_value(
            mineral="gold",
            estimated_kg=1000,
            price_per_kg=60000,
            confidence=0.5,
        )
        assert result["effective_kg"] == 500.0
        assert result["confidence"] == 0.5

    @pytest.mark.asyncio
    async def test_gross_value_calculation(self):
        """gross_value = effective_kg * price_per_kg."""
        result = await estimate_value(
            mineral="copper",
            estimated_kg=500,
            price_per_kg=8,
            confidence=1.0,
        )
        assert result["gross_value_usd"] == 4000.0

    @pytest.mark.asyncio
    async def test_net_value_is_60_percent_of_gross(self):
        """Net value = gross_value * 0.6 (40% extraction costs)."""
        result = await estimate_value(
            mineral="silver",
            estimated_kg=100,
            price_per_kg=800,
            confidence=1.0,
        )
        assert result["net_value_usd"] == result["gross_value_usd"] * 0.6

    @pytest.mark.asyncio
    async def test_zero_confidence_gives_zero_value(self):
        result = await estimate_value(
            mineral="gold",
            estimated_kg=1000,
            price_per_kg=60000,
            confidence=0.0,
        )
        assert result["effective_kg"] == 0.0
        assert result["gross_value_usd"] == 0.0
        assert result["net_value_usd"] == 0.0

    @pytest.mark.asyncio
    async def test_full_confidence_gives_full_value(self):
        result = await estimate_value(
            mineral="gold",
            estimated_kg=100,
            price_per_kg=60000,
            confidence=1.0,
        )
        assert result["effective_kg"] == 100.0
        assert result["gross_value_usd"] == 6000000.0

    @pytest.mark.asyncio
    async def test_returns_expected_keys(self):
        result = await estimate_value(
            mineral="gold",
            estimated_kg=100,
            price_per_kg=60000,
            confidence=0.75,
        )
        expected_keys = [
            "mineral", "estimated_kg", "effective_kg", "confidence",
            "price_per_kg", "gross_value_usd", "gross_value_kes",
            "net_value_usd", "net_value_kes", "note", "disclaimer",
            "swahili_summary",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_kes_conversion(self):
        """KES should be approximately USD * 130."""
        result = await estimate_value(
            mineral="gold",
            estimated_kg=100,
            price_per_kg=60000,
            confidence=1.0,
        )
        assert abs(result["gross_value_kes"] - result["gross_value_usd"] * 130) < 1.0
