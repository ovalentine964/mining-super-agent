#!/usr/bin/env bash
# Sovereign Resource DAO — Database Restore Script
# Restores from a gzip-compressed pg_dump backup with verification
#
# Usage:
#   ./scripts/restore.sh backup_file.sql.gz
#   ./scripts/restore.sh backup_file.sql.gz --force    # Skip confirmation
#   ./scripts/restore.sh --from-s3 backups/mining_backup_20260725.sql.gz

set -euo pipefail

# ── Configuration ───────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load environment
if [ -f "${PROJECT_DIR}/.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "${PROJECT_DIR}/.env"
    set +a
fi

DB_CONTAINER="${DB_CONTAINER:-sovereign-resource-dao-postgres-1}"
POSTGRES_USER="${POSTGRES_USER:-mining}"
POSTGRES_DB="${POSTGRES_DB:-mining}"

# S3 config
BACKUP_S3_BUCKET="${BACKUP_S3_BUCKET:-}"
BACKUP_S3_REGION="${BACKUP_S3_REGION:-us-east-1}"
BACKUP_S3_ACCESS_KEY="${BACKUP_S3_ACCESS_KEY:-}"
BACKUP_S3_SECRET_KEY="${BACKUP_S3_SECRET_KEY:-}"
BACKUP_S3_ENDPOINT="${BACKUP_S3_ENDPOINT:-}"

# ── Parse Arguments ─────────────────────────────────────────────
BACKUP_FILE=""
FROM_S3=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --from-s3)
            FROM_S3=true
            BACKUP_FILE="$2"
            shift 2
            ;;
        --force|-f)
            FORCE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 <backup_file.sql.gz> [--force]"
            echo "       $0 --from-s3 <s3_key> [--force]"
            echo ""
            echo "Options:"
            echo "  --force    Skip confirmation prompt"
            echo "  --from-s3  Download backup from S3 first"
            exit 0
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

if [ -z "${BACKUP_FILE}" ]; then
    echo "Error: No backup file specified"
    echo "Usage: $0 <backup_file.sql.gz> [--force]"
    exit 1
fi

# ── Functions ───────────────────────────────────────────────────
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
    exit 1
}

check_prerequisites() {
    if ! docker info > /dev/null 2>&1; then
        error "Docker is not running"
    fi

    if ! docker ps --format '{{.Names}}' | grep -q "${DB_CONTAINER}"; then
        error "PostgreSQL container '${DB_CONTAINER}' is not running"
    fi

    if ! command -v gzip &> /dev/null; then
        error "gzip is not installed"
    fi
}

download_from_s3() {
    local s3_key="$1"
    local local_file="${PROJECT_DIR}/.backups/$(basename "${s3_key}")"

    log "Downloading from S3: s3://${BACKUP_S3_BUCKET}/${s3_key}"

    mkdir -p "${PROJECT_DIR}/.backups"

    export AWS_ACCESS_KEY_ID="${BACKUP_S3_ACCESS_KEY}"
    export AWS_SECRET_ACCESS_KEY="${BACKUP_S3_SECRET_KEY}"

    local aws_opts=(--region "${BACKUP_S3_REGION}")
    if [ -n "${BACKUP_S3_ENDPOINT}" ]; then
        aws_opts+=(--endpoint-url "${BACKUP_S3_ENDPOINT}")
    fi

    aws s3 cp "s3://${BACKUP_S3_BUCKET}/${s3_key}" "${local_file}" "${aws_opts[@]}"

    # Download checksum if exists
    aws s3 cp "s3://${BACKUP_S3_BUCKET}/${s3_key}.sha256" "${local_file}.sha256" "${aws_opts[@]}" 2>/dev/null || true

    BACKUP_FILE="${local_file}"
    log "Downloaded to: ${BACKUP_FILE}"
}

verify_backup() {
    local file="$1"

    log "Verifying backup file: ${file}"

    # Check file exists
    if [ ! -f "${file}" ]; then
        error "Backup file not found: ${file}"
    fi

    # Check file is non-empty
    if [ ! -s "${file}" ]; then
        error "Backup file is empty: ${file}"
    fi

    # Check gzip integrity
    if ! gzip -t "${file}" 2>/dev/null; then
        error "Backup file is corrupted (gzip test failed): ${file}"
    fi

    # Verify checksum if available
    if [ -f "${file}.sha256" ]; then
        log "Verifying checksum..."
        if ! sha256sum -c "${file}.sha256" > /dev/null 2>&1; then
            error "Checksum verification failed!"
        fi
        log "Checksum verified ✓"
    else
        log "No checksum file found — skipping checksum verification"
    fi

    # Verify it starts with valid PostgreSQL dump
    if ! zcat "${file}" | head -5 | grep -q "PostgreSQL database dump"; then
        error "File does not appear to be a valid PostgreSQL dump"
    fi

    log "Backup verification passed ✓"
}

show_backup_info() {
    local file="$1"

    log ""
    log "=== Backup Information ==="

    # File size
    local size
    size=$(du -h "${file}" | cut -f1)
    log "File: ${file}"
    log "Size: ${size}"

    # Extract timestamp from filename
    if [[ "${file}" =~ mining_backup_([0-9]{8}_[0-9]{6}) ]]; then
        log "Timestamp: ${BASH_REMATCH[1]}"
    fi

    # Show first few lines of the dump
    log ""
    log "First lines of dump:"
    zcat "${file}" | head -20 | sed 's/^/  /'
    log ""
}

confirm_restore() {
    if [ "${FORCE}" = true ]; then
        return 0
    fi

    echo ""
    echo "⚠️  WARNING: This will REPLACE the entire '${POSTGRES_DB}' database!"
    echo ""
    echo "Database: ${POSTGRES_DB}"
    echo "Container: ${DB_CONTAINER}"
    echo "Backup: ${BACKUP_FILE}"
    echo ""
    read -r -p "Are you sure? Type 'RESTORE' to confirm: " confirmation

    if [ "${confirmation}" != "RESTORE" ]; then
        log "Restore cancelled"
        exit 0
    fi
}

perform_restore() {
    local file="$1"

    log "Starting restore..."

    # Stop the app to prevent writes during restore
    log "Stopping application..."
    docker compose -f "${PROJECT_DIR}/docker-compose.yml" stop app 2>/dev/null || true

    # Drop and recreate the database
    log "Dropping existing database..."
    docker exec "${DB_CONTAINER}" psql -U "${POSTGRES_USER}" -d postgres -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid != pg_backend_pid();" \
        2>/dev/null || true

    docker exec "${DB_CONTAINER}" psql -U "${POSTGRES_USER}" -d postgres -c \
        "DROP DATABASE IF EXISTS ${POSTGRES_DB};" 2>/dev/null

    docker exec "${DB_CONTAINER}" psql -U "${POSTGRES_USER}" -d postgres -c \
        "CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};" 2>/dev/null

    # Restore from backup
    log "Restoring from backup (this may take a while)..."
    zcat "${file}" | docker exec -i "${DB_CONTAINER}" \
        psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
        --single-transaction \
        --set ON_ERROR_STOP=on \
        2>&1 | tail -5

    # Verify restore
    log "Verifying restore..."
    local table_count
    table_count=$(docker exec "${DB_CONTAINER}" psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')

    log "Tables restored: ${table_count}"

    # Check PostGIS
    local postgis_version
    postgis_version=$(docker exec "${DB_CONTAINER}" psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -t -c \
        "SELECT PostGIS_Version();" 2>/dev/null | tr -d ' ')

    log "PostGIS version: ${postgis_version}"

    # Restart the app
    log "Restarting application..."
    docker compose -f "${PROJECT_DIR}/docker-compose.yml" start app 2>/dev/null || true

    log ""
    log "=== Restore Complete ==="
    log "Database '${POSTGRES_DB}' restored from ${file}"
    log "Tables: ${table_count}"
    log "PostGIS: ${postgis_version}"
}

# ── Main ────────────────────────────────────────────────────────
main() {
    log "=== Sovereign Resource DAO Database Restore ==="
    log ""

    check_prerequisites

    # Download from S3 if requested
    if [ "${FROM_S3}" = true ]; then
        download_from_s3 "${BACKUP_FILE}"
    fi

    verify_backup "${BACKUP_FILE}"
    show_backup_info "${BACKUP_FILE}"
    confirm_restore
    perform_restore "${BACKUP_FILE}"
}

main "$@"
