# Platform Engineering Plan

> **Council Member 4: Platform Lead — Infrastructure & DevOps Engineering**
> Hosting: Oracle Cloud Always Free | Budget: $0-50/month

---

## 1. Infrastructure Architecture

### 1.1 Target Environment

**Oracle Cloud Always Free Tier (ARM Ampere A1)**
- **Compute:** 4 OCPUs (ARM64), 24GB RAM *(Note: Oracle updated free tier — verify current allocation; plan assumes 2-4 OCPUs, 12-24GB RAM)*
- **Storage:** 200GB boot volume + up to 200GB block volume (free)
- **Network:** 10Gbps VNIC, 10TB/month outbound
- **OS:** Oracle Linux 8/9 or Ubuntu 22.04 ARM64

### 1.2 Service Topology

All services run on a **single VM** via Docker Compose with resource limits. This is the pragmatic "Always Free" reality — no Kubernetes, no managed services.

```
┌─────────────────────────────────────────────────────┐
│                   Oracle Cloud VM                    │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │            Caddy (TLS + Reverse Proxy)        │  │
│  │            :80 → :443, auto-HTTPS             │  │
│  └──────────────┬────────────────────────────────┘  │
│                 │                                    │
│  ┌──────────────▼────────────────────────────────┐  │
│  │         FastAPI (API Gateway)                  │  │
│  │         :8000, /api/v1/*                       │  │
│  └──────────────┬────────────────────────────────┘  │
│                 │                                    │
│  ┌──────────────▼────────────────────────────────┐  │
│  │         DeerFlow (Multi-Agent Orchestrator)    │  │
│  │         :8080, internal only                   │  │
│  └───┬──────┬──────┬──────┬──────┬───────────────┘  │
│      │      │      │      │      │                   │
│  ┌───▼─┐ ┌──▼──┐ ┌▼───┐ ┌▼───┐ ┌▼──────────────┐  │
│  │ PG  │ │Qdrnt│ │Redis│ │MinIO│ │  Celery/Workers│  │
│  │5432 │ │6333 │ │6379 │ │9000 │ │               │  │
│  └─────┘ └─────┘ └────┘ └────┘ └───────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │        Prometheus + Grafana (Monitoring)      │   │
│  │        :9090 / :3000                          │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 1.3 Docker Compose Structure

**File layout:**

```
project/
├── docker-compose.yml          # Production compose
├── docker-compose.dev.yml      # Local development overrides
├── docker-compose.monitoring.yml  # Optional monitoring stack
├── .env                        # Environment variables (gitignored)
├── Caddyfile                   # Caddy reverse proxy config
├── services/
│   ├── api/                    # FastAPI application
│   │   ├── Dockerfile
│   │   └── ...
│   ├── deerflow/               # DeerFlow orchestrator
│   │   ├── Dockerfile
│   │   └── ...
│   └── workers/                # Background task workers
│       ├── Dockerfile
│       └── ...
└── infra/
    ├── scripts/
    │   ├── deploy.sh
    │   ├── backup.sh
    │   ├── restore.sh
    │   └── healthcheck.sh
    └── prometheus/
        └── prometheus.yml
```

**`docker-compose.yml` (production):**

```yaml
version: "3.8"

x-common: &common
  restart: unless-stopped
  logging:
    driver: json-file
    options:
      max-size: "10m"
      max-file: "3"

services:
  # ── Reverse Proxy ──────────────────────────────
  caddy:
    <<: *common
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"   # HTTP/3
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.25"

  # ── API Gateway ────────────────────────────────
  api:
    <<: *common
    build:
      context: ./services/api
      dockerfile: Dockerfile
    expose:
      - "8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://${PG_USER}:${PG_PASSWORD}@postgres:5432/${PG_DB}
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - DEERFLOW_URL=http://deerflow:8080
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_started
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "1.0"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  # ── DeerFlow Orchestrator ──────────────────────
  deerflow:
    <<: *common
    build:
      context: ./services/deerflow
      dockerfile: Dockerfile
    expose:
      - "8080"
    environment:
      - REDIS_URL=redis://redis:6379/1
      - QDRANT_URL=http://qdrant:6333
    depends_on:
      - redis
      - qdrant
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.5"

  # ── Database ───────────────────────────────────
  postgres:
    <<: *common
    image: postgis/postgis:16-3.4-alpine
    expose:
      - "5432"
    environment:
      POSTGRES_USER: ${PG_USER}
      POSTGRES_PASSWORD: ${PG_PASSWORD}
      POSTGRES_DB: ${PG_DB}
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./infra/postgres/init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    deploy:
      resources:
        limits:
          memory: 3G
          cpus: "1.0"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${PG_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ── Vector Database ────────────────────────────
  qdrant:
    <<: *common
    image: qdrant/qdrant:v1.12.1
    expose:
      - "6333"
      - "6334"   # gRPC
    volumes:
      - qdrant_data:/qdrant/storage
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "0.5"

  # ── Cache / Message Broker ─────────────────────
  redis:
    <<: *common
    image: redis:7-alpine
    expose:
      - "6379"
    command: >
      redis-server
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --appendfsync everysec
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          memory: 768M
          cpus: "0.25"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  # ── Object Storage ─────────────────────────────
  minio:
    <<: *common
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    expose:
      - "9000"   # S3 API
      - "9001"   # Console (internal only)
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "0.25"

  # ── Background Workers ─────────────────────────
  worker:
    <<: *common
    build:
      context: ./services/api
      dockerfile: Dockerfile
      target: worker
    command: celery -A app.celery_app worker --loglevel=info --concurrency=2
    environment:
      - DATABASE_URL=postgresql+asyncpg://${PG_USER}:${PG_PASSWORD}@postgres:5432/${PG_DB}
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
    depends_on:
      - postgres
      - redis
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "0.5"
      replicas: 1

volumes:
  pg_data:
  qdrant_data:
  redis_data:
  minio_data:
  caddy_data:
  caddy_config:

networks:
  default:
    name: prod-network
```

### 1.4 Resource Budget

| Service | RAM Limit | CPU Limit | Notes |
|---------|-----------|-----------|-------|
| Caddy | 256M | 0.25 | Static files + TLS termination |
| FastAPI | 1G | 1.0 | API gateway, handles requests |
| DeerFlow | 2G | 1.5 | Multi-agent orchestration (heaviest) |
| PostgreSQL | 3G | 1.0 | Primary database |
| Qdrant | 2G | 0.5 | Vector search |
| Redis | 768M | 0.25 | Cache + message broker |
| MinIO | 512M | 0.25 | Object storage |
| Worker | 1G | 0.5 | Background tasks |
| Monitoring | 512M | 0.25 | Prometheus + Grafana (optional) |
| **Total** | **~11.3G** | **5.5** | Fits within 12G / 4 OCPU |

### 1.5 Network Security

```
Internet
    │
    ▼
┌──────────┐
│  Oracle   │  Security List: Allow 80, 443 only
│  Cloud    │  SSH: Allow from specific IP only
│  VCN      │
└────┬─────┘
     │
┌────▼─────────────────────────────┐
│  Caddy (TLS termination)         │  ← Only exposed service
├──────────────────────────────────┤
│  Docker internal network         │  ← All other services internal
│  ┌──────┐ ┌──────┐ ┌──────┐    │
│  │ API  │ │ PG   │ │Redis │    │  No port publishing
│  └──────┘ └──────┘ └──────┘    │  expose ≠ ports
└──────────────────────────────────┘
```

**Security rules:**
- Only Caddy publishes ports (80, 443)
- All other services use `expose` (internal Docker network only)
- PostgreSQL has no external port mapping
- SSH restricted to specific IPs via Oracle Cloud Security List
- UFW enabled as secondary firewall
- Fail2ban for SSH protection

---

## 2. CI/CD Pipeline

### 2.1 Pipeline Architecture

```
GitHub Push → GitHub Actions → Build Images → SSH Deploy → Health Check
     │              │               │              │            │
     │         Lint + Test     Docker Build    SCP + SSH    Curl + Retry
     │         Security Scan   Multi-arch      docker       Rollback
     │         (optional)      (ARM64)         compose up   on failure
```

### 2.2 GitHub Actions Workflow

**`.github/workflows/deploy.yml`:**

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_PREFIX: ${{ github.repository }}

jobs:
  # ── Test & Lint ────────────────────────────────
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          cd services/api
          pip install -r requirements.txt -r requirements-dev.txt

      - name: Run tests
        run: |
          cd services/api
          pytest tests/ -v --tb=short

      - name: Lint
        run: |
          cd services/api
          ruff check .
          ruff format --check .

  # ── Build & Push ───────────────────────────────
  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    strategy:
      matrix:
        service: [api, deerflow, worker]
    steps:
      - uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ./services/${{ matrix.service }}
          push: true
          platforms: linux/arm64
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_PREFIX }}-${{ matrix.service }}:latest
            ${{ env.REGISTRY }}/${{ env.IMAGE_PREFIX }}-${{ matrix.service }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ── Deploy ─────────────────────────────────────
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production
    concurrency: deploy-production
    steps:
      - uses: actions/checkout@v4

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            set -euo pipefail
            cd /opt/project

            # Pull new images
            docker compose pull

            # Deploy with zero-downtime rolling restart
            docker compose up -d --remove-orphans

            # Wait for health check
            sleep 10
            for i in $(seq 1 12); do
              if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
                echo "✅ Health check passed"
                exit 0
              fi
              echo "⏳ Attempt $i/12..."
              sleep 5
            done

            echo "❌ Health check failed, rolling back..."
            docker compose down
            docker compose -f docker-compose.prev.yml up -d
            exit 1

      - name: Notify on failure
        if: failure()
        run: |
          # Send alert via webhook (Telegram, Discord, etc.)
          curl -s -X POST "${{ secrets.ALERT_WEBHOOK_URL }}" \
            -H "Content-Type: application/json" \
            -d '{"text": "⚠️ Deployment failed for ${{ github.sha }}"}'
```

### 2.3 Deployment Script

**`infra/scripts/deploy.sh` (manual deployment option):**

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/opt/project"
BACKUP_DIR="/opt/backups/compose"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

cd "$PROJECT_DIR"

echo "📦 Saving current state..."
cp docker-compose.yml "$BACKUP_DIR/docker-compose.${TIMESTAMP}.yml"

echo "🔄 Pulling latest images..."
docker compose pull

echo "🚀 Deploying..."
docker compose up -d --remove-orphans

echo "🏥 Health check..."
sleep 10
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Deployment successful"
    # Clean up old compose backups (keep last 5)
    ls -t "$BACKUP_DIR"/docker-compose.*.yml | tail -n +6 | xargs -r rm
else
    echo "❌ Health check failed!"
    echo "🔙 Rolling back..."
    cp "$BACKUP_DIR/docker-compose.${TIMESTAMP}.yml" docker-compose.yml
    docker compose up -d --remove-orphans
    exit 1
fi
```

### 2.4 Branching Strategy

```
main ──────────────────────────────────────────────── (production)
  │
  ├── feature/xxx ── PR ── test + lint ── merge ──→ main → deploy
  │
  └── hotfix/xxx ── PR ── test ── merge ──→ main → deploy (fast)
```

- **Simple trunk-based** development (single developer, small team)
- All PRs run tests + lint
- Merge to `main` triggers auto-deploy
- `workflow_dispatch` for manual deploys when needed

---

## 3. Monitoring & Alerting

### 3.1 Monitoring Stack

**Lightweight stack that fits within resource limits:**

| Component | Purpose | Port | RAM |
|-----------|---------|------|-----|
| Prometheus | Metrics collection | 9090 | 256M |
| Grafana | Dashboards | 3000 | 192M |
| node-exporter | Host metrics | 9100 | 32M |
| postgres-exporter | DB metrics | 9187 | 32M |

**`docker-compose.monitoring.yml`:**

```yaml
version: "3.8"

services:
  prometheus:
    image: prom/prometheus:v2.53.0
    volumes:
      - ./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.retention.time=15d"
      - "--storage.tsdb.retention.size=5GB"
    expose:
      - "9090"
    deploy:
      resources:
        limits:
          memory: 256M

  grafana:
    image: grafana/grafana:11.1.0
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
      GF_SERVER_ROOT_URL: "https://your-domain.com/grafana"
    expose:
      - "3000"
    deploy:
      resources:
        limits:
          memory: 192M

  node-exporter:
    image: prom/node-exporter:v1.8.1
    command:
      - "--path.rootfs=/host"
    volumes:
      - /:/host:ro,rslave
    expose:
      - "9100"
    deploy:
      resources:
        limits:
          memory: 32M

  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:v0.15.0
    environment:
      DATA_SOURCE_NAME: "postgresql://${PG_USER}:${PG_PASSWORD}@postgres:5432/${PG_DB}?sslmode=disable"
    expose:
      - "9187"
    deploy:
      resources:
        limits:
          memory: 32M

volumes:
  prometheus_data:
  grafana_data:
```

### 3.2 Prometheus Configuration

**`infra/prometheus/prometheus.yml`:**

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alerts.yml"

alerting:
  alertmanagers: []   # Using simple webhook alerts via Grafana

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "node"
    static_configs:
      - targets: ["node-exporter:9100"]

  - job_name: "postgres"
    static_configs:
      - targets: ["postgres-exporter:9187"]

  - job_name: "redis"
    static_configs:
      - targets: ["redis:6379"]
    metrics_path: /metrics

  - job_name: "qdrant"
    static_configs:
      - targets: ["qdrant:6333"]
    metrics_path: /metrics

  - job_name: "caddy"
    static_configs:
      - targets: ["caddy:2019"]
    metrics_path: /metrics
```

### 3.3 Key Metrics to Monitor

| Category | Metric | Alert Threshold |
|----------|--------|-----------------|
| **Host** | CPU usage | > 85% for 5min |
| **Host** | Memory usage | > 90% for 2min |
| **Host** | Disk usage | > 80% |
| **Host** | Disk I/O wait | > 20% for 5min |
| **API** | Request latency (p95) | > 2s |
| **API** | Error rate (5xx) | > 5% for 2min |
| **API** | Request rate | Baseline ± 200% |
| **PostgreSQL** | Active connections | > 80% of max |
| **PostgreSQL** | Replication lag | N/A (single node) |
| **PostgreSQL** | Query duration (slow) | > 1s average |
| **Redis** | Memory usage | > 80% of limit |
| **Redis** | Connected clients | > 1000 |
| **Qdrant** | Collection health | Any yellow/red |
| **MinIO** | Disk usage | > 80% |
| **Docker** | Container restarts | Any restart |

### 3.4 Alerting

**Simple alerting via Grafana → Telegram webhook (no Alertmanager needed):**

```yaml
# Grafana alert rule example (provisioned via API or UI)
# Alerts → Contact Points → Telegram Bot

# For Telegram notifications, use Grafana's built-in contact point:
# Type: Telegram
# Bot Token: ${TELEGRAM_BOT_TOKEN}
# Chat ID: ${TELEGRAM_CHAT_ID}
```

**Alternative: Simple script-based monitoring**

**`infra/scripts/healthcheck.sh` (crontab every 5 min):**

```bash
#!/usr/bin/env bash
set -euo pipefail

ALERT_WEBHOOK="${TELEGRAM_ALERT_WEBHOOK}"
HOSTNAME=$(hostname)

check_service() {
    local name=$1
    local url=$2
    local expected=${3:-200}

    status=$(curl -sf -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    if [ "$status" != "$expected" ]; then
        send_alert "🔴 $name is DOWN (HTTP $status)"
        return 1
    fi
    return 0
}

send_alert() {
    local message=$1
    curl -sf -X POST "$ALERT_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"[$HOSTNAME] $message\"}" || true
}

# Check services
check_service "API" "http://localhost:8000/health"
check_service "Caddy" "http://localhost:80" "301"  # Redirect to HTTPS

# Check disk
disk_usage=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$disk_usage" -gt 80 ]; then
    send_alert "💾 Disk usage at ${disk_usage}%"
fi

# Check memory
mem_usage=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
if [ "$mem_usage" -gt 90 ]; then
    send_alert "🧠 Memory usage at ${mem_usage}%"
fi

# Check container restarts
restarts=$(docker inspect --format='{{.Name}}: {{.RestartCount}}' $(docker ps -q) 2>/dev/null | awk -F': ' '$2 > 0')
if [ -n "$restarts" ]; then
    send_alert "🔄 Container restarts detected: $restarts"
fi
```

### 3.5 Logging Strategy

**Centralized logging with Docker's json-file driver + logrotate:**

```yaml
# In docker-compose.yml (already configured via x-common)
x-common: &common
  logging:
    driver: json-file
    options:
      max-size: "10m"
      max-file: "3"
```

**Log access:**

```bash
# View logs for a service
docker compose logs -f api --tail 100

# Search logs
docker compose logs api 2>&1 | grep "ERROR"

# Export logs for debugging
docker compose logs --since 1h api > /tmp/api-logs.txt
```

**For production-grade logging (if budget allows):**
- Loki + Promtail (lightweight, Grafana-native)
- Or simply ship logs to an external service (e.g., free tier of Betterstack/Logtail)

---

## 4. Backup & Recovery

### 4.1 Backup Strategy

```
┌─────────────────────────────────────────────┐
│              Backup Architecture             │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────┐    ┌──────────┐              │
│  │PostgreSQL│    │  MinIO   │              │
│  │ pg_dump  │    │ mc mirror│              │
│  └────┬─────┘    └────┬─────┘              │
│       │               │                     │
│       ▼               ▼                     │
│  ┌──────────────────────────┐              │
│  │   /opt/backups/daily/    │              │
│  │   (local, 7-day rotate)  │              │
│  └────────────┬─────────────┘              │
│               │                             │
│               ▼                             │
│  ┌──────────────────────────┐              │
│  │  Oracle Object Storage   │              │
│  │  (20GB free, lifecycle)  │              │
│  └──────────────────────────┘              │
│               │                             │
│               ▼                             │
│  ┌──────────────────────────┐              │
│  │  rclone → S3-compatible  │              │
│  │  (optional, weekly)      │              │
│  └──────────────────────────┘              │
└─────────────────────────────────────────────┘
```

### 4.2 PostgreSQL Backup

**`infra/scripts/backup.sh`:**

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/opt/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting PostgreSQL backup..."

# Dump all databases with compression
docker compose exec -T postgres pg_dumpall -U "${PG_USER}" | gzip > "${BACKUP_DIR}/pg_${TIMESTAMP}.sql.gz"

# Verify backup
if [ -s "${BACKUP_DIR}/pg_${TIMESTAMP}.sql.gz" ]; then
    SIZE=$(du -h "${BACKUP_DIR}/pg_${TIMESTAMP}.sql.gz" | cut -f1)
    echo "✅ Backup complete: pg_${TIMESTAMP}.sql.gz ($SIZE)"
else
    echo "❌ Backup failed!"
    exit 1
fi

# Rotate old backups
find "$BACKUP_DIR" -name "pg_*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "🔄 Rotated backups older than $RETENTION_DAYS days"

# Upload to Oracle Object Storage (if configured)
if command -v oci &> /dev/null; then
    echo "☁️  Uploading to Oracle Object Storage..."
    oci os object put \
        --bucket-name backups \
        --file "${BACKUP_DIR}/pg_${TIMESTAMP}.sql.gz" \
        --name "postgres/pg_${TIMESTAMP}.sql.gz" \
        --force
fi
```

### 4.3 Qdrant Backup

```bash
# Qdrant snapshot
curl -X POST "http://localhost:6333/collections/{collection_name}/snapshots"
# Download snapshot
curl -o /opt/backups/qdrant/snapshot.snapshot \
    "http://localhost:6333/collections/{collection_name}/snapshots/{snapshot_name}"
```

### 4.4 Redis Backup

Redis uses AOF (already configured in compose). Additionally:

```bash
# Trigger BGSAVE
docker compose exec redis redis-cli BGSAVE

# Copy RDB file
docker compose cp redis:/data/dump.rdb /opt/backups/redis/dump_$(date +%Y%m%d).rdb
```

### 4.5 MinIO Backup

```bash
# Using mc (MinIO client)
mc mirror local/bucket /opt/backups/minio/bucket/

# Or use rclone for remote sync
rclone sync /opt/backups/ remote:bucket/backups/
```

### 4.6 Recovery Procedures

**`infra/scripts/restore.sh`:**

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh /opt/backups/postgres/
    exit 1
fi

echo "⚠️  WARNING: This will restore the database from $BACKUP_FILE"
read -p "Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo "🔄 Stopping API and workers..."
docker compose stop api worker

echo "📥 Restoring database..."
gunzip -c "$BACKUP_FILE" | docker compose exec -T postgres psql -U "${PG_USER}" -d postgres

echo "🚀 Restarting services..."
docker compose start api worker

echo "🏥 Health check..."
sleep 10
curl -sf http://localhost:8000/health && echo "✅ Restore successful" || echo "❌ Health check failed"
```

### 4.7 Backup Schedule

| What | Frequency | Retention | Method |
|------|-----------|-----------|--------|
| PostgreSQL | Daily 03:00 | 7 local + 30 cloud | pg_dump + gzip |
| Qdrant | Weekly | 4 weeks | Snapshot API |
| Redis | Daily | 3 days | BGSAVE + copy |
| MinIO | Daily | 7 days | mc mirror |
| Docker configs | On deploy | 10 versions | Git + compose backup |

**Crontab:**

```cron
# Backups
0 3 * * * /opt/project/infra/scripts/backup.sh >> /var/log/backup.log 2>&1
0 4 * * 0 /opt/project/infra/scripts/backup_qdrant.sh >> /var/log/backup.log 2>&1

# Health checks
*/5 * * * * /opt/project/infra/scripts/healthcheck.sh

# Log rotation
0 2 * * * docker system prune -f --filter "until=168h" >> /var/log/docker-prune.log 2>&1
```

---

## 5. Scaling Strategy

### 5.1 Current Capacity Estimates

| Resource | Free Tier | Typical Usage | Headroom |
|----------|-----------|---------------|----------|
| CPU | 4 OCPU | 20-40% avg | 60% |
| RAM | 24GB | 11GB allocated | 13GB |
| Storage | 200GB | ~50GB (DB + vectors) | 150GB |
| Network | 10TB/mo | ~100GB/mo | 9.9TB |
| Requests | Unlimited | ~1K-10K/day | Very high |

### 5.2 Scaling Triggers

```
┌─────────────────────────────────────────────────────┐
│                 Scaling Decision Tree                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  CPU > 80% sustained?                              │
│  ├─ YES → Optimize queries → Add worker → Scale up │
│  └─ NO  → Monitor                                  │
│                                                     │
│  RAM > 85% sustained?                              │
│  ├─ YES → Tune PG shared_buffers → Scale up        │
│  └─ NO  → Monitor                                  │
│                                                     │
│  Disk > 70%?                                       │
│  ├─ YES → Archive old data → Add volume → Scale up │
│  └─ NO  → Monitor                                  │
│                                                     │
│  Response time p95 > 2s?                           │
│  ├─ YES → Profile → Cache → Optimize → Scale       │
│  └─ NO  → Monitor                                  │
│                                                     │
│  Concurrent users > 50?                            │
│  ├─ YES → Connection pooling → Read replicas        │
│  └─ NO  → Monitor                                  │
└─────────────────────────────────────────────────────┘
```

### 5.3 Vertical Scaling (Within Free Tier)

**Optimization before scaling:**

```yaml
# PostgreSQL tuning for 12GB+ RAM
postgres:
  command: >
    postgres
    -c shared_buffers=2GB
    -c effective_cache_size=6GB
    -c work_mem=64MB
    -c maintenance_work_mem=512MB
    -c max_connections=100
    -c random_page_cost=1.1
    -c effective_io_concurrency=200
    -c wal_buffers=64MB
    -c max_wal_size=2GB
    -c checkpoint_completion_target=0.9
```

### 5.4 Horizontal Scaling (When Budget Allows)

**Phase 1: $0/month (Current)**
- Single Oracle Cloud free VM
- All services on one machine
- Good for: Development, MVP, < 100 users

**Phase 2: $25-50/month**
- Upgrade to **pay-as-you-go** ARM instance (always free covers most)
- Add **Cloudflare** (free) for CDN + DDoS protection
- Add **UptimeRobot** (free) for external monitoring
- Add **external PostgreSQL** (e.g., Neon free tier) for managed backups

**Phase 3: $50-100/month**
- Second VM for **read replica** or **worker separation**
- **Managed PostgreSQL** (e.g., Supabase free → paid, or Neon)
- **Cloudflare R2** instead of MinIO (free egress)

**Phase 4: $100+/month**
- Kubernetes (k3s) on 2-3 VMs
- Managed database (Supabase Pro, or RDS)
- Dedicated Qdrant cloud
- Full observability stack

### 5.5 Cost-Effective Scaling Alternatives

| Need | Free/Low-Cost Solution |
|------|----------------------|
| CDN | Cloudflare (free) |
| DNS | Cloudflare (free) |
| Monitoring | UptimeRobot (free, 50 monitors) |
| Error tracking | Sentry (free tier) |
| Object storage | Cloudflare R2 (free 10GB) |
| Managed DB | Neon (free 512MB), Supabase (free 500MB) |
| Email | Resend (free 3K/mo) |
| Logs | Betterstack (free 1GB/day) |

---

## 6. Big Tech Standards & Best Practices

### 6.1 How Google Does Platform Engineering

**Google's SRE Principles (adapted for small projects):**

| Principle | Google Standard | Our Adaptation |
|-----------|----------------|----------------|
| **Error Budgets** | 99.9% SLO = 0.1% error budget | 99% SLO (3.6 days/yr downtime acceptable for MVP) |
| **Toil Reduction** | Automate everything > 2x manual | Shell scripts for deploy, backup, recovery |
| **Blameless Postmortems** | Document every incident | Simple incident log in `docs/incidents/` |
| **Monitoring** | The four golden signals | Latency, traffic, errors, saturation (basic Prometheus) |
| **Capacity Planning** | Quarterly reviews | Monthly resource check in Grafana |
| **Change Management** | Progressive rollouts | Health checks + rollback in CI/CD |

### 6.2 Meta's Infrastructure Philosophy

| Meta Practice | Our Version |
|---------------|-------------|
| **Move fast with stable infra** | Auto-deploy on merge, but with tests + health checks |
| **Dogfooding** | Use the system yourself before exposing to users |
| **Infrastructure as Code** | Docker Compose + GitHub Actions = reproducible |
| **Observability-first** | Metrics before features (add Prometheus early) |
| **Blast radius reduction** | Resource limits, health checks, automatic rollback |

### 6.3 SRE Best Practices Checklist

```
✅  Deployment
    ├── [  ] Zero-downtime deploys (rolling restart)
    ├── [  ] Automated rollback on health check failure
    ├── [  ] Deployment manifest versioned in Git
    ├── [  ] Canary/staging environment (optional)
    └── [  ] Deploy window (avoid Friday afternoon)

✅  Monitoring
    ├── [  ] Health check endpoints on all services
    ├── [  ] Latency, traffic, errors, saturation metrics
    ├── [  ] Alert on-call for critical issues
    ├── [  ] Dashboard for quick status overview
    └── [  ] Log aggregation and search

✅  Reliability
    ├── [  ] SLO defined (e.g., 99% availability)
    ├── [  ] Error budget tracked
    ├── [  ] Incident response documented
    ├── [  ] Postmortem template ready
    └── [  ] Runbook for common issues

✅  Security
    ├── [  ] TLS everywhere (Caddy auto-HTTPS)
    ├── [  ] No exposed database ports
    ├── [  ] Secrets in .env, never in Git
    ├── [  ] Regular dependency updates
    └── [  ] SSH key-only auth, fail2ban

✅  Backup & Recovery
    ├── [  ] Daily automated backups
    ├── [  ] Backup verification (test restore quarterly)
    ├── [  ] Recovery time objective (RTO) < 1 hour
    ├── [  ] Recovery point objective (RPO) < 24 hours
    └── [  ] Off-site backup storage
```

### 6.4 The "12-Factor App" Compliance

| Factor | Implementation |
|--------|---------------|
| I. Codebase | One repo, Git-versioned |
| II. Dependencies | Docker images, pinned versions |
| III. Config | Environment variables (.env) |
| IV. Backing services | Docker network addresses |
| V. Build/Release/Run | GitHub Actions → Docker → Compose |
| VI. Processes | Stateless API, state in PG/Redis |
| VII. Port binding | Caddy binds ports, services internal |
| VIII. Concurrency | Docker Compose scaling + workers |
| IX. Disposability | Fast startup, graceful shutdown |
| X. Dev/Prod parity | Docker Compose for both |
| XI. Logs | stdout/stderr → Docker json-file |
| XII. Admin processes | One-off scripts in infra/scripts/ |

---

## 7. Operational Runbook

### 7.1 Common Operations

```bash
# ── Deployment ──────────────────────────────────
git push origin main                    # Auto-deploy via GitHub Actions
# OR manual:
cd /opt/project && ./infra/scripts/deploy.sh

# ── Service Management ──────────────────────────
docker compose ps                       # View running services
docker compose logs -f api              # Tail API logs
docker compose restart api              # Restart a service
docker compose down && docker compose up -d  # Full restart

# ── Database ────────────────────────────────────
docker compose exec postgres psql -U $PG_USER -d $PG_DB   # Connect
docker compose exec postgres pg_dump -U $PG_USER $PG_DB > backup.sql  # Manual backup

# ── Debugging ───────────────────────────────────
docker stats                            # Resource usage
docker compose top                      # Process list
docker compose exec api bash            # Shell into container
curl -s http://localhost:8000/health    # Health check

# ── Cleanup ─────────────────────────────────────
docker system prune -f                  # Remove unused images
docker volume prune -f                  # Remove unused volumes (careful!)
docker compose down -v                  # Stop and remove volumes (DANGER)
```

### 7.2 Incident Response

```
1. DETECT    → Alert fires (Telegram/notification)
2. TRIAGE    → Check Grafana dashboard, docker compose ps
3. MITIGATE  → Restart service, rollback deployment
4. DIAGNOSE  → Check logs, metrics, recent changes
5. FIX       → Hotfix PR, emergency deploy
6. DOCUMENT  → Write incident report in docs/incidents/
```

### 7.3 Maintenance Windows

| Task | Frequency | When | Downtime |
|------|-----------|------|----------|
| OS updates | Monthly | Sunday 04:00 | ~5min (reboot) |
| Docker updates | Monthly | With OS updates | Rolling |
| Dependency updates | Weekly | Monday morning | Rolling |
| Security patches | As needed | ASAP | Rolling |
| Backup verification | Quarterly | Any time | None |

---

## 8. Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│                  PLATFORM QUICK REF                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🚀 Deploy:     git push → auto-deploy (or deploy.sh)  │
│  📊 Monitor:    Grafana :3000 / Prometheus :9090        │
│  💾 Backup:     Daily 03:00, retained 7 days            │
│  🔍 Logs:       docker compose logs -f <service>        │
│  🏥 Health:     curl http://localhost:8000/health        │
│  🔧 DB:         docker compose exec postgres psql       │
│  🔄 Restart:    docker compose restart <service>         │
│  ⏪ Rollback:   ./infra/scripts/deploy.sh (auto)        │
│  📈 Scale:      See scaling decision tree               │
│                                                         │
│  Key Paths:                                             │
│  /opt/project/                    # Project root        │
│  /opt/backups/                    # Backup storage      │
│  /var/log/backup.log              # Backup logs         │
│                                                         │
│  Emergency:                                               │
│  docker compose down              # Stop everything     │
│  docker compose up -d             # Start everything    │
│  ./infra/scripts/restore.sh FILE  # Restore DB          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Summary

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Deployment** | Docker Compose on single VM | Simple, fits free tier, reproducible |
| **CI/CD** | GitHub Actions → SSH deploy | Free, integrated, auto-rollback |
| **Monitoring** | Prometheus + Grafana | Lightweight, free, powerful |
| **Alerting** | Telegram webhooks | Free, instant, mobile-friendly |
| **Backup** | pg_dump + cron + cloud upload | Reliable, automated, tested |
| **Scaling** | Vertical first, horizontal later | Free tier → $50/mo path |
| **Standards** | 12-Factor + SRE-lite | Industry best practices, adapted |

**Philosophy:** Start simple, automate early, monitor everything, scale when needed. The best infrastructure is the one you actually maintain.

---

*Platform Engineering Plan v1.0 — Council Member 4*
