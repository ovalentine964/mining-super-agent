# Review 5: Tool Registry & Tools Verification

**Reviewer:** Review Council 5 — Tool Registry Reviewer  
**Date:** 2026-07-25  
**Scope:** `/mining-super-agent/src/tools/` — registry.py, schemas.py, all tool modules  
**Verdict:** ❌ **FAIL — Critical integration failures despite individual components being sound**

---

## Executive Summary

The individual components (registry.py, schemas.py, tool modules) are well-designed in isolation. However, **the integration between them is fundamentally broken.** Handler names registered in Python don't match YAML tool names, meaning the registry cannot route execution calls to actual tool implementations. Only **18 of 55 YAML tools (33%)** have working handlers. The claimed "55 tools, 27 handlers" is numerically accurate but misleading — most handlers are registered under names that don't correspond to any YAML tool.

---

## Claim-by-Claim Verification

### 1. Runtime Argument Validation via Pydantic

**Claim:** Runtime argument validation with Pydantic.  
**Verdict:** ⚠️ PARTIAL — Infrastructure exists but is incomplete.

**Evidence:**
- `registry.py` lines ~276-282: `execute()` method does check for `input_schema` and validates via `input_schema(**arguments)`. ✅
- Output validation also present (lines ~310-318). ✅
- **BUT:** Only **8 of 27 handlers** have input schemas registered:
  - `identify_mineral_from_photo`, `mineral_photo_id`, `xrf_analysis` (vision)
  - `query_mining_act`, `licensing_info` (legal)
  - `npv_calculator`, `value_estimator` (financial)
  - `generate_report` (reports)
- **Missing schemas for:** All geological, satellite, market, and quantum tool handlers.
- Runtime test confirms: `execute('get_commodity_price', {})` does NOT raise a validation error — it falls through to the handler which fails with a Python TypeError, not a Pydantic ValidationError.

```python
# Test result:
# get_commodity_price (no args) → handler error, NOT schema validation error
# get_commodity_price input_schema: None  ← schema not registered
```

### 2. YAML ↔ Python Name Matching

**Claim:** YAML ↔ Python name mismatches fixed.  
**Verdict:** ❌ **FAIL — 9 critical mismatches remain.**

**Evidence:** The `register_*_tools()` functions register handlers under names that DON'T match the YAML tool definitions. When `execute("query_sentinel2", ...)` is called, the registry looks for a handler named `"query_sentinel2"` — but it was registered as `"sentinel2_download"`.

| YAML Tool Name | Handler Registered As | Match? |
|---|---|---|
| `query_sentinel2` | `sentinel2_download` | ❌ |
| `run_geophysical_inversion` | `simpeg_inversion` | ❌ |
| `query_mindat` | `mindat_query` | ❌ |
| `query_geological_database` | `geological_database_query` | ❌ |
| `check_cloud_cover` | `cloud_cover_check` | ❌ |
| `identify_mineral_from_photo` | `identify_mineral_from_photo` | ✅ |
| `mineral_photo_id` | `mineral_photo_id` | ✅ (alias, not in YAML) |
| ... | ... | ... |

**9 handler names have NO matching YAML entry:**
`calculate_clay_ratio`, `calculate_iron_oxide_ratio`, `calculate_ndvi`, `cloud_cover_check`, `geological_database_query`, `mindat_query`, `mineral_photo_id`, `sentinel2_download`, `simpeg_inversion`

**37 of 55 YAML tools have NO handler registered** — they would fail at runtime with `ToolNotFoundError` or "No handler registered."

**Working tools (18 of 55):**
`alpha_vantage_price`, `classical_greedy_optimize`, `classical_mineral_classify`, `finnhub_price`, `gempy_3d_model`, `generate_report`, `get_commodity_price`, `get_price_history`, `identify_mineral_from_photo`, `licensing_info`, `npv_calculator`, `quantum_drill_optimize`, `quantum_mineral_classify`, `query_mining_act`, `usgs_mrdata_query`, `value_estimator`, `xrf_analysis`, `yfinance_price`

### 3. register_*_tools() in All 4 Missing Modules

**Claim:** register_*_tools() added to all 4 missing modules (vision, legal, financial, reports).  
**Verdict:** ✅ CONFIRMED for the 4 claimed modules.  
**BUT:** 3 additional modules also lack register functions.

**Evidence:**
| Module | Has register function? |
|---|---|
| `vision.py` | ✅ `register_vision_tools()` |
| `legal.py` | ✅ `register_legal_tools()` |
| `financial.py` | ✅ `register_financial_tools()` |
| `reports.py` | ✅ `register_report_tools()` |
| `geological.py` | ✅ `register_geological_tools()` |
| `satellite.py` | ✅ `register_satellite_tools()` |
| `market.py` | ✅ `register_market_tools()` |
| `quantum.py` | ✅ `register_quantum_tools()` |
| **community** (no module) | ❌ No module exists |
| **exploration** (no module) | ❌ No module exists |
| **qc** (no module) | ❌ No module exists |

The YAML defines 13 tools for community/exploration/qc domains that have NO Python implementation module at all. These are referenced in `tools.yaml` pointing to `src.agents.*` paths that don't exist.

### 4. schemas.py — Pydantic I/O Models

**Claim:** schemas.py created with all I/O schemas.  
**Verdict:** ✅ CONFIRMED — comprehensive and well-structured.

**Evidence:**
- `schemas.py` contains **32 Pydantic models** covering all tool domains.
- Geological: `GemPyInput/Output`, `SimPEGInput/Output`, `MindatInput/Output`, `USGSMRDSInput/Output`, `GeologicalDBInput/Output`
- Satellite: `Sentinel2Input/Output`, `NDVIInput`, `SpectralIndexOutput`, `CloudCoverInput/Output`
- Vision: `MineralPhotoInput/Output`, `XRFInput/Output`
- Market: `CommodityPriceInput/Output`, `PriceHistoryInput/Output`
- Legal: `MiningActInput/Output`, `LicensingInput/Output`
- Financial: `NPVInput/Output`, `ValueEstimateInput/Output`
- Quantum: `QuantumKernelInput/Output`, `QAOAInput/Output`, `ClassicalMineralClassifyInput/Output`, `GreedyOptimizeInput/Output`
- Reports: `ReportInput/Output`
- All schemas import cleanly: `from src.tools.schemas import *` → ✅

**Gap:** Schemas exist but aren't connected to most handlers. Only 8 of 27 handlers have schemas wired up.

### 5. Tests

**Claim:** Tests passing.  
**Verdict:** ⚠️ PARTIAL — 11/12 pass, 1 failure.

**Evidence:**
```
tests/test_quantum.py::TestQuantumConfig::test_default_config PASSED
tests/test_quantum.py::TestQuantumConfig::test_force_classical PASSED
tests/test_quantum.py::TestQuantumConfig::test_small_problem_classical PASSED
tests/test_quantum.py::TestQuantumConfig::test_available_backends PASSED
tests/test_quantum.py::TestClassicalFallback::test_kernel_classification PASSED
tests/test_quantum.py::TestClassicalFallback::test_qubo_optimization PASSED
tests/test_quantum.py::TestQAOAOptimizer::test_build_qubo_matrix PASSED
tests/test_quantum.py::TestBenchmarks::test_run_benchmarks FAILED  ← AttributeError
tests/test_tools_registry.py::test_tool_config_creation PASSED
tests/test_tools_registry.py::test_registry_register_config PASSED
tests/test_tools_registry.py::test_registry_list_tools PASSED
tests/test_tools_registry.py::test_registry_disabled_tool PASSED
```

**Failure:** `TestBenchmarks::test_run_benchmarks` — `QAOAOptimizer` has no `generate_random_problem` method. The benchmark code references a method that doesn't exist on the class.

**Missing test coverage:**
- No tests for tool handler registration
- No tests for YAML ↔ handler name matching
- No tests for Pydantic input/output validation in `execute()`
- No tests for any non-quantum tool handler
- No integration test that loads YAML + registers handlers + executes

---

## Additional Critical Issues Found

### BUG: `np.npv()` and `np.irr()` removed from NumPy

**File:** `src/tools/financial.py` lines ~85, ~89  
**Severity:** 🔴 CRITICAL — `calculate_npv` will crash at runtime.

```python
npv = np.npv(discount_rate, cash_flows)  # ❌ AttributeError: np.npv removed in NumPy 1.18+
irr = np.irr(cash_flows)                  # ❌ AttributeError: np.irr removed in NumPy 1.18+
```

NumPy 2.5.1 is installed. `np.npv` and `np.irr` were deprecated in NumPy 1.18 and removed. Must use `numpy_financial.npv()` / `numpy_financial.irr()` instead.

### BUG: Vision module imports non-existent ML modules

**File:** `src/tools/vision.py` lines ~71-72  
**Severity:** 🟡 MEDIUM — `identify_mineral_from_photo` will crash at runtime.

```python
from ..ml.mineral_classifier import MineralClassifier  # ❌ Module doesn't exist
from ..ml.clip_classifier import CLIPClassifier          # ❌ Module doesn't exist
```

These modules are not present in the codebase. The function will raise `ImportError` at call time.

### BUG: DeerFlow adapters reference non-existent functions

**File:** `src/tools/deerflow_tools.py`  
**Severity:** 🟡 MEDIUM — 26 DeerFlow tool classes reference functions that don't exist in the target modules.

Examples:
- `RunGemPyModelTool.func_name = "run_gempy_model"` → geological.py has `gempy_3d_model` (no `run_` prefix)
- `IdentifyMineralPhotoTool.func_name = "identify_mineral_photo"` → vision.py has `identify_mineral_from_photo`
- `CheckLicenseRequirementsTool.func_name = "check_license_requirements"` → legal.py has no such function
- `CalculateNPVIRRTool.func_name = "calculate_npv_irr"` → financial.py has `calculate_npv`

The DeerFlow adapter layer appears to be a stale parallel system that was never updated to match the actual tool implementations.

### ISSUE: `register_all_tools()` warns on every handler

When `register_all_tools()` is called without first loading YAML config, all 27 handler registrations produce `WARNING: Registering handler for unconfigured tool`. This is harmless but indicates the expected initialization order (YAML first, then handlers) isn't enforced or documented.

---

## Component Quality Assessment

| Component | Quality | Notes |
|---|---|---|
| `registry.py` | ✅ Good | Clean design, rate limiting, caching, fallback chains, Pydantic validation hooks |
| `schemas.py` | ✅ Good | Comprehensive 32 models, proper Field descriptions, all import cleanly |
| `geological.py` | ✅ Good | Clean async handlers, proper error handling, mock fallbacks |
| `satellite.py` | ✅ Good | Proper pystac-client integration, NDVI/clay/iron calculations |
| `market.py` | ✅ Good | Multi-provider fallback chain (yfinance→Finnhub→AlphaVantage), TTL caching |
| `quantum.py` | ✅ Good | PennyLane + Qiskit implementations with classical fallbacks |
| `vision.py` | ⚠️ Fair | Good safety rules (pyrite≠gold), but imports non-existent ML modules |
| `legal.py` | ✅ Good | Comprehensive Kenya Mining Act data |
| `financial.py` | ❌ Broken | `np.npv`/`np.irr` removed from NumPy — will crash |
| `reports.py` | ✅ Good | Clean PDF generation wrapper |
| `deerflow_tools.py` | ❌ Broken | Stale adapter layer, function names don't match actual implementations |
| **Integration** | ❌ Broken | YAML↔handler name mismatches make 67% of tools non-functional |

---

## Summary Scorecard

| Check | Result | Details |
|---|---|---|
| Pydantic validation in registry | ⚠️ PARTIAL | Infrastructure works, but only 8/27 handlers have schemas |
| YAML ↔ Python name match | ❌ FAIL | 9 mismatches; 37/55 YAML tools have no handler |
| register_*_tools() in 4 modules | ✅ PASS | vision, legal, financial, reports all have register functions |
| schemas.py complete | ✅ PASS | 32 models, all import cleanly |
| Tests passing | ⚠️ PARTIAL | 11/12 pass; 1 failure (missing method); no integration tests |
| Handler count (27) | ✅ ACCURATE | 27 unique handler names registered |
| YAML tool count (55) | ✅ ACCURATE | 55 tools loaded from YAML |
| Tools actually executable end-to-end | ❌ FAIL | ~18/55 (33%) work; rest fail at handler lookup or runtime |

---

## Required Fixes

1. **[CRITICAL]** Align all `register_*_tools()` handler names to match YAML tool names (or vice versa). 9 mismatches must be resolved.
2. **[CRITICAL]** Replace `np.npv()`/`np.irr()` with `numpy_financial` equivalents in `financial.py`.
3. **[HIGH]** Wire up Pydantic input schemas to ALL handlers (currently only 8/27).
4. **[HIGH]** Create tool modules for community, exploration, and qc domains (13 YAML tools with no implementation).
5. **[MEDIUM]** Fix or remove stale `deerflow_tools.py` adapter layer.
6. **[MEDIUM]** Create `src/ml/mineral_classifier.py` and `src/ml/clip_classifier.py` or make vision.py gracefully handle missing ML deps.
7. **[MEDIUM]** Fix `QAOAOptimizer.generate_random_problem` missing method in benchmarks.
8. **[LOW]** Add integration tests: YAML load → handler registration → execution → validation.
