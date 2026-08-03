# Security Sprint 1 — Fixes Summary

**Date**: 2026-08-04
**Status**: ✅ All 5 critical vulnerabilities fixed

---

## V-35: Rate Limiting Fails Open on Redis Failure

**Problem**: When Redis was unreachable, the rate limiter allowed ALL requests through (fail-open).

**Fix**: Added in-memory sliding window rate limiter as fallback in both the Rust gateway and Python application. When Redis is down, the in-memory limiter takes over and **blocks** requests that exceed limits (fail-closed).

### Changes

| File | Change |
|------|--------|
| `gateway/rust/src/tools/mod.rs` | Added `InMemoryRateLimiter` struct with sliding window algorithm. Modified `execute_tool` to fall back to in-memory limiter when Redis `INCR` fails. |
| `gateway/rust/src/main.rs` | Added `rate_limiter: tools::InMemoryRateLimiter` field to `AppState`. Initialized at startup. |
| `src/main.py` | Added `InMemoryRateLimiter` class and `RateLimitMiddleware` (Starlette). Configured as FastAPI middleware with Redis primary + in-memory fallback. |

**Behavior**: Redis down → in-memory limiter active → 429 Too Many Requests if limit exceeded. No request passes unvalidated.

---

## V-42: CDN Deployment Guidance

**Problem**: No documentation on how to deploy behind a CDN for IP obfuscation or domain naming best practices.

**Fix**: Created comprehensive `DEPLOYMENT.md` covering:

- **Cloudflare (free tier) setup**: Step-by-step DNS, SSL/TLS "Full (Strict)" mode, proxy headers, firewall rules
- **Caddy configuration**: Updated instructions for trusting Cloudflare proxy headers
- **Domain recommendations**: Generic/abstract naming patterns (avoid "mining", "dao", "mineral", etc.)
- **Registrar recommendations**: Privacy-focused (Namecheap, Cloudflare Registrar, Njalla)
- **Network security**: Docker isolation verification, host firewall rules
- **Production environment variables**: All required secrets documented

### Changes

| File | Change |
|------|--------|
| `DEPLOYMENT.md` | **New file** — complete deployment guide with Cloudflare CDN, domain strategy, and security hardening |

---

## V-20: Prompt Injection Defense

**Problem**: No input sanitization against prompt injection attacks. Users could attempt to override the system prompt.

**Fix**: Multi-layer defense in `superagent.py`:

1. **Pattern detection**: 25+ injection patterns checked (e.g., "ignore previous instructions", "you are now", "jailbreak", "DAN mode")
2. **Input sanitization**: Strips injection delimiters (`[SYSTEM]`, `[INST]`, `<|im_start|>system`, etc.) and role markers
3. **Logging**: All suspicious inputs logged at WARNING level with user ID and truncated content
4. **System prompt hardening**: Added rule 8 instructing the LLM to resist injection and never reveal instructions

### Changes

| File | Change |
|------|--------|
| `src/superagent.py` | Added `_INJECTION_PATTERNS` list, `_detect_injection()` function, `_sanitize_input()` function. Modified `chat()` to detect, log, sanitize, and annotate suspicious inputs. Updated `_default_system_prompt()` with anti-injection instruction (rule 8). |

---

## V-41/V-25: Internal Service URLs Leaked in Error Responses

**Problem**: Error responses contained internal service URLs like `http://geological:8001`, `http://satellite:8002`, etc., exposing infrastructure details to API clients.

**Fix**: All error responses across the Rust gateway now return generic messages. Full error details (including internal URLs) are logged server-side via `tracing::error!`.

### Changes

| File | Leaks Fixed |
|------|-------------|
| `gateway/rust/src/tools/mod.rs` | Tool execution errors, tool stats errors |
| `gateway/rust/src/tools/geo.rs` | Geological service errors, nearby sites query errors |
| `gateway/rust/src/tools/satellite.rs` | Satellite service errors, imagery query errors |
| `gateway/rust/src/tools/market.rs` | Finnhub errors, market data errors, forecast errors, call_service errors |
| `gateway/rust/src/tools/vision.rs` | Vision service errors |
| `gateway/rust/src/tools/quantum.rs` | Quantum service errors |

**Client sees**: `"Service temporarily unavailable"` or `"Service error (HTTP 502)"`
**Server logs**: Full URL, error message, status code, endpoint path

---

## V-24: JSON Schema Validation for Tool Execution

**Problem**: The Rust gateway tool executor accepted arbitrary `serde_json::Value` without validating input parameters, allowing malformed or malicious payloads to reach backend services.

**Fix**: Added parameter validation layer:

1. **`required_params`** field in `tools.yaml` — each tool declares required parameters
2. **`params_schema`** field — optional full JSON Schema for detailed validation
3. **`validate_params()` method** on `ToolRegistry` — checks required params exist and are non-null, validates against JSON Schema if provided, rejects non-object top-level types
4. **Validation gate** in `execute_tool` — returns 400 Bad Request with descriptive message before any rate limiting or service calls

### Changes

| File | Change |
|------|--------|
| `gateway/rust/src/tools/registry.rs` | Added `params_schema` and `required_params` fields to `ToolConfig`. Added `validate_params()` method. |
| `gateway/rust/src/tools/mod.rs` | Added validation call before rate limiting in `execute_tool`. |
| `gateway/rust/config/tools.yaml` | Added `required_params` to all 12 tools. |
| `gateway/rust/Cargo.toml` | Added `jsonschema = "0.17"` dependency. |

---

## Summary Table

| ID | Severity | Description | Files Changed |
|----|----------|-------------|---------------|
| V-35 | Critical | Rate limiting fails open | `main.rs`, `mod.rs`, `src/main.py` |
| V-42 | Critical | No CDN/IP obfuscation guidance | `DEPLOYMENT.md` (new) |
| V-20 | Critical | No prompt injection defense | `src/superagent.py` |
| V-41/V-25 | Critical | Internal URLs in error responses | `geo.rs`, `satellite.rs`, `market.rs`, `vision.rs`, `quantum.rs`, `mod.rs` |
| V-24 | Critical | No input schema validation | `registry.rs`, `mod.rs`, `tools.yaml`, `Cargo.toml` |

**Total files changed**: 12
**New files**: 1 (`DEPLOYMENT.md`)
