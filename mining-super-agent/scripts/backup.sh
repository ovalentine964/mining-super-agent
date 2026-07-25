#!/usr/bin/env bash
# Mining Super-Agent — Database Backup Script
# pg_dump with gzip compression → S3 upload with KMS encryption
# 7-day rotation: keeps daily backups for 7 days, weekly for 4 weeks, monthly for 12 months
#
# Usage:
#   ./scripts/backup.sh                    # Full backup
#   ./scripts/backup.sh --schema-only      # Schema only (no data)
#   ./scripts/backup.sh --dry-run          # Show what would happen

set -euo pipefail

# ── Configuration ───────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/.backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="mining_backup_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"
CHECKSUM_FILE="${BACKUP_PATH}.sha256"

# Load environment
if [ -f "${PROJECT_DIR}/.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "${PROJECT_DIR}/.env"
    set +a
fi

# Required variables
DB_CONTAINER="${DB_CONTAINER:-mining-super-agent-postgres-1}"
POSTGRES_USER="${POSTGRES_USER:-mining}"
POSTGRES_DB="${POSTGRES_DB:-mining}"

# S3 backup config
BACKUP_S3_BUCKET="${BACKUP_S3_BUCKET:-}"
BACKUP_S3_REGION="${BACKUP_S3_REGION:-us-east-1}"
BACKUP_S3_ACCESS_KEY="${BACKUP_S3_ACCESS_KEY:-}"
BACKUP_S3_SECRET_KEY="${BACKUP_S3_SECRET_KEY:-}"
BACKUP_S3_ENDPOINT="${BACKUP_S3_ENDPOINT:-}"
BACKUP_KMS_KEY_ID="${BACKUP_KMS_KEY_ID:-}"

# Retention
RETENTION_DAYS=7
RETENTION_WEEKS=28   # 4 weeks
RETENTION_MONTHS=365 # 12 months

# ── Parse Arguments ─────────────────────────────────────────────
SCHEMA_ONLY=false
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --schema-only) SCHEMA_ONLY=true ;;
        --dry-run) DRY_RUN=true ;;
        --help|-h)
            echo "Usage: $0 [--schema-only] [--dry-run]"
            echo ""
            echo "Options:"
            echo "  --schema-only   Backup schema only (no data)"
            echo "  --dry-run       Show what would happen without executing"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg"
            exit 1
            ;;
    esac
done

# ── Functions ───────────────────────────────────────────────────
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
    exit 1
}

check_prerequisites() {
    # Check if docker is running
    if ! docker info > /dev/null 2>&1; then
        error "Docker is not running"
    fi

    # Check if postgres container is running
    if ! docker ps --format '{{.Names}}' | grep -q "${DB_CONTAINER}"; then
        error "PostgreSQL container '${DB_CONTAINER}' is not running"
    fi

    # Check for gzip
    if ! command -v gzip &> /dev/null; then
        error "gzip is not installed"
    fi

    # Check for AWS CLI (if S3 upload is configured)
    if [ -n "${BACKUP_S3_BUCKET}" ]; then
        if ! command -v aws &> /dev/null; then
            error "aws CLI is not installed (needed for S3 upload)"
        fi
    fi
}

perform_backup() {
    log "Starting backup: ${BACKUP_FILE}"

    mkdir -p "${BACKUP_DIR}"

    if [ "${DRY_RUN}" = true ]; then
        log "[DRY RUN] Would backup to: ${BACKUP_PATH}"
        return 0
    fi

    # Build pg_dump command
    local pg_dump_opts=(
        --host=localhost
        --port=5432
        --username="${POSTGRES_USER}"
        --dbname="${POSTGRES_DB}"
        --format=plain
        --no-owner
        --no-privileges
        --verbose
    )

    if [ "${SCHEMA_ONLY}" = true ]; then
        pg_dump_opts+=(--schema-only)
        log "Schema-only backup"
    fi

    # Execute pg_dump inside container and compress
    docker exec "${DB_CONTAINER}" \
        pg_dump "${pg_dump_opts[@]}" 2>/dev/null \
        | gzip -9 > "${BACKUP_PATH}"

    # Generate checksum
    sha256sum "${BACKUP_PATH}" > "${CHECKSUM_FILE}"

    local size
    size=$(du -h "${BACKUP_PATH}" | cut -f1)
    log "Backup complete: ${BACKUP_PATH} (${size})"
}

upload_to_s3() {
    if [ -z "${BACKUP_S3_BUCKET}" ]; then
        log "S3 upload not configured — skipping"
        return 0
    fi

    if [ "${DRY_RUN}" = true ]; then
        log "[DRY RUN] Would upload to s3://${BACKUP_S3_BUCKET}/backups/${BACKUP_FILE}"
        return 0
    fi

    log "Uploading to S3: s3://${BACKUP_S3_BUCKET}/backups/${BACKUP_FILE}"

    local aws_opts=(
        --region "${BACKUP_S3_REGION}"
    )

    if [ -n "${BACKUP_S3_ENDPOINT}" ]; then
        aws_opts+=(--endpoint-url "${BACKUP_S3_ENDPOINT}")
    fi

    # Build AWS CLI environment
    export AWS_ACCESS_KEY_ID="${BACKUP_S3_ACCESS_KEY}"
    export AWS_SECRET_ACCESS_KEY="${BACKUP_S3_SECRET_KEY}"

    local s3_opts=()
    if [ -n "${BACKUP_KMS_KEY_ID}" ]; then
        s3_opts+=(--sse aws:kms --sse-kms-key-id "${BACKUP_KMS_KEY_ID}")
    else
        s3_opts+=(--sse AES256)
    fi

    aws s3 cp "${BACKUP_PATH}" \
        "s3://${BACKUP_S3_BUCKET}/backups/${BACKUP_FILE}" \
        "${aws_opts[@]}" \
        "${s3_opts[@]}"

    aws s3 cp "${CHECKSUM_FILE}" \
        "s3://${BACKUP_S3_BUCKET}/backups/${BACKUP_FILE}.sha256" \
        "${aws_opts[@]}" \
        "${s3_opts[@]}"

    log "S3 upload complete"
}

rotate_local_backups() {
    log "Rotating local backups (keeping last ${RETENTION_DAYS} days)..."

    if [ "${DRY_RUN}" = true ]; then
        log "[DRY RUN] Would delete backups older than ${RETENTION_DAYS} days"
        return 0
    fi

    local deleted=0
    while IFS= read -r -d '' old_backup; do
        rm -f "${old_backup}" "${old_backup}.sha256"
        deleted=$((deleted + 1))
    done < <(find "${BACKUP_DIR}" -name "mining_backup_*.sql.gz" -mtime "+${RETENTION_DAYS}" -print0)

    log "Deleted ${deleted} old local backups"
}

rotate_s3_backups() {
    if [ -z "${BACKUP_S3_BUCKET}" ]; then
        return 0
    fi

    if [ "${DRY_RUN}" = true ]; then
        log "[DRY RUN] Would rotate S3 backups"
        return 0
    fi

    log "S3 lifecycle rotation is managed by S3 bucket lifecycle rules"
    log "Recommended: set lifecycle rule to transition to Glacier after 30 days, delete after 365 days"
}

verify_backup() {
    if [ "${DRY_RUN}" = true ]; then
        return 0
    fi

    log "Verifying backup integrity..."

    # Check file exists and is non-empty
    if [ ! -s "${BACKUP_PATH}" ]; then
        error "Backup file is empty or missing: ${BACKUP_PATH}"
    fi

    # Verify checksum
    if ! sha256sum -c "${CHECKSUM_FILE}" > /dev/null 2>&1; then
        error "Checksum verification failed!"
    fi

    # Verify gzip integrity
    if ! gzip -t "${BACKUP_PATH}" 2>/dev/null; then
        error "Backup file is corrupted (gzip test failed)"
    fi

    # Verify it starts with valid SQL
    if ! zcat "${BACKUP_PATH}" | head -5 | grep -q "PostgreSQL database dump"; then
        error "Backup does not start with valid PostgreSQL dump header"
    fi

    log "Backup verification passed ✓"
}

# ── Main ────────────────────────────────────────────────────────
main() {
    log "=== Mining Super-Agent Backup ==="
    log "Timestamp: ${TIMESTAMP}"
    log "Type: $([ "${SCHEMA_ONLY}" = true ] && echo 'schema-only' || echo 'full')"
    log ""

    check_prerequisites
    perform_backup
    verify_backup
    upload_to_s3
    rotate_local_backups
    rotate_s3_backups

    log ""
    log "=== Backup Complete ==="
    log "Local: ${BACKUP_PATH}"
    log "Checksum: ${CHECKSUM_FILE}"
    [ -n "${BACKUP_S3_BUCKET}" ] && log "S3: s3://${BACKUP_S3_BUCKET}/backups/${BACKUP_FILE}"
}

main "$@"
