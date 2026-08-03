# Testing & Quality Review — Sovereign Resource DAO

**Council:** Testing & Quality Review
**Date:** 2026-08-04
**Scope:** All components — Python backend, Solidity contracts, Flutter mobile, React dashboard

---

## Executive Summary

| Component | Modules | Tested | Coverage | Grade |
|-----------|---------|--------|----------|-------|
| Python Backend (`src/`) | 39 | 4 (direct) | ~10% module-level | 🔴 Critical |
| Smart Contracts | 5 | 5 | 100% module-level | 🟢 Strong |
| Flutter Mobile | 18 files | 1 file | ~5% | 🔴 Critical |
| React Dashboard | 14 files | 0 | 0% | 🔴 Critical |
| **Overall** | **76** | **10** | **~13%** | **🔴 Critical** |

**Bottom line:** The quantum subsystem is thoroughly tested. Everything else is essentially untested at the unit level. The smart contracts are the strongest component. The dashboard has zero tests.

---

## 1. Python Backend (`tests/` + `src/`)

### 1.1 What Exists

| Test File | Tests | Lines | Covers |
|-----------|-------|-------|--------|
| `test_agents.py` | 3 | 40 | `src/agents/base.py` — `calibrate_confidence`, `ConfidenceLevel`, `ToolDefinition` |
| `test_hallucination_prevention.py` | 11 | 76 | `src/ml/hallucination_prevention.py` — confidence checks, consistency, domain rules |
| `test_quantum.py` | 45 | 518 | All 7 quantum modules: config, classical fallback, kernel, QAOA, ML, chemistry, benchmarks |
| `test_tools_registry.py` | 4 | 35 | `src/tools/registry.py` — config creation, register, list, disabled tools |
| **Total** | **63** | **669** | |

### 1.2 What's Tested

- **Quantum subsystem (7/7 modules):** Excellent. 45 tests covering QuantumConfig, ClassicalFallback, QuantumKernelClassifier, QAOAOptimizer, QuantumMineralClassifier, QuantumChemistrySimulator, and benchmarks. Includes edge cases, fallback behavior, and numerical correctness.
- **Agent base (1/39 modules):** 3 tests for confidence calibration and tool definition serialization.
- **Hallucination prevention (1/39 modules):** 11 tests covering confidence capping, consistency checks, domain rules, and full pipeline.
- **Tool registry (1/39 modules):** 4 tests for config CRUD operations.

### 1.3 What's Missing — Critical Gaps

**35 of 39 Python modules have ZERO direct test coverage:**

| Category | Untested Modules | Functions/Classes |
|----------|-----------------|-------------------|
| **ML/Core** | `clip_classifier.py`, `mineral_classifier.py`, `model_registry.py`, `rag_pipeline.py`, `satellite_analyzer.py` | ~75 functions |
| **ML/Data & Training** | `data/dataset.py`, `evaluation/eval_suite.py`, `training/train_mineral.py`, `utils/preprocessing.py` | ~16 functions |
| **Tools** | `deerflow_tools.py`, `fair_deal.py`, `financial.py`, `geological.py`, `legal.py`, `market.py`, `reports.py`, `satellite.py`, `schemas.py`, `vision.py` | ~110 functions |
| **API/Channels** | `api/routes/voice.py`, `channels/telegram_bot.py`, `chain/oracle_bridge.py` | ~70 functions |
| **Core/DAO** | `dao/governance.py`, `deerflow_integration.py`, `superagent.py`, `main.py`, `main_legacy.py` | ~54 functions |
| **Reports** | `reports/pdf_generator.py` | ~4 functions |

**Highest-risk untested areas:**
1. **`src/tools/geological.py`** — Core mineral classification logic. If this breaks, the entire product fails.
2. **`src/tools/financial.py`** — Royalty calculations and financial models. Errors here = real money wrong.
3. **`src/ml/mineral_classifier.py`** — ML model inference. Silent failures = wrong mineral IDs.
4. **`src/chain/oracle_bridge.py`** — Blockchain bridge. Bugs = lost transactions or wrong on-chain data.
5. **`src/dao/governance.py`** — Governance logic. Bugs = broken voting.
6. **`src/tools/schemas.py`** — 42 functions defining data contracts. No validation tests = schema drift.

### 1.4 Test Configuration

- **pytest config:** `pyproject.toml` sets `asyncio_mode = "auto"`, `testpaths = ["tests"]` ✅
- **Fixtures:** `conftest.py` provides `event_loop`, `sample_mineral_data`, `sample_gold_pyrite_data` ✅
- **Coverage:** Makefile target `test` runs `pytest tests/ -v --cov=src --cov-report=term-missing` ✅
- **CI:** `.github/workflows/ci.yml` runs `pytest tests/ -v --tb=short` — **no `--cov` flag** ⚠️
- **No coverage thresholds** configured — no fail-under gate ⚠️

### 1.5 Specific Findings

1. **`test_quantum.py` is 518 lines** — well-structured with 7 test classes, but tests import modules lazily inside test bodies (e.g., `from src.quantum.classical_fallback import ClassicalFallback` inside each test). This works but is fragile — if import paths change, every test fails silently at collection time rather than with a clear error.

2. **`conftest.py` fixtures are minimal** — only 3 fixtures for 63 tests. The hallucination prevention tests create their own `HallucinationPrevention()` fixture inline. More shared fixtures would reduce duplication.

3. **No mocking/patching** — Tests that call real backends (e.g., `ClassicalFallback.kernel_classification`) run actual sklearn models. This is acceptable for unit tests of pure functions, but no tests mock external dependencies (database, blockchain, API calls), meaning integration-layer code can't be tested without infrastructure.

4. **No parametrized tests** — Could benefit from `@pytest.mark.parametrize` for boundary conditions (e.g., confidence scores at 0.0, 0.5, 1.0 boundaries).

---

## 2. Smart Contracts (`contracts/test/`)

### 2.1 What Exists

| Test File | `it()` Blocks | `describe()` Blocks | Lines |
|-----------|---------------|---------------------|-------|
| `ExtractionTracker.test.js` | 33 | 9 | 543 |
| `MiningOracle.test.js` | 34 | 8 | 432 |
| `QuadraticVoting.test.js` | 36 | 7 | 468 |
| `RoyaltyDistributor.test.js` | 31 | 7 | 428 |
| **Total** | **134** | **31** | **1,871** |

### 2.2 What's Tested

- **ExtractionTracker:** Soulbound NFT behavior, recording extractions, role-based access, IPFS metadata, location verification.
- **MiningOracle:** Initialization, oracle confirmations, location verification workflow, admin roles.
- **QuadraticVoting:** Token-based voting power, quadratic scaling, proposal lifecycle, whale resistance.
- **RoyaltyDistributor:** Proxy deployment, split percentages (70/20/10), distribution, admin controls.

### 2.3 What's Missing

1. **GovernanceToken — No dedicated test file.** It's used as a dependency in `QuadraticVoting.test.js` (minted/approved), but its own vesting logic (`VestingSchedule`, `release`, `revoke`), `MINTER_ROLE` enforcement, `MAX_SUPPLY` cap, and `ERC20Votes` delegation are untested. This is a **high-risk gap** — vesting bugs = token lock or over-minting.

2. **No negative/fuzz tests.** All tests verify happy paths. Missing:
   - Reentrancy attack vectors on `RoyaltyDistributor.distribute()`
   - Integer overflow in quadratic power calculation (despite Solidity 0.8.x checks)
   - Flash loan + voting manipulation scenarios
   - Zero-amount distribution edge cases

3. **No gas consumption assertions.** No tests verify that operations stay within reasonable gas limits.

4. **No event emission tests.** Tests verify state changes but not that correct events are emitted (important for off-chain indexers).

5. **No upgrade tests for RoyaltyDistributor** (uses OpenZeppelin upgrades proxy). Missing:
   - Storage layout compatibility after upgrade
   - State preservation across upgrades
   - Initializer re-entrancy protection

### 2.4 Test Configuration

- **Framework:** Hardhat + Chai + ethers.js v6 ✅
- **Upgrades plugin:** `@openzeppelin/hardhat-upgrades` ✅
- **Solidity version:** 0.8.20 with optimizer (200 runs) ✅
- **No Solidity linter** (solhint, slither, mythril) configured ⚠️
- **No coverage tool** (`solidity-coverage` not in devDependencies) ⚠️
- **CI:** Compiles and tests contracts ✅, no coverage reporting ⚠️

---

## 3. Flutter Mobile (`mobile/flutter/test/`)

### 3.1 What Exists

| Test File | Tests | Lines |
|-----------|-------|-------|
| `widget_test.dart` | 5 | 143 |

### 3.2 What's Tested

1. **App renders home screen** with menu cards (camera, trending, description, settings icons)
2. **Settings screen** shows all 5 language options (English, Swahili, Luo, Kamba, Luhya)
3. **Observation model** serialization roundtrip (toMap/fromMap)
4. **Observation.copyWith** works correctly
5. **Observation null handling** — defaults for missing fields
6. **LocaleProvider** default locale, supported locales, language names

### 3.3 What's Missing

**17 of 18 Dart source files have ZERO test coverage:**

| Category | Untested Files | Risk |
|----------|---------------|------|
| **Screens** (8) | `agent_chat_screen.dart`, `blockchain_screen.dart`, `dao_screen.dart`, `fair_deal_screen.dart`, `photo_screen.dart`, `price_screen.dart`, `report_screen.dart`, `voice_chat_screen.dart` | 🔴 High — all user-facing |
| **Services** (6) | `api_client.dart`, `channel_manager.dart`, `local_db.dart`, `offline_sync.dart`, `on_device_voice.dart`, `voice_service.dart` | 🔴 Critical — data layer |
| **Models** (1) | `commodity_price.dart` | 🟡 Medium |
| **Other** (2) | `main.dart`, `app_localizations.dart` | 🟡 Medium |

**Critical untested areas:**
- **`services/local_db.dart`** — SQLite operations. Bugs = data loss.
- **`services/offline_sync.dart`** — Offline-to-online sync. Bugs = duplicate/lost data.
- **`services/api_client.dart`** — HTTP client. Needs error handling tests.
- **`services/voice_service.dart`** + **`on_device_voice.dart`** — Voice input. Complex state machine, zero tests.

### 3.4 Test Configuration

- **Framework:** `flutter_test` ✅
- **Analysis:** `flutter_lints` in devDependencies ✅, but **no `analysis_options.yaml`** found ⚠️
- **CI:** Runs `flutter analyze` + `flutter test` ✅
- **No integration tests** (`integration_test/` directory missing) ⚠️
- **No golden tests** for UI snapshots ⚠️

---

## 4. React Dashboard (`dashboard/`)

### 4.1 What Exists

**Nothing.** Zero test files. No test framework configured.

### 4.2 Source Inventory

| Category | Files | Lines |
|----------|-------|-------|
| Components | 7 (ExtractionTable, FairnessIndex, Header, PriceWidget, ProposalList, RoyaltyCard, SatelliteAlerts) | ~500 |
| Hooks | 4 (useExtractions, usePrices, useProposals, useWebSocket) | ~200 |
| Utils | 3 (api, i18n, vite-env.d.ts) | ~100 |
| App/main | 2 | ~50 |
| **Total** | **14** | **~848** |

### 4.3 What's Missing — Everything

- No test framework (no Jest, Vitest, React Testing Library, Cypress, Playwright)
- No test scripts in `package.json`
- No component tests
- No hook tests
- No API mock tests
- No visual regression tests

### 4.4 Recommendations

1. Add `vitest` + `@testing-library/react` + `jsdom` (aligns with Vite toolchain)
2. Add test script: `"test": "vitest run", "test:watch": "vitest"`
3. Priority test targets:
   - `hooks/useWebSocket.ts` — real-time data, reconnection logic
   - `hooks/useExtractions.ts` — data fetching + caching
   - `components/ExtractionTable.tsx` — data display correctness
   - `utils/api.ts` — API client error handling

---

## 5. Static Analysis & Linting

| Tool | Component | Status | Config |
|------|-----------|--------|--------|
| **Ruff** | Python | ✅ Configured | `pyproject.toml` — line-length=100, py312 |
| **Mypy** | Python | ⚠️ Makefile only | No `mypy.ini` or `[tool.mypy]` in pyproject; CI doesn't run it |
| **Flutter analyze** | Dart | ✅ CI runs it | No `analysis_options.yaml` found |
| **Solhint/Slither** | Solidity | ❌ Missing | No Solidity linter configured |
| **ESLint** | Dashboard | ❌ Missing | No eslint config |
| **TypeScript** | Dashboard | ✅ tsconfig.json | Strict mode not enabled |

### 5.1 CI Pipeline Gaps

The CI workflow (`ci.yml`) runs:
- ✅ `ruff check src/ tests/`
- ✅ `pytest tests/ -v --tb=short`
- ✅ `flutter analyze` + `flutter test`
- ✅ `npx hardhat compile` + `npx hardhat test`
- ✅ Rust build + test

**Missing from CI:**
- ❌ `--cov` flag on pytest (no coverage reporting)
- ❌ `mypy` type checking
- ❌ Solidity coverage (`npx hardhat coverage`)
- ❌ Dashboard build verification (no `npm run build` step)
- ❌ Coverage thresholds / gates
- ❌ Security scanning (slither, mythril, bandit, safety)

---

## 6. Test Infrastructure Issues

### 6.1 No Coverage Reporting

- **Python:** `--cov` in Makefile but not in CI. No coverage.xml output. No Codecov/Coveralls integration.
- **Contracts:** `solidity-coverage` not installed. No coverage reports.
- **Dashboard:** No test runner at all.
- **Mobile:** `flutter test` runs but no `--coverage` flag in CI.

### 6.2 No Test Data Factories

- No Faker/factory_boy for Python test data
- No fixtures for contract test scenarios
- No mock data generators for dashboard

### 6.3 No Integration/E2E Tests

- No API integration tests (FastAPI `TestClient`)
- No contract integration tests (multi-contract workflows)
- No mobile integration tests (`integration_test/`)
- No E2E tests (Playwright, Detox)

---

## 7. Priority Recommendations

### P0 — Immediate (Blockers)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 1 | **Add GovernanceToken dedicated tests** — vesting, minting, supply cap, delegation | 1 day | Prevents token lock / over-minting |
| 2 | **Add `--cov` to CI pytest command** + fail-under threshold (start at 30%) | 1 hour | Visibility into coverage regression |
| 3 | **Add `solidity-coverage`** to contracts devDependencies | 30 min | Contract coverage visibility |
| 4 | **Add Vitest to dashboard** + smoke tests for hooks | 1 day | Prevents silent dashboard regressions |

### P1 — High Priority (This Sprint)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 5 | **Test `src/tools/financial.py`** — royalty calculations, NPV, IRR | 1 day | Financial correctness |
| 6 | **Test `src/tools/geological.py`** — mineral classification | 1 day | Core product logic |
| 7 | **Test `src/ml/mineral_classifier.py`** — inference pipeline | 1 day | ML correctness |
| 8 | **Test `src/chain/oracle_bridge.py`** — blockchain bridge | 1 day | Transaction safety |
| 9 | **Add `analysis_options.yaml`** for Flutter with strict rules | 1 hour | Catch Dart issues earlier |
| 10 | **Add contract negative tests** — reentrancy, overflow, zero-amount | 2 days | Security hardening |

### P2 — Medium Priority (Next Sprint)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 11 | **Test `src/dao/governance.py`** — voting logic | 1 day | Governance correctness |
| 12 | **Test remaining `src/tools/` modules** (10 files) | 3 days | Tool reliability |
| 13 | **Test Flutter services** — api_client, local_db, offline_sync | 2 days | Mobile data layer |
| 14 | **Test Flutter screens** — widget tests for all 8 screens | 2 days | UI correctness |
| 15 | **Add Mypy with strict config** to CI | 2 hours | Type safety |
| 16 | **Add ESLint to dashboard** | 1 hour | Code quality |

### P3 — Backlog

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 17 | Add contract gas consumption tests | 1 day | Gas optimization |
| 18 | Add contract event emission tests | 1 day | Off-chain indexer reliability |
| 19 | Add mobile integration tests | 3 days | End-to-end mobile reliability |
| 20 | Add API integration tests (FastAPI TestClient) | 2 days | Backend integration |
| 21 | Add golden tests for Flutter UI | 1 day | Visual regression |
| 22 | Add E2E tests (Playwright for dashboard) | 3 days | Full-stack confidence |
| 23 | Add security scanning (slither, bandit) to CI | 1 day | Vulnerability detection |

---

## 8. Test Quality Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Python module coverage | 4/39 (10%) | 30/39 (77%) |
| Contract module coverage | 4/5 (80%)* | 5/5 (100%) |
| Dashboard test files | 0/14 (0%) | 14/14 (100%) |
| Mobile test files | 1/18 (6%) | 10/18 (56%) |
| CI coverage reporting | ❌ | ✅ All components |
| Static analysis (all languages) | 2/4 (50%) | 4/4 (100%) |
| Integration tests | 0 | At least API + contract |
| Security scanning | 0 | slither + bandit |

*GovernanceToken has no dedicated tests; counted as untested for standalone coverage.

---

## 9. Positive Observations

1. **Quantum tests are exemplary.** 45 tests with proper class organization, edge cases, fallback testing, and numerical assertions. This is the gold standard the rest of the project should follow.

2. **Contract tests are solid.** 134 test cases across 31 describe blocks covering role-based access, state transitions, and deployment patterns. The use of OpenZeppelin upgrades is a good practice.

3. **CI pipeline is well-structured.** Four independent jobs (Python, Rust, Flutter, Contracts) with proper caching and artifact uploads.

4. **Test configuration is clean.** `pyproject.toml` has proper pytest and ruff config. Hardhat config is minimal and correct.

5. **Hallucination prevention tests** demonstrate good defensive testing — verifying that confidence caps, consistency checks, and domain rules work together.

---

## 10. Files Analyzed

| Path | Type | Lines |
|------|------|-------|
| `tests/test_quantum.py` | Python test | 518 |
| `tests/test_hallucination_prevention.py` | Python test | 76 |
| `tests/test_agents.py` | Python test | 40 |
| `tests/test_tools_registry.py` | Python test | 35 |
| `tests/conftest.py` | Python fixtures | 38 |
| `contracts/test/ExtractionTracker.test.js` | Contract test | 543 |
| `contracts/test/QuadraticVoting.test.js` | Contract test | 468 |
| `contracts/test/MiningOracle.test.js` | Contract test | 432 |
| `contracts/test/RoyaltyDistributor.test.js` | Contract test | 428 |
| `mobile/flutter/test/widget_test.dart` | Flutter test | 143 |
| `pyproject.toml` | Config | 100 |
| `Makefile` | Build config | 30 |
| `.github/workflows/ci.yml` | CI pipeline | 110 |
| `contracts/hardhat.config.js` | Contract config | 36 |
| `dashboard/package.json` | Dashboard config | 25 |
| `dashboard/vite.config.ts` | Dashboard config | 22 |
| `mobile/flutter/pubspec.yaml` | Mobile config | 40 |
| `src/` (39 Python modules) | Source | 11,093 |
| `contracts/*.sol` (5 contracts) | Source | 943 |
| `dashboard/src/` (14 files) | Source | 848 |
| `mobile/flutter/lib/` (18 files) | Source | 3,833 |
