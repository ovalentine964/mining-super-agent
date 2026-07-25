# Final Council 7: Tool Registry — Full Repo Review

**Reviewer:** Tool Registry Council  
**Scope:** `/home/work/.openclaw/workspace/mining-super-agent/src/tools/` + `src/config/tools.yaml`  
**Date:** 2026-07-25

---

## Executive Summary

The tool registry has **excellent architectural design** — YAML-driven config, Pydantic schemas, token-bucket rate limiting, TTL caching, and fallback chains are all present in the code. However, there is a **critical execution gap**: ~50% of YAML-declared tools lack Python handlers, and naming mismatches between YAML and Python create runtime resolution failures. Two parallel tool systems exist (custom registry + DeerFlow LangChain adapters) without a unified bridge.

**Score: 7/10**

---

## Detailed Findings

### 1. Plug-and-Play Registry (YAML Config) ✅/⚠️

| Aspect | Status | Detail |
|--------|--------|--------|
| YAML config exists | ✅ | `src/config/tools.yaml` — 60+ tools defined |
| YAML structure | ✅ | Each tool has: name, description, module, permissions, timeout, rate_limit, cache, fallback |
| Registry loads YAML | ✅ | `ToolRegistry.load_from_yaml()` parses and creates `ToolConfig` + `RateLimiter` + `CacheManager` per tool |
| Rust config exists | ⚠️ | `rust/config/tools.yaml` — completely different tool names/format, no cross-reference |
| DeerFlow adapters | ⚠️ | `deerflow_tools.py` — parallel LangChain `BaseTool` system, 25+ tool classes, separate from registry |

**Issue:** Two tool systems coexist without integration. DeerFlow tools bypass the registry entirely (no rate limiting, no caching, no fallback chains).

---

### 2. Pydantic Schemas for All Tool I/O ✅/⚠️

| Aspect | Status | Detail |
|--------|--------|--------|
| Schema file exists | ✅ | `schemas.py` — 40+ Input/Output BaseModel classes |
| Registry supports schemas | ✅ | `register_handler(tool_name, handler, input_schema, output_schema)` |
| Runtime validation | ✅ | `execute()` validates input via `input_schema(**arguments)` and output via `output_schema(**result)` |
| Coverage | ⚠️ | Only **4 of 8** register functions pass schemas (vision, legal, financial, reports). Geological, satellite, market, quantum pass **no schemas** to handlers. |
| DeerFlow schemas | ✅ | `deerflow_tools.py` has its own Pydantic schemas per tool (25+ classes) |

**Schemas registered by module:**

| Module | Input Schema | Output Schema |
|--------|-------------|---------------|
| geological.py | ❌ None | ❌ None |
| satellite.py | ❌ None | ❌ None |
| market.py | ❌ None | ❌ None |
| quantum.py | ❌ None | ❌ None |
| vision.py | ✅ MineralPhotoInput/Output, XRFInput/Output | ✅ |
| legal.py | ✅ MiningActInput/Output, LicensingInput/Output | ✅ |
| financial.py | ✅ NPVInput/Output, ValueEstimateInput/Output | ✅ |
| reports.py | ✅ ReportInput/Output | ✅ |

---

### 3. register_*_tools() in All Modules ✅

| Module | Function | Handler Count |
|--------|----------|---------------|
| geological.py | `register_geological_tools()` | 5 handlers |
| satellite.py | `register_satellite_tools()` | 5 handlers |
| market.py | `register_market_tools()` | 5 handlers |
| quantum.py | `register_quantum_tools()` | 4 handlers |
| vision.py | `register_vision_tools()` | 3 handlers |
| legal.py | `register_legal_tools()` | 2 handlers |
| financial.py | `register_financial_tools()` | 2 handlers |
| reports.py | `register_report_tools()` | 1 handler |
| **Total** | **8 register functions** | **31 handlers** |

**`register_all_tools()`** in `__init__.py` calls all 8 — ✅ complete.

---

### 4. YAML ↔ Python Name Match ❌

This is the **biggest problem**. 60+ tools declared in YAML, only 31 handlers registered.

#### A. Tools with NO handler (YAML declares, Python never registers):

| YAML Tool Name | YAML Module Path | Problem |
|----------------|-----------------|---------|
| `analyze_deposit_model` | `src.agents.geological...` | Points to agents/, no handler |
| `detect_alteration_zones` | `src.agents.satellite...` | Points to agents/, no handler |
| `query_planetary_computer` | `src.agents.satellite...` | Points to agents/, no handler |
| `check_look_alikes` | `src.agents.mineral_id...` | Points to agents/, no handler |
| `record_physical_test` | `src.agents.mineral_id...` | Points to agents/, no handler |
| `classify_with_clip` | `src.agents.mineral_id...` | Points to agents/, no handler |
| `analyze_price_trend` | `src.agents.market...` | Points to agents/, no handler |
| `calculate_value` | `src.agents.market...` | Points to agents/, no handler |
| `generate_swahili_report` | `src.agents.market...` | Points to agents/, no handler |
| `calculate_npv_irr` | `src.agents.financial...` | Points to agents/, no handler |
| `estimate_capex` | `src.agents.financial...` | Points to agents/, no handler |
| `estimate_opex` | `src.agents.financial...` | Points to agents/, no handler |
| `sensitivity_analysis` | `src.agents.financial...` | Points to agents/, no handler |
| `check_license_requirements` | `src.agents.legal...` | Points to agents/, no handler |
| `check_eia_requirements` | `src.agents.legal...` | Points to agents/, no handler |
| `check_fpic_requirements` | `src.agents.legal...` | Points to agents/, no handler |
| `generate_compliance_checklist` | `src.agents.legal...` | Points to agents/, no handler |
| `stakeholder_analysis` | `src.agents.community...` | Points to agents/, no handler |
| `fpic_guidance` | `src.agents.community...` | Points to agents/, no handler |
| `draft_cda_outline` | `src.agents.community...` | Points to agents/, no handler |
| `cultural_guidance` | `src.agents.community...` | Points to agents/, no handler |
| `design_drilling_program` | `src.agents.exploration...` | Points to agents/, no handler |
| `design_sampling_strategy` | `src.agents.exploration...` | Points to agents/, no handler |
| `plan_geophysical_survey` | `src.agents.exploration...` | Points to agents/, no handler |
| `estimate_exploration_costs` | `src.agents.exploration...` | Points to agents/, no handler |
| `cross_check_results` | `src.agents.qc...` | Points to agents/, no handler |
| `validate_confidence` | `src.agents.qc...` | Points to agents/, no handler |
| `check_data_quality` | `src.agents.qc...` | Points to agents/, no handler |
| `flag_conflicts` | `src.agents.qc...` | Points to agents/, no handler |
| `quantum_feature_map` | `src.agents.quantum...` | Points to agents/, no handler |
| `classical_fallback` | `src.agents.quantum...` | Points to agents/, no handler |

**~31 tools with YAML config but no handler** — rate limiters and caches created for tools that will always fail at execution.

#### B. Handler name mismatches (registered name ≠ YAML name):

| YAML Name | Registered Handler Name | Function |
|-----------|------------------------|----------|
| `query_sentinel2` | `sentinel2_download` | sentinel2_download() |
| `get_commodity_price` | `get_commodity_price` | → calls `get_commodity_price_chain()` |
| `xrf_analysis` | `xrf_analysis` | → calls `analyze_xrf()` |
| `npv_calculator` | `npv_calculator` | → calls `calculate_npv()` |
| `licensing_info` | `licensing_info` | → calls `get_licensing_info()` |

The `get_commodity_price` case works because the handler is registered as `"get_commodity_price"` but points to `get_commodity_price_chain` function. Similarly `licensing_info` maps to `get_licensing_info`. These are fine. But `query_sentinel2` in YAML maps to handler `sentinel2_download` — **name mismatch**.

#### C. Module path mismatches:

| YAML Tool | YAML Module | Actual Python |
|-----------|------------|---------------|
| `calculate_spectral_indices` | `src.tools.satellite` | No single function — 3 separate calculators (ndvi, clay, iron oxide) |
| `licensing_info` | `src.tools.legal.get_licensing_info` | Function is `get_licensing_info()`, registered as `licensing_info` ✅ |

---

### 5. Rate Limiting (Token Bucket) ✅

| Aspect | Status | Detail |
|--------|--------|--------|
| Algorithm | ✅ | Token bucket with per-minute AND per-hour dual-bucket |
| Implementation | ✅ | `RateLimiter` class with `acquire()` and `wait_and_acquire(max_wait)` |
| Per-tool config | ✅ | Each YAML tool has `rate_limit.requests_per_minute` and `requests_per_hour` |
| Async-safe | ✅ | Uses `asyncio.Lock()` |
| Burst support | ✅ | `burst_size` field in `RateLimitConfig` (default 5) |
| Integration | ✅ | `execute()` calls `wait_and_acquire()` before handler execution |
| Fallback on rate limit | ✅ | If rate limit exceeded, triggers `_execute_fallback()` |

**Note:** Rate limiters are created for all 60+ YAML tools, even those without handlers. Wasted but not harmful.

---

### 6. Caching (TTL) ✅

| Aspect | Status | Detail |
|--------|--------|--------|
| TTL cache | ✅ | `CacheManager` with per-tool TTL from YAML |
| Cache strategies | ✅ | Supports "exact" (SHA-256 hash of args) and "semantic" (declared but not implemented) |
| Eviction | ✅ | LRU-like: evicts oldest entry when at capacity (`max_entries=1000`) |
| Integration | ✅ | `execute()` checks cache before execution, stores after |
| Bypass option | ✅ | `bypass_cache=True` parameter |
| Per-tool enable/disable | ✅ | `cache.enabled: true/false` per tool |
| Market-specific cache | ✅ | `market.py` has its own in-memory price cache with 300s TTL |

**Note:** Cache is in-memory only. YAML comments say "For production, backed by Redis" — Redis not implemented.

---

### 7. Fallback Chains ✅

| Aspect | Status | Detail |
|--------|--------|--------|
| Config | ✅ | Each YAML tool has `fallback.tools: [...]` — ordered list of alternative tools |
| Implementation | ✅ | `_execute_fallback()` iterates through fallback list, tries each |
| Rate limit fallback | ✅ | Rate limit exhaustion triggers fallback chain |
| Error fallback | ✅ | Handler exceptions trigger fallback chain |
| Key chains | ✅ | `get_commodity_price` → `finnhub_price` → `alpha_vantage_price` |
| | | `query_geological_database` → `query_mindat` → `usgs_mrdata_query` |
| | | `quantum_mineral_classify` → `classical_mineral_classify` |
| | | `identify_mineral_from_photo` → `classify_with_clip` |

**Issue:** Many fallback targets are themselves agent-module tools with no handlers, so fallback chains break at runtime.

---

### 8. Error Handling ✅

| Aspect | Status | Detail |
|--------|--------|--------|
| Try/except in handlers | ✅ | All handlers have try/except with graceful error returns |
| Timeout enforcement | ✅ | `asyncio.wait_for()` with `config.timeout_seconds` |
| ImportError handling | ✅ | All optional-dependency tools (GemPy, SimPEG, PennyLane, Qiskit, yfinance, pystac-client) catch ImportError and return mock/fallback data |
| Permission checking | ✅ | `execute()` checks `permissions` set against tool requirements |
| Disabled tool check | ✅ | Raises `ValueError` for disabled tools |
| Output validation | ⚠️ | Output schema validation failures are logged but **not raised** — silently passes invalid output |
| Schema validation on input | ✅ | Raises `ValueError` on input validation failure |

---

## Architecture Diagram

```
src/config/tools.yaml          src/tools/*.py
┌─────────────────────┐       ┌──────────────────────────┐
│ 60+ tool definitions│       │ 31 handler functions     │
│ rate_limit, cache,  │──────▶│ 8 register_*_tools()     │
│ fallback, perms     │       │ schemas.py (40+ models)  │
└─────────────────────┘       └──────────┬───────────────┘
                                         │
                                         ▼
                               ┌─────────────────────┐
                               │   ToolRegistry      │
                               │  - load_from_yaml() │
                               │  - register_handler()│
                               │  - execute()        │
                               │    ├─ permission ck  │
                               │    ├─ schema valid.  │
                               │    ├─ cache lookup   │
                               │    ├─ rate limit     │
                               │    ├─ handler exec   │
                               │    ├─ cache store    │
                               │    └─ fallback chain │
                               └─────────────────────┘

src/tools/deerflow_tools.py     (PARALLEL SYSTEM — no integration)
┌─────────────────────────────┐
│ 25+ LangChain BaseTool cls  │
│ Own Pydantic schemas        │
│ No rate limiting            │
│ No caching                  │
│ No fallback chains          │
└─────────────────────────────┘
```

---

## Score Breakdown

| Criterion | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| YAML config (plug-and-play) | 8/10 | 15% | 1.20 |
| Pydantic schemas (all I/O) | 7/10 | 15% | 1.05 |
| register_*_tools() presence | 10/10 | 10% | 1.00 |
| YAML ↔ Python name match | 4/10 | 20% | 0.80 |
| Rate limiting (token bucket) | 9/10 | 10% | 0.90 |
| Caching (TTL) | 8/10 | 10% | 0.80 |
| Fallback chains | 7/10 | 10% | 0.70 |
| Error handling | 8/10 | 10% | 0.80 |
| **TOTAL** | | **100%** | **7.25 → 7/10** |

---

## Critical Issues (Must Fix)

1. **~31 YAML tools have no Python handlers.** Registry creates rate limiters and caches for them, but `execute()` will always raise `ValueError("No handler registered")`. These tools are dead config.

2. **Agent/tool confusion.** Many YAML `module` paths point to `src.agents.*` instead of `src.tools.*`. The YAML declares these as "tools" but they're actually agent-level functions that were never ported to the tool layer.

3. **`query_sentinel2` name mismatch.** YAML name is `query_sentinel2` but the handler is registered as `sentinel2_download`. Lookup by YAML name will fail.

4. **Dual tool system.** `deerflow_tools.py` implements 25+ LangChain tools with its own schemas but doesn't use the ToolRegistry — no rate limiting, caching, or fallback chains apply to DeerFlow-invoked tools.

5. **`calculate_spectral_indices` has no single handler.** YAML points to `src.tools.satellite` (the module), but the module registers 3 separate index calculators (NDVI, clay ratio, iron oxide), not one unified tool.

## Recommendations

1. **Move agent-level tools to tool layer.** Create handler functions in `src/tools/` for the 31 missing tools, or remove them from YAML.
2. **Fix name mismatches.** Align YAML `name` fields with `register_handler()` first argument.
3. **Bridge DeerFlow adapters to registry.** Have `MiningTool._run()` go through `ToolRegistry.execute()` to get rate limiting/caching/fallback.
4. **Register schemas for all modules.** Geological, satellite, market, and quantum modules should pass input/output schemas.
5. **Implement Redis cache backend.** Current in-memory cache doesn't survive restarts.
6. **Implement "semantic" cache strategy.** Declared in config but not implemented.
