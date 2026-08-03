#!/usr/bin/env bash
# Sovereign Resource DAO — Database Rollback (downgrade one step)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Use the Alembic config inside src/db/
export ALEMBIC_CONFIG="${ALEMBIC_CONFIG:-src/db/alembic.ini}"

STEPS="${1:-1}"

echo "▶ Rolling back $STEPS migration(s)..."
echo "  Config: $ALEMBIC_CONFIG"
echo "  Database: ${DATABASE_URL:-postgresql://mining:***@localhost:5432/mining}"

alembic -c "$ALEMBIC_CONFIG" downgrade "-${STEPS}"

echo "✔ Rollback complete."
