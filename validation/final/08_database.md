# 08 — Database Review

**Reviewer:** Final Council 8 — Database
**Date:** 2026-07-25
**Scope:** `/src/db/`, `migrations/`, `docs/data_governance.md`

---

## Checklist Results

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | PostgreSQL + PostGIS | ✅ | `asyncpg` engine, `CREATE EXTENSION postgis`, `geoalchemy2.Geometry` throughout, SRID 4326 |
| 2 | All required tables | ⚠️ PARTIAL | `geological_units` ✅, `mineral_occurrences` ✅, `observations` ✅, `users` ✅, **`api_keys` ❌ MISSING** |
| 3 | GIST spatial indexes | ✅ | GIST indexes on all 6 geometry tables (geological_units, mineral_occurrences, structural_features, geochemical_samples, mining_sites, observations) |
| 4 | pgvector for embeddings | ✅ | `document_embeddings` table with `vector(1024)`, IVFFlat index (`vector_cosine_ops`, lists=100) |
| 5 | Alembic migrations | ✅ | Full async setup: `env.py`, `alembic.ini`, `001_initial.py`, `002_log_retention.py`, async engine support |
| 6 | Log retention (90-day purge) | ✅ | `purge_old_audit_logs(90)` function + pg_cron daily schedule at 03:00 UTC, graceful fallback if pg_cron unavailable |
| 7 | Column-level encryption | ✅ | `encryption.py`: Fernet (AES-128-CBC + HMAC-SHA256) via HKDF key derivation, `EncryptedString`/`EncryptedText`/`EncryptedJSON` types, key rotation support, startup validation. Applied to `User.mfa_secret` |
| 8 | Data governance docs | ✅ | Comprehensive `docs/data_governance.md`: data ownership, classification (Public→Restricted), GDPR Art.15-21 compliance, right-to-erasure cascade, breach response, retention policies |

---

## Detailed Findings

### Architecture
- **Async-first**: SQLAlchemy 2.0 async engine (`asyncpg`), `async_sessionmaker`, proper context-manager session lifecycle with commit/rollback
- **Connection pooling**: pool_size=5, max_overflow=10, pool_pre_ping=True, pool_recycle=1800s
- **PostGIS search path**: `SET search_path TO public, topology, tiger` on connect
- **Extensions**: postgis, postgis_topology, vector, pg_trgm, uuid-ossp

### Tables Present (beyond required)
- `rock_types` — mineral/rock taxonomy reference
- `structural_features` — geological structure data (LINESTRING geom)
- `geochemical_samples` — XRF/geochemistry data (POINT geom)
- `mining_sites` — license & site management (MULTIPOLYGON geom)
- `document_embeddings` — RAG vector store
- `audit_logs` — compliance audit trail

### Tables Missing
- **`api_keys`** — No table for API key management. Third-party API keys are stored in env vars (`NVIDIA_API_KEY`, `GROQ_API_KEY`, etc.) via `pydantic-settings`, but there is no database-backed key management table for user/tenant API keys. This is a gap if the platform needs to issue API keys to external consumers.

### Encryption Quality
- HKDF key derivation (never uses master key directly)
- Key rotation: comma-separated keys, first=active, rest=legacy tried for decryption
- Refuses to start if `ENCRYPTION_KEY` is unset or placeholder
- Encrypt/decrypt roundtrip validation at startup
- Minor note: `mfa_secret` column in `001_initial.sql` is `VARCHAR(64)` but model uses `EncryptedString(512)` — ciphertext is ~2x plaintext, so the migration column width may be insufficient for encrypted storage

### pgvector Implementation
- 1024-dimension vectors (likely for large embedding models like NVIDIA or text-embedding-3-large)
- IVFFlat index with `lists=100` — appropriate for datasets up to ~1M vectors
- Source tracking via `source_table` + `source_id` for provenance

### Migration Quality
- Proper up/down migrations
- Idempotent (`CREATE EXTENSION IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`)
- pg_cron scheduling wrapped in exception handler for portability
- Composite index on `audit_logs(created_at)` for efficient retention deletes

---

## Score: 8 / 10

**Rationale:** The database layer is production-grade — async PostgreSQL + PostGIS + pgvector, proper Alembic migrations, column-level encryption with key rotation, comprehensive data governance documentation, and automated 90-day log retention. The only significant gap is the missing `api_keys` table (required by spec), and a minor migration column-width mismatch on `mfa_secret`. Everything else exceeds expectations.
