"""
Sovereign Resource DAO — Messaging Channel Integrations

Architecture Overview
═══════════════════════════════════════════════════════════════════════════

                        ┌─────────────────────────────────────┐
                        │        FastAPI Backend (main.py)     │
                        │  /api/v1/channels/*  +  /ws/channels │
                        └──────────┬──────────────┬────────────┘
                                   │              │
                    ┌──────────────┘              └──────────────┐
                    │                                            │
        ┌───────────▼───────────┐              ┌─────────────────▼──────────┐
        │   Telegram Bot        │              │   WhatsApp Business Bot    │
        │   (telegram_bot.py)   │              │   (whatsapp_bot.py)        │
        │                       │              │                            │
        │   python-telegram-bot │              │   Meta Cloud API           │
        │   ↓ webhook/polling   │              │   ↓ webhook receiver       │
        │   ↓ photo → AI agent  │              │   ↓ media download → AI    │
        │   ↓ inline buttons    │              │   ↓ interactive messages   │
        └───────────┬───────────┘              └──────────┬─────────────────┘
                    │                                     │
                    │   Both bots share:                  │
                    │   • MessageRouter (routes to AI)    │
                    │   • MediaHandler (download/upload)  │
                    │   • ChannelRegistry (user ↔ channel)│
                    │   • EventBus (WebSocket to Flutter) │
                    └─────────────┬───────────────────────┘
                                  │
                        ┌─────────▼─────────┐
                        │   AI Agent Pool    │
                        │   (resource scan,  │
                        │    community Q&A,  │
                        │    data analysis)  │
                        └───────────────────┘

Message Flow (e.g., Telegram photo analysis):
  1. User sends photo to @SovereignDAO_bot
  2. telegram_bot.py receives update via webhook
  3. MediaHandler downloads the photo, stores in S3/object storage
  4. MessageRouter creates a ChannelMessage and dispatches to AI pipeline
  5. AI agent (e.g., ResourceAnalyzer) processes the image
  6. Response routed back through the originating channel
  7. Simultaneously pushed to Flutter app via WebSocket
"""

from .telegram_bot import TelegramBot, create_telegram_bot
from .whatsapp_bot import WhatsAppBot, create_whatsapp_bot

__all__ = [
    "TelegramBot",
    "create_telegram_bot",
    "WhatsAppBot",
    "create_whatsapp_bot",
]
