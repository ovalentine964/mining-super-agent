#!/usr/bin/env bash
# Mining Super-Agent — Database Migration (upgrade to latest)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Use the Alembic config inside src/db/
export ALEMBIC_CONFIG="${ALEMBIC_CONFIG:-src/db/alembic.ini}"

echo "▶ Running Alembic migrations (upgrade head)..."
echo "  Config: $ALEMBIC_CONFIG"
echo "  Database: ${DATABASE_URL:-postgresql://mining:***@localhost:5432/mining}"

alembic -c "$ALEMBIC_CONFIG" upgrade head

echo "✔ Migrations complete."
