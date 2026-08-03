"""
Sovereign Resource DAO — Messaging Channel Integrations

Provides a unified registry for all communication channels (Telegram, WhatsApp,
in-app, etc.) so the FastAPI backend can discover, route to, and lifecycle-manage
each channel from a single place.

Usage from main.py:
    from src.channels import get_registry, register_default_channels

    @asynccontextmanager
    async def lifespan(app):
        await register_default_channels()
        yield
        await get_registry().shutdown_all()
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Protocol

logger = logging.getLogger(__name__)


# ── Channel Protocol ────────────────────────────────────────────────────────


class Channel(Protocol):
    """Minimal interface every channel implementation must satisfy."""

    channel_type: str  # "telegram", "whatsapp", "discord", …

    async def start(self) -> None:
        """Start listening for inbound messages."""
        ...

    async def stop(self) -> None:
        """Gracefully stop the channel."""
        ...

    async def send_message(
        self,
        recipient_id: str,
        text: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Push an outbound message to a user. Returns delivery metadata."""
        ...


# ── Channel Registry ────────────────────────────────────────────────────────


class ChannelRegistry:
    """
    Central registry for all active messaging channels.

    The backend uses this to:
      • look up a channel by type when routing outbound messages
      • start / stop every channel during app lifecycle
      • list active channels for status endpoints
    """

    def __init__(self) -> None:
        self._channels: dict[str, Channel] = {}

    def register(self, channel: Channel) -> None:
        ch_type = channel.channel_type
        if ch_type in self._channels:
            logger.warning("Overwriting existing channel '%s'", ch_type)
        self._channels[ch_type] = channel
        logger.info("Channel registered: %s", ch_type)

    def get(self, channel_type: str) -> Channel | None:
        return self._channels.get(channel_type)

    def list_channels(self) -> list[dict[str, str]]:
        return [
            {"type": ch.channel_type, "status": "active"}
            for ch in self._channels.values()
        ]

    async def start_all(self) -> None:
        """Start every registered channel concurrently."""
        if not self._channels:
            logger.info("No channels registered.")
            return
        logger.info("Starting %d channel(s)…", len(self._channels))
        await asyncio.gather(
            *(ch.start() for ch in self._channels.values()),
            return_exceptions=True,
        )

    async def shutdown_all(self) -> None:
        """Gracefully stop every channel."""
        logger.info("Shutting down channels…")
        await asyncio.gather(
            *(ch.stop() for ch in self._channels.values()),
            return_exceptions=True,
        )

    async def send_to_channel(
        self,
        channel_type: str,
        recipient_id: str,
        text: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a message via a specific channel."""
        ch = self._channels.get(channel_type)
        if ch is None:
            raise ValueError(f"Channel '{channel_type}' not registered")
        return await ch.send_message(recipient_id, text, **kwargs)


# ── Module-level singleton ──────────────────────────────────────────────────

_registry = ChannelRegistry()


def get_registry() -> ChannelRegistry:
    return _registry


# ── Convenience: build & register channels from env ─────────────────────────


async def register_default_channels() -> None:
    """
    Inspect environment variables and register every configured channel.

    Currently supported:
      • TELEGRAM_BOT_TOKEN  → Telegram polling bot
    """
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if telegram_token:
        try:
            from .telegram_bot import TelegramBotChannel

            backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
            channel = TelegramBotChannel(
                token=telegram_token,
                backend_url=backend_url,
                webhook_url=os.environ.get("TELEGRAM_WEBHOOK_URL"),
            )
            _registry.register(channel)
        except Exception:
            logger.exception("Failed to register Telegram channel")
    else:
        logger.info("TELEGRAM_BOT_TOKEN not set — skipping Telegram channel")


# ── Public re-exports (backward compat) ─────────────────────────────────────

from .telegram_bot import TelegramBot, create_telegram_bot  # noqa: E402

__all__ = [
    "Channel",
    "ChannelRegistry",
    "TelegramBot",
    "TelegramBotChannel",
    "create_telegram_bot",
    "get_registry",
    "register_default_channels",
]
