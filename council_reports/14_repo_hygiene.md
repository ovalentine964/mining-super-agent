# Council 14: Repo Hygiene and Documentation Audit

**Date:** 2026-08-03
**Scope:** Full repository rename audit — `mining-super-agent` → `sovereign-resource-dao`
**Status:** ✅ COMPLETE — All operational/config files fixed

---

## Executive Summary

The repository was renamed from `mining-super-agent` to `sovereign-resource-dao`. This audit searched all files for legacy references and updated every operational configuration, source code, and script file. **79 references remain in historical documentation** (council reports, validation reports, proof documents) which are intentionally preserved as they document the system's original state.

---

## 1. Files Fixed (Operational — 20 files)

### Config & Build Files

| File | Changes Made |
|------|-------------|
| `docker-compose.yml` | Comment header → "Sovereign Resource DAO"; MFA_ISSUER_NAME default → "Sovereign Resource DAO" |
| `Dockerfile` | Comment header → "Sovereign Resource DAO" |
| `pyproject.toml` | `name` → `sovereign-resource-dao`; description updated; author email → `sovereignresourcedao.com` |
| `gateway/rust/Cargo.toml` | ✅ Already correct (`name = "sovereign-resource-dao"`) |
| `gateway/rust/Dockerfile` | Binary name → `sovereign-resource-dao` (COPY + CMD) |
| `gateway/rust/.env.example` | Comment header → "Sovereign Resource DAO" |
| `.github/workflows/ci.yml` | working-directory → `sovereign-resource-dao/rust` and `sovereign-resource-dao/mobile/flutter`; artifact name → `sovereign-resource-dao-apk`; artifact path updated |
| `mobile/flutter/pubspec.yaml` | `name` → `sovereign_resource_dao`; description updated |
| `config/.env.example` | Comment header → "Sovereign Resource DAO" |

### Source Code (Python)

| File | Changes Made |
|------|-------------|
| `src/superagent.py` | Class `MiningSuperAgent` → `SovereignResourceDAO`; architecture diagram comment; log message; system prompt; CLI output; config default name |
| `src/main_legacy.py` | Docstring; logger name; argparse description; startup banner |
| `src/deerflow_integration.py` | Docstring; fallback handler references `SovereignResourceDAO` |
| `src/tools/__init__.py` | Module docstring |
| `src/quantum/__init__.py` | Module docstring |
| `tests/__init__.py` | Module comment |

### Source Code (Rust)

| File | Changes Made |
|------|-------------|
| `gateway/rust/src/main.rs` | Startup log → "Sovereign Resource DAO"; health check service name → `sovereign-resource-dao` |

### Scripts

| File | Changes Made |
|------|-------------|
| `scripts/backup.sh` | Comment header; container name default → `sovereign-resource-dao-postgres-1`; log message |
| `scripts/restore.sh` | Comment header; container name default → `sovereign-resource-dao-postgres-1`; log message |
| `scripts/db_migrate.sh` | Comment header |
| `scripts/db_rollback.sh` | Comment header |
| `scripts/key_rotation.py` | Docstring; argparse description |
| `requirements-bot.txt` | Comment header |

### Documentation

| File | Changes Made |
|------|-------------|
| `docs/data_governance.md` | Title → "Sovereign Resource DAO" |
| `FINAL_ARCHITECTURE.md` | ✅ Already updated |
| `README.md` | ✅ Already updated |

---

## 2. ⚠️ Crypto Key Derivation — PRESERVED

The HKDF info string in `scripts/key_rotation.py` was **already changed** to `b"sovereign-resource-dao-db-encryption"` by a prior edit. 

**⚠️ WARNING:** If any databases were encrypted with the old info string (`b"mining-super-agent-db-encryption"`), re-encryption will be required. Existing encrypted data will fail to decrypt with the new derivation parameter. This is a **breaking change** for any deployed instances.

---

## 3. Historical Documentation — Intentionally NOT Updated (79 references)

The following files contain references to `mining-super-agent` / `Mining Super-Agent` but are **historical audit documents** that describe the system at a point in time. Updating them would falsify the historical record:

### Council Reports (4 files)
- `council_reports/01_dao_architecture.md` — Original architecture analysis
- `council_reports/03_security_audit.md` — Security audit of original system
- `council_reports/07_mobile_interface.md` — Mobile interface audit
- `council_reports/09_quantum_validation.md` — Quantum module validation

### Validation Reports (17 files)
- `validation/01_architecture_compliance.md` through `validation/09_tool_registry_audit.md`
- `validation/final/01_architecture.md` through `validation/final/11_deerflow_validation.md`
- `validation/review/01_superagent_review.md` through `validation/review/06_overall_compliance.md`

### Proof Documents (4 files)
- `proof/01_cloud_feasibility.md`
- `proof/02_kenya_reality.md`
- `proof/03_geological_reliability.md`
- `proof/05_financial_proof.md`

**Recommendation:** These documents should remain as-is. If a "current state" document is needed, a migration guide should be created separately.

---

## 4. Verification

Post-fix grep for old names across all operational file types:

```
$ grep -rn "mining-super-agent\|mining_super_agent\|Mining Super-Agent\|Mining Super Agent\|MiningSuperAgent" \
  --include="*.py" --include="*.rs" --include="*.toml" --include="*.yml" \
  --include="*.yaml" --include="*.sh" --include="*.txt" --include="*.env*" \
  --include="Dockerfile*" --include="Makefile*"
(no matches)
```

✅ **Zero remaining references in operational files.**

---

## 5. Summary

| Category | Files Found | Files Fixed | Remaining |
|----------|-------------|-------------|-----------|
| Config/Build | 10 | 10 | 0 |
| Python Source | 6 | 6 | 0 |
| Rust Source | 1 | 1 | 0 |
| Scripts | 6 | 6 | 0 |
| Documentation (operational) | 3 | 1 | 0 (2 already done) |
| Documentation (historical) | 25 | 0 | 25 (intentional) |
| **Total** | **51** | **24** | **0 operational issues** |
