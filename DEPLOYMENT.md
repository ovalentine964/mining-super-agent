# Deployment Guide — Sovereign Resource DAO

Production deployment on Oracle Cloud Free Tier (4 ARM cores, 24 GB RAM).

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Docker | ≥ 24.0 | Docker Engine or Docker Desktop |
| Docker Compose | ≥ 2.20 | Compose V2 (plugin) |
| Domain name | — | Pointed to your server's public IP |
| Cloudflare (optional) | — | For DNS proxy, DDoS protection |
| Git | ≥ 2.30 | To clone the repository |

### Server Requirements

- **OS:** Ubuntu 22.04+ / Debian 12+ (ARM64 or AMD64)
- **RAM:** 8 GB minimum (24 GB recommended)
- **CPU:** 4 cores minimum
- **Disk:** 50 GB minimum (100 GB recommended for satellite data)
- **Ports:** 80 (HTTP), 443 (HTTPS + HTTP/3)

---

## Step 1: Clone and Configure

```bash
# Clone the repository
git clone https://github.com/sovereign-resource-dao/sovereign-resource-dao.git
cd sovereign-resource-dao

# Copy the environment template
cp config/.env.example .env
```

### Generate Secrets

```bash
# JWT keys (generate two different ones)
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"
python3 -c "import secrets; print('JWT_REFRESH_SECRET_KEY=' + secrets.token_urlsafe(64))"

# Encryption keys (generate two)
python3 -c "from cryptography.fernet import Fernet; print('API_KEYS_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
python3 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"

# Database password
python3 -c "import secrets; print('DB_PASSWORD=' + secrets.token_urlsafe(24))"

# Redis password
python3 -c "import secrets; print('REDIS_PASSWORD=' + secrets.token_urlsafe(24))"

# MinIO credentials
python3 -c "import secrets; print('MINIO_ROOT_USER=mining_admin')"
python3 -c "import secrets; print('MINIO_ROOT_PASSWORD=' + secrets.token_urlsafe(24))"
```

Paste the generated values into your `.env` file. **Never commit `.env` to git.**

### Required Variables

These must be set or the stack will refuse to start:

| Variable | Description |
|---|---|
| `DB_PASSWORD` | PostgreSQL password (≥ 20 chars) |
| `REDIS_PASSWORD` | Redis password (≥ 20 chars) |
| `MINIO_ROOT_USER` | MinIO admin username |
| `MINIO_ROOT_PASSWORD` | MinIO admin password (≥ 20 chars) |
| `JWT_SECRET_KEY` | JWT signing key |
| `JWT_REFRESH_SECRET_KEY` | JWT refresh key (different from above) |
| `API_KEYS_ENCRYPTION_KEY` | Fernet key for API key encryption |
| `ENCRYPTION_KEY` | Fernet key for general encryption |
| `CORS_ORIGINS` | Comma-separated allowed origins (no `*` in production) |

### Domain & TLS

Set your domain in `.env`:

```bash
DOMAIN=mining.yourdomain.com
ACME_EMAIL=admin@yourdomain.com
```

Caddy auto-provisions TLS via Let's Encrypt. If using Cloudflare:

1. Set DNS A record → server IP
2. Enable Cloudflare proxy (orange cloud) for DDoS protection
3. Set SSL/TLS mode to **Full (strict)** in Cloudflare dashboard

---

## Step 2: Build and Start

```bash
# Build all containers
docker compose build

# Start the full stack
docker compose up -d

# Watch startup logs
docker compose logs -f --tail=50
```

### Services Started

| Service | Port | Description |
|---|---|---|
| caddy | 80, 443 | Reverse proxy, auto-TLS |
| app | 8000 (internal) | FastAPI application |
| gateway | 8080 (internal) | Rust API gateway |
| postgres | 5432 (internal) | PostgreSQL + PostGIS |
| redis | 6379 (internal) | Cache, sessions, rate limiting |
| qdrant | 6333 (internal) | Vector database |
| minio | 9000 (internal) | S3-compatible storage |

All databases are on the internal network — no ports exposed to the host.

---

## Step 3: Verify Health

```bash
# Check all containers are running
docker compose ps

# Expected: all services "Up" with "(healthy)" status

# Test the health endpoint
curl -f https://mining.yourdomain.com/health
# Expected: {"status": "healthy"}

# Test the API
curl -f https://mining.yourdomain.com/status
# Expected: {"agents": 5, "agent_names": [...], "blockchain": {...}}

# Check Caddy TLS
curl -vI https://mining.yourdomain.com 2>&1 | grep "SSL certificate"
# Expected: SSL certificate verify ok
```

### Service Health Checks

Each service has built-in health checks. Check individual services:

```bash
# PostgreSQL
docker compose exec postgres pg_isready -U mining -d mining

# Redis
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" ping

# Qdrant
docker compose exec qdrant curl -f http://localhost:6333/healthz

# Application
docker compose exec app curl -f http://localhost:8000/health
```

---

## Step 4: Database Initialization

```bash
# Run database migrations (if using Alembic)
docker compose exec app python -m alembic upgrade head

# Verify PostGIS extension
docker compose exec postgres psql -U mining -d mining -c "SELECT PostGIS_Version();"
```

---

## Step 5: Post-Deployment Checklist

- [ ] Health endpoint returns 200
- [ ] TLS certificate valid (check expiry: `echo | openssl s_client -connect DOMAIN:443 2>/dev/null | openssl x509 -noout -dates`)
- [ ] CORS configured (no wildcards in production)
- [ ] All JWT/encryption keys are unique and securely generated
- [ ] Database passwords are strong (≥ 20 characters)
- [ ] Redis commands disabled (FLUSHALL, FLUSHDB, CONFIG, DEBUG, SHUTDOWN)
- [ ] Telegram bot connected (if configured)
- [ ] Backup script scheduled (see `scripts/backup.sh`)
- [ ] Monitoring alerts configured
- [ ] `.env` file is NOT committed to git

---

## Environment Variable Reference

See [`config/.env.example`](config/.env.example) for the complete list with descriptions.

### Variable Categories

| Category | Variables | Required |
|---|---|---|
| **Application** | `APP_ENV`, `LOG_LEVEL`, `CORS_ORIGINS` | Yes |
| **Domain/TLS** | `DOMAIN`, `ACME_EMAIL` | Yes |
| **Auth/Encryption** | `JWT_SECRET_KEY`, `JWT_REFRESH_SECRET_KEY`, `API_KEYS_ENCRYPTION_KEY`, `ENCRYPTION_KEY` | Yes |
| **Database** | `POSTGRES_DB`, `POSTGRES_USER`, `DB_PASSWORD` | Yes |
| **Cache** | `REDIS_PASSWORD` | Yes |
| **Storage** | `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` | Yes |
| **AI APIs** | `NVIDIA_API_KEY`, `GROQ_API_KEY`, etc. | No |
| **Telegram** | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_URL` | No |
| **Blockchain** | `POLYGON_RPC_URL`, `ORACLE_PRIVATE_KEY`, etc. | No |
| **Backup** | `BACKUP_S3_*` | No |

---

## Rollback Procedure

### Immediate Rollback (Docker)

```bash
# Stop the current deployment
docker compose down

# Checkout the previous known-good version
git log --oneline -5  # Find the commit hash
git checkout <previous-commit-hash>

# Rebuild and restart
docker compose build
docker compose up -d

# Verify health
curl -f https://mining.yourdomain.com/health
```

### Database Rollback

```bash
# If migrations were run, rollback the last migration
docker compose exec app python -m alembic downgrade -1

# Or restore from backup
docker compose exec postgres pg_restore -U mining -d mining /backups/latest.dump
```

### Full Restore from Backup

```bash
# Stop services (keep databases running)
docker compose stop app gateway caddy

# Restore PostgreSQL
docker compose exec -T postgres psql -U mining -d mining < backup_YYYYMMDD.sql

# Restore MinIO data
docker compose exec minio mc mirror /backups/minio/ /data/

# Restart all services
docker compose up -d

# Verify
curl -f https://mining.yourdomain.com/health
```

### Emergency: Nuclear Reset

```bash
# WARNING: This destroys ALL data (databases, uploads, cache)
docker compose down -v  # Removes volumes
docker compose up -d
# Re-run database initialization (Step 4)
```

---

## Monitoring

### Log Access

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f app
docker compose logs -f gateway

# Last 100 lines
docker compose logs --tail=100 app
```

### Resource Usage

```bash
# Container resource stats
docker stats --no-stream

# Disk usage
docker system df
```

### Backup Schedule

Set up the backup cron job:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/sovereign-resource-dao/scripts/backup.sh >> /var/log/dao-backup.log 2>&1
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| Container won't start | Check logs: `docker compose logs <service>` |
| TLS certificate fails | Verify DNS A record points to server IP; check port 443 is open |
| Database connection refused | Ensure postgres is healthy: `docker compose ps` |
| Redis auth error | Verify `REDIS_PASSWORD` matches in all services |
| Out of memory | Check `docker stats`; reduce resource limits in `docker-compose.yml` |
| Port 80/443 in use | Stop conflicting services: `sudo lsof -i :80` |
