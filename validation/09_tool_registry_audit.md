# 09 — Tool Registry Audit Report

**Auditor:** Validation Council Member 9 — Tool Registry Auditor  
**Date:** 2026-07-25  
**Target:** `/mining-super-agent/src/tools/`  
**Verdict:** ⚠️ PASS WITH WARNINGS (7/7 checks, 3 warnings)

---

## Executive Summary

The tool registry is a well-designed plug-and-play system with YAML configuration, per-tool rate limiting, TTL caching, fallback chains, and Pydantic-validated registry config. Tools are correctly implemented as standalone async functions (not agent classes). However, there are gaps in tool handler registration completeness and tool I/O Pydantic validation.

---

## 1. Registry — YAML-Configured? Auto-Discovery?

**Status: ✅ PASS**

| Aspect | Implementation | Quality |
|--------|---------------|---------|
| YAML config | `src/config/tools.yaml` — 50+ tool definitions | Excellent |
| Auto-discovery | `ToolRegistry.load_from_yaml()` parses and registers all tools | ✅ |
| Config schema | `ToolConfig(BaseModel)` with rate_limit, cache, fallback, permissions | ✅ |
| Dynamic registration | `register_handler()` for runtime handler binding | ✅ |
| Tool listing | `list_tools()`, `get_all_definitions()`, `get_tools_for_agent()` | ✅ |

**Evidence:**
- `registry.py` line 223: `load_from_yaml()` reads YAML, creates `ToolConfig` per tool, instantiates rate limiters and cache managers automatically.
- `main.py` `_load_tool_configs()` calls `load_from_yaml(str(tools_yaml))` at startup.
- YAML contains 50+ tools across all domains with structured config per tool.

**Strengths:**
- Clean separation: YAML defines _what_ (config), Python defines _how_ (handler).
- Pydantic `ToolConfig` model validates YAML structure at parse time.
- `ToolDefinition` model exposes only the fields agents need (name, description, parameters, permissions, timeout).

---

## 2. Tools as Functions — NOT Agent Classes?

**Status: ✅ PASS**

All 8 tool modules define **standalone async functions**, not agent classes:

| Module | Functions | Pattern |
|--------|-----------|---------|
| `geological.py` | `gempy_3d_model`, `simpeg_inversion`, `mindat_query`, `usgs_mrdata_query`, `geological_database_query` | `async def fn(**kwargs) → dict` ✅ |
| `satellite.py` | `sentinel2_download`, `calculate_ndvi`, `calculate_clay_ratio`, `calculate_iron_oxide_ratio`, `cloud_cover_check` | `async def fn(**kwargs) → dict` ✅ |
| `vision.py` | `identify_mineral_from_photo`, `analyze_xrf` | `async def fn(**kwargs) → dict` ✅ |
| `market.py` | `yfinance_price`, `finnhub_price`, `alpha_vantage_price`, `get_commodity_price_chain`, `price_history` | `async def fn(**kwargs) → dict` ✅ |
| `legal.py` | `query_mining_act`, `get_licensing_info` | `async def fn(**kwargs) → dict` ✅ |
| `financial.py` | `calculate_npv`, `estimate_value` | `async def fn(**kwargs) → dict` ✅ |
| `quantum.py` | `pennylane_quantum_kernel`, `qiskit_qaoa_optimize`, `classical_mineral_classify`, `classical_greedy_optimize` | `async def fn(**kwargs) → dict` ✅ |
| `reports.py` | `generate_pdf` | `async def fn(**kwargs) → dict` ✅ |

**No agent classes found in tools/ directory.** Architecture doc requirement met.

**Evidence (geological.py):**
```python
async def gempy_3d_model(
    extent: list[float],
    resolution: list[int] = None,
    surface_points: list[dict] = None,
    orientation_data: list[dict] = None,
) -> dict[str, Any]:
```
Pure function, no `self`, no class inheritance, no agent protocol.

---

## 3. Rate Limiting — Per-Tool Limits?

**Status: ✅ PASS**

| Aspect | Implementation |
|--------|---------------|
| Algorithm | Token bucket (dual: per-minute + per-hour) |
| Per-tool config | Each tool in YAML has `rate_limit.requests_per_minute` and `requests_per_hour` |
| Burst support | `burst_size` field in `RateLimitConfig` |
| Async-safe | `asyncio.Lock` protects token state |
| Wait-and-acquire | `wait_and_acquire(max_wait=10.0)` blocks until token available or timeout |
| Fallback on limit | If rate limit exceeded, triggers fallback chain |

**Evidence (registry.py lines 78-118):**
```python
class RateLimiter:
    async def acquire(self) -> bool:
        # Refill minute bucket based on elapsed time
        # Refill hour bucket based on elapsed time
        # Check both buckets before allowing
```

**YAML examples of differentiated limits:**
| Tool | RPM | RPH | Rationale |
|------|-----|-----|-----------|
| `run_gempy_model` | 5 | 50 | Compute-heavy |
| `run_geophysical_inversion` | 2 | 20 | Very expensive |
| `alpha_vantage_price` | 5 | 100 | API provider limit |
| `check_cloud_cover` | 60 | 1000 | Lightweight query |
| `validate_confidence` | 100 | 5000 | Ultra-fast check |

**Strength:** Limits are tuned per-tool based on external API constraints and compute cost.

---

## 4. Caching — TTL-Based Caching?

**Status: ✅ PASS**

| Aspect | Implementation |
|--------|---------------|
| TTL per tool | Each tool has `cache.ttl_seconds` in YAML |
| Cache key | SHA-256 of `{tool_name, args}` (deterministic) |
| Eviction | Oldest-entry eviction at `max_entries` capacity |
| Hit tracking | `CacheEntry.hit_count` incremented on access |
| Expiry check | `is_expired()` compares elapsed time vs TTL |
| Async-safe | `asyncio.Lock` protects cache state |
| Bypass option | `execute(..., bypass_cache=True)` skips cache |
| Per-tool disable | `cache.enabled: false` for volatile tools (QC, physical tests) |

**TTL examples from YAML:**
| Tool | TTL | Rationale |
|------|-----|-----------|
| `get_commodity_price` | 300s (5min) | Prices change fast |
| `query_geological_database` | 3600s (1hr) | Geological data stable |
| `query_mindat` | 86400s (24hr) | Mineral data rarely changes |
| `check_look_alikes` | 604800s (1wk) | Static reference data |
| `record_physical_test` | disabled | Never cache test results |

**Note:** Cache is in-memory (`dict`). Production guidance mentions Redis backing but it's not implemented. Acceptable for current scale.

---

## 5. Fallback Chains — What Happens When a Tool Fails?

**Status: ✅ PASS**

| Aspect | Implementation |
|--------|---------------|
| Chain config | `fallback.tools: [ordered_list]` in YAML per tool |
| Trigger | On handler exception OR rate limit timeout |
| Execution | `_execute_fallback()` iterates chain, tries each in order |
| Recursive | Fallback tools go through the full `execute()` pipeline (cache, rate limit, etc.) |
| Exhaustion | Returns `{"success": False, "error": "All fallbacks exhausted"}` |

**Fallback chains from YAML:**

| Primary Tool | Fallback Chain |
|-------------|---------------|
| `query_geological_database` | → `query_mindat` → `usgs_mrdata_query` |
| `query_mindat` | → `usgs_mrdata_query` → `query_geological_database` |
| `query_sentinel2` | → `query_planetary_computer` |
| `identify_mineral_photo` | → `classify_with_clip` |
| `get_commodity_price` | → `finnhub_price` → `alpha_vantage_price` |
| `yfinance_price` | → `finnhub_price` |
| `quantum_mineral_classify` | → `classical_mineral_classify` |
| `quantum_drill_optimize` | → `classical_greedy_optimize` |

**Market tool has explicit multi-provider chain in code (`market.py`):**
```python
async def get_commodity_price_chain(commodity, currency):
    result = await yfinance_price(...)     # Primary
    if result.get("success"): return result
    result = await finnhub_price(...)      # Fallback 1
    if result.get("success"): return result
    result = await alpha_vantage_price(...) # Fallback 2
```

**Quantum tools have classical fallbacks:**
- `pennylane_quantum_kernel` → `classical_mineral_classify`
- `qiskit_qaoa_optimize` → `classical_greedy_optimize`

**Strength:** Graceful degradation from quantum → classical is architecturally elegant.

---

## 6. Pydantic Validation — All Inputs/Outputs Validated?

**Status: ⚠️ WARNING — Partial**

**Registry-level config: ✅ Fully Pydantic**
- `ToolConfig(BaseModel)` validates YAML structure
- `RateLimitConfig`, `CacheConfig`, `FallbackConfig` — all Pydantic
- `ToolDefinition(BaseModel)` — validated output for agent consumption
- `CacheEntry(BaseModel)` — validated cache entries

**Tool I/O: ⚠️ NOT Pydantic-validated**

Tool functions accept raw Python types and return plain `dict[str, Any]`:
```python
async def gempy_3d_model(
    extent: list[float],           # ← type hint only, no Pydantic validation
    resolution: list[int] = None,
) -> dict[str, Any]:              # ← unvalidated dict output
```

**What's missing:**
- No `InputModel(BaseModel)` / `OutputModel(BaseModel)` per tool
- No runtime validation of arguments against JSON Schema in `config.parameters`
- The `execute()` method docstring says "arguments: Tool arguments (will be validated)" but no validation code exists
- Tool return values are not validated against any schema

**Impact:** Invalid arguments could reach tool handlers unchecked. Malformed return values propagate silently.

**Recommendation:** Add Pydantic input models per tool and validate in `execute()`:
```python
# In registry.py execute():
if config.parameters:
    # Validate arguments against JSON Schema or Pydantic model
    pass
```

---

## 7. Error Handling — Graceful Degradation?

**Status: ✅ PASS**

| Pattern | Implementation | Quality |
|---------|---------------|---------|
| ImportError fallback | Every external lib (GemPy, SimPEG, PennyLane, Qiskit, yfinance) wrapped in `try/ImportError` | ✅ |
| Mock results | Missing deps return `{"success": False, "error": "...", "mock_result": {...}}` | ✅ |
| API error handling | HTTP errors caught, returned as `{"success": False, "error": "..."}` | ✅ |
| Timeout handling | `asyncio.wait_for(handler, timeout=config.timeout_seconds)` | ✅ |
| Missing handler | `ValueError("No handler registered for tool")` | ✅ |
| Missing tool | `ValueError("Tool not found in registry")` | ✅ |
| Disabled tool | `ValueError("Tool is disabled")` | ✅ |
| Permission denied | `PermissionError("Missing permission")` | ✅ |
| Fallback exhaustion | `{"success": False, "error": "All fallbacks exhausted"}` | ✅ |
| API key missing | Returns error with guidance: `"MINDAT_API_KEY not set"` | ✅ |

**Vision tool safety (vision.py):**
- Pyrite NEVER classified as gold (hard assertion with CLIP double-check)
- Photo-only confidence capped at 65%
- Swahili disclaimers on every prediction
- Economic minerals flagged for expert review

**Financial tool conservatism (financial.py):**
- 15% discount rate (high for Kenya)
- 75% recovery rate (conservative for artisanal)
- Sensitivity analysis always included
- Clear disclaimers in Swahili and English

---

## ⚠️ Warnings

### W1: Incomplete Handler Registration for 4 Modules

`vision.py`, `legal.py`, `financial.py`, and `reports.py` do **not** have `register_*_tools()` functions. Their handlers must be registered through `main.py`'s agent module import path.

**Current flow in `main.py`:**
```python
# This works for geological, satellite, market, quantum:
register_geological_tools(self.tool_registry)

# But for vision, legal, financial, reports — relies on agent module imports:
("src.agents.mineral_id", ["identify_mineral_photo", ...]),
("src.agents.legal", ["query_mining_act", ...]),
```

**Risk:** If agent modules don't expose these exact function names, tools silently fail to register.

**Recommendation:** Add `register_vision_tools()`, `register_legal_tools()`, `register_financial_tools()`, `register_report_tools()` functions and call them in `main.py`.

### W2: YAML Tool Name ↔ Python Function Name Mismatches

Some YAML tool names don't match the Python function names in tools/:

| YAML tool name | Python function | Match? |
|---------------|----------------|--------|
| `query_geological_database` | `geological_database_query` | ❌ Different |
| `run_gempy_model` | `gempy_3d_model` | ❌ Different |
| `identify_mineral_photo` | `identify_mineral_from_photo` | ❌ Different |
| `calculate_npv_irr` | `calculate_npv` | ❌ Different |

These mismatches mean YAML config won't find the tools/ handlers unless agent modules expose them with the YAML names.

### W3: No Runtime Argument Validation

The `execute()` method promises validation but doesn't implement it. Tool handlers receive raw kwargs with no schema enforcement. This is a security and reliability gap.

---

## Tool Coverage Matrix

| Architecture Requirement | Tool Module | Functions | Registered | Fallback |
|--------------------------|-------------|-----------|------------|----------|
| geological (GemPy, SimPEG, Mindat, USGS) | `geological.py` | 5 functions | ✅ via `register_geological_tools` | ✅ USGS↔Mindat |
| satellite (Sentinel-2, Planetary Computer) | `satellite.py` | 5 functions | ✅ via `register_satellite_tools` | ✅ Sentinel→PC |
| vision (EfficientNet-B4, CLIP, YOLOv8) | `vision.py` | 2 functions | ⚠️ via agent modules | ✅ Photo→CLIP |
| market (yfinance, Finnhub, Alpha Vantage) | `market.py` | 5 functions | ✅ via `register_market_tools` | ✅ 3-provider chain |
| legal (Kenya Mining Act, licensing) | `legal.py` | 2 functions | ⚠️ via agent modules | ❌ No fallback |
| financial (NPV calculator, valuation) | `financial.py` | 2 functions | ⚠️ via agent modules | ❌ No fallback |
| quantum (PennyLane, Qiskit) | `quantum.py` | 4 functions | ✅ via `register_quantum_tools` | ✅ Quantum→Classical |
| reports (PDF generator) | `reports.py` | 1 function | ⚠️ via agent modules | ❌ No fallback |

---

## Final Score

| Check | Status |
|-------|--------|
| 1. YAML-configured registry | ✅ PASS |
| 2. Tools as functions (not classes) | ✅ PASS |
| 3. Per-tool rate limiting | ✅ PASS |
| 4. TTL-based caching | ✅ PASS |
| 5. Fallback chains | ✅ PASS |
| 6. Pydantic validation | ⚠️ PARTIAL (config ✅, I/O ❌) |
| 7. Error handling / graceful degradation | ✅ PASS |

**Overall: ⚠️ PASS WITH WARNINGS**

The tool registry is architecturally sound and well-implemented for a prototype. The YAML-driven configuration, token bucket rate limiting, TTL caching, and quantum→classical fallback chains are production-quality patterns. The main gaps are in Pydantic I/O validation at the tool boundary and incomplete handler registration for 4 of 8 modules. These are fixable without architectural changes.
