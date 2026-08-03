#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start_telegram.sh — Launch the Sovereign Resource DAO backend with Telegram
#
# This script starts uvicorn which hosts:
#   • FastAPI REST API (agents, DAO governance, blockchain, fair-deal)
#   • Voice transcription endpoint (NVIDIA NIM Whisper)
#   • Telegram bot (started automatically via ChannelRegistry in lifespan)
#
# Usage:
#   ./scripts/start_telegram.sh                    # default: port 8000, polling
#   PORT=9000 ./scripts/start_telegram.sh          # custom port
#   TELEGRAM_BOT_MODE=webhook ./scripts/start_telegram.sh  # webhook mode
#
# Required environment:
#   TELEGRAM_BOT_TOKEN   — Telegram Bot API token from @BotFather
#   NVIDIA_API_KEY       — NVIDIA NIM API key for Whisper transcription
#
# Optional:
#   BACKEND_URL          — Backend URL the bot uses for internal routing
#                          (default: http://localhost:8000)
#   TELEGRAM_WEBHOOK_URL — Public URL for webhook mode
#   TELEGRAM_WEBHOOK_HOST — Webhook listen host (default: 0.0.0.0)
#   TELEGRAM_WEBHOOK_PORT — Webhook listen port (default: 8443)
#   NVIDIA_NIM_BASE_URL  — NIM API base (default: https://integrate.api.nvidia.com/v1)
#   WHISPER_MODEL        — Whisper model override
#   CORS_ORIGINS         — Comma-separated CORS origins (default: *)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Defaults ─────────────────────────────────────────────────────────────────
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
LOG_LEVEL="${LOG_LEVEL:-info}"
WORKERS="${WORKERS:-1}"

# ── Preflight checks ────────────────────────────────────────────────────────

# Load .env if present
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "📄 Loading .env from $PROJECT_ROOT/.env"
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Check required vars
missing=()
[ -z "${TELEGRAM_BOT_TOKEN:-}" ] && missing+=("TELEGRAM_BOT_TOKEN")
[ -z "${NVIDIA_API_KEY:-}" ]     && missing+=("NVIDIA_API_KEY")

if [ ${#missing[@]} -gt 0 ]; then
    echo "❌ Missing required environment variables:"
    for var in "${missing[@]}"; do
        echo "   • $var"
    done
    echo ""
    echo "Set them in .env or export them before running."
    exit 1
fi

# ── Launch ───────────────────────────────────────────────────────────────────

echo "🌿 Sovereign Resource DAO — starting services..."
echo "   FastAPI   : http://${HOST}:${PORT}"
echo "   Voice API : http://${HOST}:${PORT}/api/v1/voice/transcribe"
echo "   Telegram  : polling mode (managed by ChannelRegistry)"
echo "   Docs      : http://${HOST}:${PORT}/docs"
echo ""

cd "$PROJECT_ROOT"

exec uvicorn src.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level "$LOG_LEVEL" \
    --workers "$WORKERS"
