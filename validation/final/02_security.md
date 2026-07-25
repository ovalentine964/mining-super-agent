# Final Council 2: Security — Full Repo Review

**Reviewed:** `/home/work/.openclaw/workspace/mining-super-agent/`
**Date:** 2026-07-25

---

## 1. JWT refuses to start if secret not set? ✅

**Python (`src/config/settings.py`):**
- `_validate_critical_secrets()` model validator checks `jwt_secret_key` and `jwt_refresh_secret_key`
- Refuses to start if empty OR starts with `"CHANGE_ME"` → `sys.exit(1)`
- In production, also validates `DB_PASSWORD`, `API_KEYS_ENCRYPTION_KEY`, `ENCRYPTION_KEY`, `REDIS_PASSWORD`

**Rust (`rust/src/config.rs`):**
- `AppConfig::from_env()` requires `JWT_SECRET` via `env::var().context()`
- Validates minimum length: `if jwt_secret.len() < 32 { anyhow::bail!(...) }`
- `.env.example` warns: `JWT_SECRET=change-me-to-a-secure-random-string-at-least-32-chars`

**Verdict:** Solid fail-closed on both stacks.

---

## 2. CORS rejects wildcards (Python AND Rust)? ⚠️ Partial

**Python (`src/config/settings.py`):**
- `_reject_wildcard_cors` field_validator rejects `"*"` in `CORS_ORIGINS`
- `cors_origin_list` property rejects `"*"` and `".*"` patterns
- **Gap:** If `CORS_ORIGINS` is empty (not set), the validator passes (empty string → no origins to check). `cors_origin_list` returns `[]`. FastAPI's `CORSMiddleware` with `allow_origins=[]` **blocks all cross-origin requests** — this is actually safe, but the intent is unclear.

**Rust (`rust/src/config.rs`):**
- Production: `if cors_raw.trim() == "*" && app_env == "production"` → `anyhow::bail!`
- YAML overlay: same check for `"*"` in production
- Dev mode: allows `"*"` with a `tracing::warn!`

**Issue:** The `.env.example` sets `CORS_ORIGINS=https://mining.example.com` (good), and `docker-compose.yml` requires `CORS_ORIGINS:?CORS_ORIGINS must be set` (fail-fast). However, the Python validator does NOT reject empty string — it silently allows it. The Rust validator only rejects `"*"` in production, not other dangerous patterns.

**Verdict:** Wildcard rejection works when explicitly set to `*`. Empty/unset bypasses the check in Python but results in no origins allowed (safe by accident). Rust only checks in production.

---

## 3. TLS enforcement? ✅

**Caddy (`Caddyfile`):**
- `tls {$ACME_EMAIL}` — automatic Let's Encrypt certificates
- HTTP→HTTPS redirect is implicit with Caddy TLS
- HSTS header: `max-age=63072000; includeSubDomains; preload`

**Python (`src/api/middleware/tls_enforcement.py`):**
- `TLSEnforcementMiddleware` rejects plain HTTP with 403 in production
- Validates `X-Forwarded-Proto` header (anti-spoofing)
- Injects HSTS on every response
- Exempt paths: `/health`, `/health/detailed`

**Rust:** No TLS middleware (relies on Caddy at edge). Acceptable for reverse-proxy architecture.

**Verdict:** Defense-in-depth with Caddy (proxy) + Python middleware (app-level). Strong.

---

## 4. MFA (TOTP + backup codes)? ✅

**Python (`src/api/routes/auth.py`):**
- TOTP setup via `pyotp` with QR code generation (SVG)
- 10 backup codes, bcrypt-hashed, single-use (removed after use)
- MFA-required login flow (returns 428 with `mfa_required: true`)
- MFA disable requires current TOTP verification
- Account lockout after 5 failed attempts (15 min)
- Warning when ≤2 backup codes remaining
- `TOTP_VALID_WINDOW = 1` (30s drift tolerance)

**Rust:** No MFA implementation (API gateway delegates to Python auth service).

**Verdict:** Full TOTP + backup codes implementation. Well-designed.

---

## 5. Column-level encryption (Fernet)? ⚠️ Partial

**`src/db/encryption.py`:**
- `EncryptedString`, `EncryptedText`, `EncryptedJSON` — transparent SQLAlchemy types
- HKDF key derivation from master key (never uses raw key)
- Multi-key support for rotation (comma-separated `ENCRYPTION_KEY`)
- Startup validation: `validate_encryption_key()` tests encrypt→decrypt roundtrip
- App **refuses to start** if `ENCRYPTION_KEY` is missing or placeholder

**`src/db/models.py`:**
- `mfa_secret` → `EncryptedString(512)` ✅
- **`phone` → `String(30)` — NOT encrypted** ❌
- Key rotation script lists `phone` as encrypted column, but model uses plain `String(30)`

**`scripts/key_rotation.py`:**
- Lists `("users", "phone", "string")` as encrypted column — **mismatch with model**
- Re-encryption would silently skip unencrypted phone values (they don't start with `gAAAAA`)

**Verdict:** Encryption infrastructure is solid. Only `mfa_secret` is actually encrypted. `phone` field is a gap — rotation script assumes it's encrypted but it's not.

---

## 6. Key rotation script? ✅

**`scripts/key_rotation.py`:**
- Supports: `encryption` (Fernet), `jwt`, `jwt-refresh`, `all`
- DB re-encryption with old→new key (graceful: new key first, old as fallback)
- `.env` file update with backup creation
- Audit logging to `logs/key_rotation_audit.jsonl`
- `--dry-run` mode for safe testing
- Preserves old key as comma-separated fallback for zero-downtime rotation

**Verdict:** Comprehensive rotation script with audit trail and dry-run. Production-ready.

---

## 7. Internal Docker networks? ✅

**`docker-compose.yml`:**
- `internal` network: `internal: true` — no external access
- `external` network: Caddy + app only
- **No port mappings** on: postgres, redis, qdrant, minio
- Only Caddy exposes `80`, `443`, `443/udp` (HTTP/3)
- Resource limits on all services
- Health checks on all services

**Verdict:** Perfect network isolation. Databases are unreachable from outside.

---

## 8. Redis hardening? ✅

**`docker-compose.yml` Redis config:**
- `--requirepass ${REDIS_PASSWORD:?REDIS_PASSWORD must be set}` — mandatory password
- Disabled commands: `FLUSHALL`, `FLUSHDB`, `CONFIG`, `DEBUG`, `SHUTDOWN`
- `--maxmemory 256mb` with `--maxmemory-policy allkeys-lru`
- No port mapping — internal network only
- Health check with password: `redis-cli -a "${REDIS_PASSWORD}" ping`

**Verdict:** Strong Redis hardening. Dangerous commands disabled, password required, memory bounded.

---

## 9. Security headers (OWASP)? ✅

**Python (`src/api/middleware/security_headers.py`):**
- `Strict-Transport-Security`: `max-age=63072000; includeSubDomains; preload`
- `X-Frame-Options`: `DENY`
- `X-Content-Type-Options`: `nosniff`
- `X-XSS-Protection`: `1; mode=block`
- `Referrer-Policy`: `strict-origin-when-cross-origin`
- `Content-Security-Policy`: strict `default-src 'self'` with granular directives
- `Cross-Origin-Embedder-Policy`: `require-corp`
- `Cross-Origin-Opener-Policy`: `same-origin`
- `Cross-Origin-Resource-Policy`: `same-origin`
- `Permissions-Policy`: `camera=(), microphone=(), geolocation=(self)`
- Removes: `Server`, `X-Powered-By`, `X-AspNet-Version`, `X-AspNetMvc-Version`

**Caddy:** Same headers duplicated at proxy level (defense-in-depth).

**Verdict:** Complete OWASP header coverage at both proxy and app layers.

---

## 10. Rate limiting? ✅

**Caddy (`Caddyfile`):**
- Global: 100 req/s burst per IP
- API: 30 req/s per IP
- Auth: 5 req/s per IP
- Request body limit: 10MB

**Python (`src/api/middleware/rate_limit.py`):**
- Redis-backed token bucket middleware exists
- Auth: 5 req/60s, Default: 60 req/60s
- **Not registered in `src/api/main.py`** — dead code

**Rust:** `default_rate_limit: 100` and `rate_window_secs: 60` in config, but no middleware implementation.

**Verdict:** Rate limiting is enforced at the Caddy edge (effective). Python app-level middleware exists but is not wired up — redundant with Caddy but could be defense-in-depth.

---

## Summary

| # | Check | Status |
|---|-------|--------|
| 1 | JWT refuses to start if secret not set | ✅ |
| 2 | CORS rejects wildcards (Python AND Rust) | ⚠️ |
| 3 | TLS enforcement | ✅ |
| 4 | MFA (TOTP + backup codes) | ✅ |
| 5 | Column-level encryption (Fernet) | ⚠️ |
| 6 | Key rotation script | ✅ |
| 7 | Internal Docker networks | ✅ |
| 8 | Redis hardening | ✅ |
| 9 | Security headers (OWASP) | ✅ |
| 10 | Rate limiting | ✅ |

## Score: 8/10

### Deductions

**CORS (-1):** Python wildcard rejection works when `CORS_ORIGINS="*"`, but empty/unset silently passes (safe by accident, not by design). Rust only rejects wildcards in production, not dev. The fail-safe behavior of `CORSMiddleware(allow_origins=[])` blocking all cross-origin is correct but unintentional.

**Column-level encryption (-1):** Encryption infrastructure is excellent (HKDF, multi-key rotation, startup validation). However, only `mfa_secret` is actually encrypted. The `phone` field uses plain `String(30)` despite the key rotation script listing it as an encrypted column — a model/script mismatch that could cause data exposure.

### Notable Strengths
- Defense-in-depth: Caddy + app-level middleware for TLS, headers, rate limiting
- Fail-closed design: app refuses to start with missing/placeholder secrets
- Redis hardening: dangerous commands disabled, password mandatory
- Docker network isolation: databases completely unreachable externally
- MFA: full TOTP + single-use bcrypt-hashed backup codes with lockout
- Key rotation: audit-logged, dry-run capable, zero-downtime with fallback keys
