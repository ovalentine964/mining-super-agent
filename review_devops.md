# DevOps & Infrastructure Review — Sovereign Resource DAO

**Date:** 2026-08-04
**Scope:** Docker, CI/CD, Monitoring, Backup/DR, Secrets, Networking, Operational Readiness

---

## Executive Summary

The infrastructure is **well-architected for a small-team project** — clean multi-stage Docker builds, proper network isolation in Compose, strong Caddy security headers, and solid backup/restore scripts. However, there are **critical security gaps** (CI pipelines always pass, `curl` missing in Rust healthcheck), **no observability stack** (despite `prometheus-client` being a dependency), and **no operational runbooks**. The project needs hardening before production traffic.

| Area | Grade | Key Risk |
|------|-------|----------|
| Docker & Containers | B+ | Missing `curl` in Rust runtime breaks healthcheck |
| CI/CD | D | All `\|\| true` — pipelines never fail |
| Monitoring | F | No metrics, no tracing, no alerts |
| Backup & DR | B+ | Solid scripts, missing automated scheduling |
| Secrets Management | B | Good key rotation, some gaps |
| Networking & DNS | A- | Excellent Caddy config |
| Operational Runbooks | F | None exist |

---

## 1. Docker & Container Security

### 1.1 Python Application (`Dockerfile`)

**What's good:**
- Multi-stage concept (though only one stage — "base" label suggests intent)
- `python:3.12-slim` base image — appropriate size/security tradeoff
- Non-root user (`mining:mining`) created and used
- `HEALTHCHECK` defined with interval/timeout/retries
- `--no-cache-dir` on pip install
- `apt` cleanup with `rm -rf /var/lib/apt/lists/*`

**Issues:**

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| D1 | 🔴 Critical | `COPY .env.example .env.example` copies a file with placeholder secrets into the image layer. While not real secrets, it trains bad habits and leaks the secret *structure* to anyone who pulls the image. | Remove this line. The `.env.example` is documentation, not runtime config. |
| D2 | 🟡 Medium | No image tag pinning — `python:3.12-slim` will float with patch releases. A bad upstream patch could break production silently. | Pin to digest: `python:3.12-slim@sha256:...` or use `3.12.X-slim`. |
| D3 | 🟡 Medium | Single-stage build despite the "Multi-stage build" comment. GDAL/geospatial libs are ~400MB and remain in the final image. | Split into builder (compile wheels) + runtime (copy wheels only). |
| D4 | 🟡 Medium | `pip install ".[dev]"` installs dev dependencies (ruff, mypy, black, isort, pre-commit) in the production image. | Use `pip install .` only for production. Dev tools belong in CI, not runtime. |
| D5 | 🟢 Low | No `COPY --chown=mining:mining` — the `RUN chown -R` creates an extra layer. | Use `COPY --chown=mining:mining` to avoid the chown layer. |
| D6 | 🟢 Low | No `dumb-init` or `tini` — uvicorn with `--workers 2` forks, which is fine, but signals may not propagate cleanly. | Consider `tini` as entrypoint for proper PID 1 signal handling. |

### 1.2 Rust Gateway (`gateway/rust/Dockerfile`)

**What's good:**
- Proper two-stage build (builder → runtime)
- Dependency caching trick (`echo "fn main() {}"`)
- `debian:bookworm-slim` runtime — minimal
- Non-root user
- Separate `libssl3`/`libpq5` runtime deps only

**Issues:**

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| D7 | 🔴 Critical | `HEALTHCHECK CMD curl -f http://localhost:8080/health` — but `curl` is **not installed** in `debian:bookworm-slim`. The healthcheck will **always fail**, meaning Docker/K8s will perpetually restart the container. | Install `curl` in the runtime stage: `apt-get install -y curl` (adds ~5MB), or switch to `wget` or a Rust-built health binary. |
| D8 | 🟡 Medium | No version pinning on `rust:1.79-slim`. Rust compiler version affects reproducibility. | Pin to specific patch or digest. |
| D9 | 🟡 Medium | `COPY --from=builder ... 2>/dev/null || true` swallows errors — if `config/` or `migrations/` are required at runtime, missing files won't surface until crash. | Either ensure directories exist or fail loudly. |

### 1.3 Docker Compose (`docker-compose.yml`)

**What's excellent:**
- Network isolation: `internal: true` network for databases — no port mapping to host
- Resource limits on every service (CPU + memory)
- Healthchecks on all services with `start_period`
- `depends_on` with `condition: service_healthy`
- JSON logging with rotation (`max-size: 10m`, `max-file: 3`)
- Redis security: `rename-command` disabling dangerous commands (`FLUSHALL`, `CONFIG`, `DEBUG`, `SHUTDOWN`)
- `POSTGRES_PASSWORD` / `REDIS_PASSWORD` use `${VAR:?must be set}` — fails fast on missing secrets

**Issues:**

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| D10 | 🟡 Medium | `version: "3.8"` is deprecated in modern Docker Compose (v2). Not harmful but noisy. | Remove the `version` key — Docker Compose v2 ignores it with a warning. |
| D11 | 🟡 Medium | `minio/minio:latest` — unversioned tag. Could pull a breaking change. | Pin to a specific version (e.g., `minio/minio:RELEASE.2024-XX-XX`). |
| D12 | 🟡 Medium | Qdrant has no authentication enabled — accessible to any container on the internal network. If the `app` container is compromised, Qdrant is wide open. | Enable Qdrant API key: `QDRANT__SERVICE__API_KEY`. |
| D13 | 🟢 Low | Redis password is passed via `redis-cli -a` in healthcheck — visible in `docker inspect` / process list. | Use `REDISCLI_AUTH` env var or a file-based auth approach. |
| D14 | 🟢 Low | No `tmpfs` for `/tmp` in containers — temp files go to the writable layer. | Add `tmpfs: /tmp` to app container for ephemeral data. |
| D15 | 🟢 Low | No container `read_only: true` — the app filesystem is fully writable. | Add `read_only: true` with explicit `tmpfs` mounts for writable paths. |

---

## 2. CI/CD Pipeline

### 2.1 `ci.yml` — Critical Failure

**The entire CI pipeline is non-functional as a quality gate.**

Every single lint, test, and analysis step uses `|| true`:

```yaml
- run: ruff check src/ tests/ --ignore-missing-imports || true    # Lint errors swallowed
- run: pytest tests/ -v --tb=short || true                         # Test failures swallowed
- run: cargo build --release 2>&1 || echo "Build completed with warnings"  # Build errors → "warnings"
- run: cargo test 2>&1 || echo "Tests completed with warnings"     # Test failures → "warnings"
- run: flutter analyze || true                                      # Analysis errors swallowed
- run: flutter test || true                                         # Test failures swallowed
- run: npx hardhat test || true                                     # Contract test failures swallowed
```

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| CI1 | 🔴 Critical | **All `\|\| true` must be removed.** The CI pipeline literally cannot fail. Broken code merges to `main` without any signal. | Remove every `\|\| true` and `|| echo "..."` from all steps. |
| CI2 | 🔴 Critical | No dependency vulnerability scanning (no `pip audit`, `cargo audit`, `npm audit`). Supply chain attacks go undetected. | Add `pip-audit`, `cargo audit`, `npm audit` steps. |
| CI3 | 🟡 Medium | No SAST (Static Application Security Testing) — no `bandit` for Python, no `cargo clippy` warnings-as-errors. | Add `bandit -r src/` and `cargo clippy -- -D warnings`. |
| CI4 | 🟡 Medium | No Docker image build/push in CI — images are built locally on the deployment target. | Add a Docker build + push job with vulnerability scanning (Trivy/Grype). |
| CI5 | 🟡 Medium | `pip install -r requirements-bot.txt || true` — silently ignores missing file. | Either create the file or remove the step. |
| CI6 | 🟢 Low | No branch protection enforcement documented — even if CI eventually passes, nothing blocks merge. | Require status checks in GitHub branch protection rules. |

### 2.2 `release-apk.yml`

**What's good:**
- Tag-based release workflow
- Conditional keystore signing (graceful fallback to debug)
- APK versioning and size reporting
- GitHub Release with auto-generated notes
- Artifact retention (30 days)

**Issues:**

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| CI7 | 🟡 Medium | `flutter analyze --no-fatal-infos \|\| true` and `flutter test \|\| true` — release builds can ship with failing tests. | Remove `\|\| true` for release builds. Releases should be gated on passing tests. |
| CI8 | 🟡 Medium | Keystore is decoded to disk but never cleaned up (`rm -f android/app/keystore/release.jks`). If the runner is reused, the keystore persists. | Add a `post` cleanup step or use `${{ runner.temp }}`. |
| CI9 | 🟢 Low | `cancel-in-progress: false` for releases is correct, but no concurrency guard on the build job itself — two simultaneous tag pushes could race. | Acceptable for now, but consider mutex on release artifacts. |

---

## 3. Monitoring & Observability

### 3.1 Prometheus Metrics — **Not Implemented**

`prometheus-client>=0.20.0` is listed in `pyproject.toml` but **zero Prometheus metrics are defined anywhere in the codebase**. No `Histogram`, `Counter`, `Gauge`, or `PrometheusMiddleware` exists.

**What's missing:**
- No HTTP request metrics (latency, error rate, throughput)
- No business metrics (agent calls, governance votes, oracle submissions)
- No `/metrics` endpoint
- No Prometheus scrape configuration
- No Grafana dashboards

**Recommended metrics to implement:**
```python
# HTTP metrics
http_requests_total = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
http_request_duration_seconds = Histogram('http_request_duration_seconds', 'Request latency')

# Business metrics
agent_chat_total = Counter('agent_chat_total', 'Agent chat requests', ['agent'])
oracle_submissions_total = Counter('oracle_submissions_total', 'Blockchain oracle submissions', ['status'])
governance_votes_total = Counter('governance_votes_total', 'Governance votes cast')
```

### 3.2 Logging — **Unstructured**

All logging uses Python's built-in `logging` module with basic `%(asctime)s [%(levelname)s] %(message)s` formatting. No structured (JSON) logging, no correlation IDs, no request tracing.

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| M1 | 🟡 Medium | Unstructured logs make parsing/alerting in production very difficult. | Adopt `structlog` or configure `python-json-logger` for JSON output. |
| M2 | 🟡 Medium | No request ID / correlation ID propagation. | Add middleware to inject `X-Request-ID` and propagate through all log calls. |
| M3 | 🟡 Medium | No log level configuration per module — everything is `INFO`. | Support `LOG_LEVEL` env var (already in `.env.example`) with per-module overrides. |

### 3.3 Health Checks — **Superficial**

```python
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "sovereign-resource-dao"}
```

This endpoint returns `200 healthy` **without checking anything**. It doesn't verify:
- Database connectivity
- Redis connectivity
- Qdrant connectivity
- External API availability

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| M4 | 🔴 Critical | Health check is a lie — returns healthy even if PostgreSQL is down. | Add dependency checks (db ping, redis ping) with degraded/unhealthy states. |
| M5 | 🟡 Medium | No readiness vs liveness probe separation. Kubernetes/orchestrators need distinct endpoints. | Split into `/healthz` (liveness) and `/readyz` (readiness, checks deps). |

### 3.4 Distributed Tracing — **Not Implemented**

No OpenTelemetry, Jaeger, Zipkin, or any tracing library. For a multi-service architecture (Python app + Rust gateway + external APIs), this makes debugging latency issues extremely difficult.

### 3.5 Alerting — **Not Configured**

No alerting rules, no PagerDuty/Opsgenie integration, no webhook-based alerting. The Caddy access log goes to a file with rotation, but nothing reads it.

---

## 4. Backup & Disaster Recovery

### 4.1 `backup.sh` — **Well Engineered**

**What's excellent:**
- `set -euo pipefail` — proper error handling
- SHA-256 checksums for integrity verification
- Gzip compression with `-9` (max compression)
- S3 upload with KMS encryption support
- `--schema-only` and `--dry-run` modes
- Local backup rotation (7-day retention)
- PostgreSQL dump header verification
- Comprehensive logging with timestamps

**Issues:**

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| B1 | 🔴 Critical | **No automated scheduling.** The backup script exists but nothing runs it. No cron job, no systemd timer, no CI workflow. | Add a cron job or systemd timer. Example: `0 2 * * * /path/to/backup.sh >> /var/log/backup.log 2>&1` |
| B2 | 🟡 Medium | `RETENTION_DAYS=7` for local, but S3 lifecycle rules are "managed by S3 bucket lifecycle rules" — which are not configured anywhere in the repo. | Add a `lifecycle.json` or document the required S3 lifecycle configuration. |
| B3 | 🟡 Medium | No backup of Redis data, Qdrant data, or MinIO data. Only PostgreSQL is backed up. | Add Redis BGSAVE + copy, Qdrant snapshot, and MinIO bucket sync procedures. |
| B4 | 🟢 Low | Backup file is named with `localhost:5432` (the default `pg_dump --host=localhost`). When run inside a container, this works, but the naming is confusing. | Not blocking — just cosmetic. |

### 4.2 `restore.sh` — **Solid**

**What's good:**
- S3 download capability
- Checksum verification
- Interactive confirmation (`Type 'RESTORE'`)
- Stops app before restore to prevent writes
- `pg_terminate_backend` to kill active connections
- `--single-transaction` with `ON_ERROR_STOP` for atomicity
- Post-restore verification (table count, PostGIS version)
- Restarts app after restore

**Issues:**

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| B5 | 🟡 Medium | No pre-restore backup — if the restore fails midway, both the old and new data may be corrupted. | Take a "pre-restore" backup before dropping the database. |
| B6 | 🟡 Medium | The `2>/dev/null` on `psql` commands silences errors during drop/create. | Remove stderr redirection to surface errors. |

### 4.3 RTO/RPO Estimates

| Metric | Current | Target |
|--------|---------|--------|
| RPO (Recovery Point Objective) | Up to 24h (if daily backup) | 1h (hourly backups or WAL archiving) |
| RTO (Recovery Time Objective) | ~30-60 min (manual restore) | <15 min (automated) |

**Recommendations:**
- Enable PostgreSQL WAL archiving for point-in-time recovery
- Test restore procedure monthly (document results)
- Automate the full recovery runbook

---

## 5. Secrets Management

### 5.1 `.env.example` — **Good Documentation**

Clear separation of concerns, helpful generation commands in comments, all secrets are placeholder values. The `.gitignore` correctly excludes `.env`, `*.pem`, `*.key`.

### 5.2 Secrets in Docker

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| S1 | 🟡 Medium | Secrets are passed as environment variables in `docker-compose.yml`. Visible via `docker inspect`. | Use Docker secrets (`secrets:` directive) or mount `.env` as a file. |
| S2 | 🟡 Medium | No secret rotation schedule documented. The `key_rotation.py` script exists but no runbook says when/how often to run it. | Document rotation schedule: encryption keys every 90 days, JWT secrets every 30 days. |
| S3 | 🟢 Low | `MINIO_ROOT_USER=mining_admin` is a non-default username (good), but the default in `.env.example` is still a static value. | Acceptable — it's just an example. |

### 5.3 `key_rotation.py` — **Well Designed**

**What's excellent:**
- Supports encryption key, JWT secret, and JWT refresh secret rotation
- Fernet-based database column re-encryption
- Zero-downtime rotation (old key preserved as fallback)
- JSONL audit log for every rotation event
- Dry-run mode
- `.env` file backup before modification
- HKDF key derivation for database encryption

**Issues:**

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| S4 | 🟡 Medium | The `combined_key = f"{new_key},{old_key}"` approach for zero-downtime rotation assumes the app code knows how to parse comma-separated keys. Need to verify the app's Fernet wrapper supports this. | Verify `make_fernet()` in the app tries keys in order. |
| S5 | 🟡 Medium | No validation that the new key actually works before committing the rotation. | Add a encrypt→decrypt round-trip test with the new key before updating `.env`. |
| S6 | 🟢 Low | `AUDIT_LOG_PATH` is `logs/key_rotation_audit.jsonl` — the `logs/` directory is in `.gitignore`, so audit logs are ephemeral on container restart. | Ship audit logs to a persistent store or external logging service. |

### 5.4 Secrets in Logs

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| S7 | 🟢 Low | Error messages mention API key names ("NVIDIA_API_KEY not set") but never leak actual values. Good. | No action needed. |
| S8 | 🟢 Low | Redis healthcheck passes password via CLI arg (`redis-cli -a ${REDIS_PASSWORD}`) — visible in `ps` output. | Use `REDISCLI_AUTH` env var instead. |

---

## 6. Networking & DNS

### 6.1 Caddyfile — **Excellent**

**What's outstanding:**
- Full security header suite: HSTS (2 years, preload-ready), X-Content-Type-Options, X-Frame-Options, CSP, COEP, COOP, CORP
- CSP is restrictive: `default-src 'self'`, `frame-ancestors 'none'`
- `X-XSS-Protection` (legacy but still useful)
- `Permissions-Policy` restricting camera, microphone, geolocation
- Server/Powered-By headers removed
- Tiered rate limiting: global (100/s), API (30/s), auth (5/s)
- Request body size limit (10MB)
- JSON access logging with rotation
- Per-route timeout configuration
- HTTP/3 support (port 443/udp)

**Issues:**

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| N1 | 🟡 Medium | `rate_limit` is a Caddy plugin (caddy-ratelimit) — need to verify it's included in the `caddy:2-alpine` image or build a custom image. | Verify the plugin is available, or use `xcaddy` to build with the plugin. |
| N2 | 🟢 Low | `X-XSS-Protection: 1; mode=block` is deprecated in modern browsers and can introduce vulnerabilities in older ones. | Consider removing it; CSP is the modern replacement (already configured). |
| N3 | 🟢 Low | Error handler returns plain text — no custom error pages. | Add HTML error pages for 4xx/5xx. |

### 6.2 DNS Configuration

No DNS guidance exists in the repo. The `{$DOMAIN:localhost}` Caddy variable means DNS must be configured externally.

**Recommendations:**
- Document DNS setup (A/AAAA records, CNAME for subdomains)
- Document ACME email configuration
- Add a setup guide for Let's Encrypt staging vs production

---

## 7. Operational Runbooks — **None Exist**

This is a **critical gap**. There are no runbooks, no incident response procedures, no escalation paths.

### 7.1 Missing Runbooks

| Scenario | Impact | Status |
|----------|--------|--------|
| **Service goes down** | No documented procedure. Operators must reverse-engineer from docker-compose.yml. | ❌ Missing |
| **PostgreSQL goes down** | `restore.sh` exists but no runbook for detection, triage, or communication. | ❌ Missing |
| **Redis goes down** | No documented failover. App will crash on Redis connection errors. | ❌ Missing |
| **NVIDIA API rate-limited** | `superagent.py` falls back to mock LLM, but no alerting or documentation. | ❌ Missing |
| **Deployment rollback** | `db_rollback.sh` exists for DB, but no app rollback procedure (image tag management). | ❌ Missing |
| **Certificate expiry** | Caddy auto-renews, but no monitoring for renewal failures. | ❌ Missing |
| **Disk full** | Log rotation exists, but no disk space monitoring. | ❌ Missing |
| **Security incident** | No incident response plan. | ❌ Missing |

### 7.2 Recommended Runbook Structure

```
docs/runbooks/
├── 00-incident-response.md     # General incident playbook
├── 01-service-down.md          # App container down
├── 02-database-down.md         # PostgreSQL failure
├── 03-redis-down.md            # Redis failure
├── 04-api-rate-limit.md        # External API throttling
├── 05-deployment-rollback.md   # Rollback procedure
├── 06-certificate-expiry.md    # TLS issues
├── 07-disk-full.md             # Storage issues
└── 08-security-incident.md     # Breach response
```

---

## 8. Summary of All Findings

### 🔴 Critical (Must Fix Before Production)

| ID | Area | Issue |
|----|------|-------|
| D7 | Docker | Rust Dockerfile healthcheck uses `curl` but doesn't install it — container will perpetually restart |
| CI1 | CI/CD | All `\|\| true` in CI — pipeline cannot detect any failures |
| CI2 | CI/CD | No dependency vulnerability scanning |
| M4 | Monitoring | Health check is superficial — returns healthy when deps are down |
| B1 | Backup | No automated backup scheduling |

### 🟡 Medium (Should Fix)

| ID | Area | Issue |
|----|------|-------|
| D1 | Docker | `.env.example` copied into image |
| D2 | Docker | No base image digest pinning |
| D4 | Docker | Dev dependencies in production image |
| D8 | Docker | Rust builder image not pinned |
| D11 | Docker | MinIO uses `latest` tag |
| D12 | Docker | Qdrant has no authentication |
| CI3 | CI/CD | No SAST (bandit, clippy) |
| CI4 | CI/CD | No Docker image build in CI |
| CI5 | CI/CD | Silent failure on missing requirements file |
| CI7 | CI/CD | Release APK ships with `\|\| true` on tests |
| M1 | Monitoring | Unstructured logging |
| M2 | Monitoring | No request correlation IDs |
| M3 | Monitoring | No per-module log levels |
| M5 | Monitoring | No readiness vs liveness separation |
| B2 | Backup | S3 lifecycle rules not configured |
| B3 | Backup | No Redis/Qdrant/MinIO backup |
| B5 | Backup | No pre-restore safety backup |
| S1 | Secrets | Secrets visible via `docker inspect` |
| S2 | Secrets | No rotation schedule documented |
| S4 | Secrets | Key rotation fallback unverified |
| S5 | Secrets | No key validation before rotation commit |
| N1 | Networking | Rate limit plugin may not be in stock Caddy image |

### 🟢 Low (Nice to Have)

| ID | Area | Issue |
|----|------|-------|
| D3 | Docker | Single-stage build, large image |
| D5 | Docker | No `COPY --chown` |
| D6 | Docker | No PID 1 init system |
| D9 | Docker | Swallowed errors in Rust Dockerfile |
| D10 | Docker | Deprecated compose version key |
| D13 | Docker | Redis password in healthcheck CLI args |
| D14 | Docker | No tmpfs for /tmp |
| D15 | Docker | No read-only filesystem |
| CI6 | CI/CD | No branch protection documented |
| CI8 | CI/CD | Keystore not cleaned up after signing |
| N2 | Networking | Deprecated X-XSS-Protection header |
| N3 | Networking | No custom error pages |
| S3 | Secrets | Static MinIO username in example |
| S6 | Secrets | Audit log ephemeral |
| S8 | Secrets | Redis password in process list |
| B4 | Backup | Cosmetic naming issue |
| B6 | Backup | Silenced stderr during restore |

---

## 9. Recommended Action Plan

### Phase 1: Critical Fixes (Week 1)
1. Install `curl` in Rust Dockerfile runtime stage
2. Remove all `|| true` from CI pipelines
3. Add `pip-audit` and `cargo audit` to CI
4. Implement real health checks (db/redis/qdrant ping)
5. Set up automated backup cron/timer

### Phase 2: Security Hardening (Week 2)
6. Remove `.env.example` from Dockerfile COPY
7. Pin all base image versions to digests
8. Remove dev dependencies from production image
9. Enable Qdrant authentication
10. Add Docker secrets or file-based secret injection

### Phase 3: Observability (Week 3)
11. Implement Prometheus metrics + `/metrics` endpoint
12. Switch to structured JSON logging
13. Add request ID middleware
14. Separate `/healthz` and `/readyz` endpoints
15. Set up basic alerting (Prometheus Alertmanager or webhook)

### Phase 4: Operational Maturity (Week 4)
16. Write all operational runbooks
17. Document DNS setup and certificate management
18. Add Redis/Qdrant/MinIO backup procedures
19. Implement deployment rollback procedure
20. Test full restore from backup (document RTO)
