"""
Sovereign Resource DAO — Telegram Bot Integration

Connects to the FastAPI backend and handles:
  • User linking (/link CODE)
  • Photo/document analysis (sends to AI agent pipeline)
  • Community resource queries
  • Inline keyboards for DAO governance
  • Group chat support for community channels
"""

import asyncio
import io
import logging
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel, Field

# Fair Deal Calculator (direct import — runs in-process, no network)
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', '..'))
from src.tools.fair_deal import evaluate_offer, evaluate_valentine_offer

# ── Telegram Bot Library ─────────────────────────────────────────────────────
# Using python-telegram-bot v20+ (async)
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    InputMediaPhoto,
    Message,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)


# ── Models ───────────────────────────────────────────────────────────────────


class ChannelType(str, Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    DISCORD = "discord"
    IN_APP = "inApp"


class ProcessedResult(BaseModel):
    """Result from AI agent processing."""

    text: str
    media_url: str | None = None
    media_type: str | None = None  # photo, document, etc.
    inline_keyboard: list[list[dict[str, str]]] | None = None
    parse_mode: str = "Markdown"


class UserSession(BaseModel):
    """Tracks per-user conversation state."""

    telegram_user_id: int
    chat_id: int
    linked_account_id: str | None = None
    is_linked: bool = False
    link_code: str | None = None
    current_mode: str = "default"  # default, awaiting_photo, awaiting_location
    thread_id: str | None = None
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    context: dict[str, Any] = Field(default_factory=dict)


# ── Backend API Client ───────────────────────────────────────────────────────


class BackendClient:
    """Async HTTP client for the FastAPI backend."""

    def __init__(self, base_url: str, bot_token: str):
        self.base_url = base_url.rstrip("/")
        self.bot_token = bot_token
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(60.0, connect=10.0),
            headers={"X-Channel": "telegram"},
        )

    async def close(self):
        await self._client.aclose()

    # ── Channel Management ──────────────────────────────────────────────

    async def register_webhook(self, webhook_url: str) -> dict:
        """Register the Telegram webhook URL with the backend."""
        resp = await self._client.post(
            "/api/v1/channels/telegram/webhook-register",
            json={"webhook_url": webhook_url, "bot_token": self.bot_token},
        )
        resp.raise_for_status()
        return resp.json()

    async def verify_link_code(self, code: str, telegram_user_id: int, chat_id: int) -> dict:
        """Verify a user's link code and bind their Telegram to their DAO account."""
        resp = await self._client.post(
            "/api/v1/channels/telegram/verify-link",
            json={
                "link_code": code,
                "telegram_user_id": telegram_user_id,
                "chat_id": chat_id,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def get_user_context(self, telegram_user_id: int) -> dict | None:
        """Get the linked DAO account context for a Telegram user."""
        resp = await self._client.get(
            f"/api/v1/channels/telegram/user/{telegram_user_id}"
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    # ── Message Routing ─────────────────────────────────────────────────

    async def route_message(
        self,
        telegram_user_id: int,
        chat_id: int,
        message_type: str,
        text: str | None = None,
        media_bytes: bytes | None = None,
        media_filename: str | None = None,
        media_mime: str | None = None,
        location: dict | None = None,
        thread_id: str | None = None,
        raw_update: dict | None = None,
    ) -> dict:
        """
        Route an incoming message to the AI agent pipeline.

        This is the core routing function. For photos:
          1. Uploads media to backend object storage
          2. Backend dispatches to appropriate AI agent
          3. Returns the AI response (possibly async via callback)

        For text: routes to the community Q&A or task agent.
        """
        # Upload media first if present
        media_url = None
        if media_bytes:
            media_url = await self._upload_media(
                media_bytes, media_filename or "upload", media_mime or "application/octet-stream"
            )

        resp = await self._client.post(
            "/api/v1/channels/route",
            json={
                "source_channel": "telegram",
                "sender_id": str(telegram_user_id),
                "sender_chat_id": str(chat_id),
                "message_type": message_type,
                "text": text,
                "media_url": media_url,
                "location": location,
                "thread_id": thread_id,
                "raw_payload": raw_update,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def _upload_media(
        self, data: bytes, filename: str, content_type: str
    ) -> str:
        """Upload media to the backend's object storage, returns the URL."""
        resp = await self._client.post(
            "/api/v1/media/upload",
            files={"file": (filename, io.BytesIO(data), content_type)},
        )
        resp.raise_for_status()
        return resp.json()["url"]

    async def send_delivery_receipt(self, message_id: str, status: str):
        """Notify backend that a message was delivered/read."""
        await self._client.post(
            "/api/v1/channels/receipt",
            json={"message_id": message_id, "status": status},
        )


# ── Telegram Bot ─────────────────────────────────────────────────────────────


class TelegramBot:
    """
    Sovereign Resource DAO Telegram Bot.

    Features:
      /start     — Welcome & link instructions
      /link      — Link Telegram account to DAO identity
      /unlink    — Unlink Telegram account
      /status    — Show DAO membership & linked channels
      /resources — Browse community resources
      /propose   — Submit a governance proposal
      /vote      — Vote on active proposals
      /analyze   — Send a photo for AI resource analysis

    Photo messages are automatically routed to the AI agent pipeline.
    """

    def __init__(
        self,
        token: str,
        backend_url: str,
        webhook_url: str | None = None,
        allowed_user_ids: set[int] | None = None,
    ):
        self.token = token
        self.backend_url = backend_url
        self.webhook_url = webhook_url
        self.allowed_user_ids = allowed_user_ids  # None = allow all

        self.backend = BackendClient(backend_url, token)
        self.sessions: dict[int, UserSession] = {}  # chat_id → session

        self._app: Application | None = None

    # ── Application Setup ───────────────────────────────────────────────

    def build_application(self) -> Application:
        """Build and configure the telegram.ext Application."""
        app = Application.builder().token(self.token).build()

        # Commands
        app.add_handler(CommandHandler("start", self._handle_start))
        app.add_handler(CommandHandler("link", self._handle_link))
        app.add_handler(CommandHandler("unlink", self._handle_unlink))
        app.add_handler(CommandHandler("status", self._handle_status))
        app.add_handler(CommandHandler("resources", self._handle_resources))
        app.add_handler(CommandHandler("propose", self._handle_propose))
        app.add_handler(CommandHandler("vote", self._handle_vote))
        app.add_handler(CommandHandler("analyze", self._handle_analyze))
        app.add_handler(CommandHandler("fairdeal", self._handle_fairdeal))
        app.add_handler(CommandHandler("help", self._handle_help))

        # Media handlers
        app.add_handler(MessageHandler(filters.PHOTO, self._handle_photo))
        app.add_handler(MessageHandler(filters.Document.ALL, self._handle_document))
        app.add_handler(MessageHandler(filters.VIDEO, self._handle_video))
        app.add_handler(MessageHandler(filters.LOCATION, self._handle_location))
        app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, self._handle_audio))

        # Text messages (non-command)
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self._handle_text
        ))

        # Callback queries (inline keyboard buttons)
        app.add_handler(CallbackQueryHandler(self._handle_callback))

        # Error handler
        app.add_error_handler(self._handle_error)

        # Set bot commands for the menu
        app.post_init = self._post_init

        self._app = app
        return app

    async def _post_init(self, app: Application):
        """Set bot commands after initialization."""
        await app.bot.set_my_commands([
            BotCommand("start", "Welcome & link your DAO account"),
            BotCommand("link", "Link Telegram to your DAO identity"),
            BotCommand("status", "Show your DAO status & channels"),
            BotCommand("resources", "Browse community resources"),
            BotCommand("analyze", "Send a photo for AI analysis"),
            BotCommand("fairdeal", "Check if a mining offer is fair"),
            BotCommand("propose", "Submit a governance proposal"),
            BotCommand("vote", "Vote on active proposals"),
            BotCommand("help", "Show all commands"),
        ])

    # ── Access Control ──────────────────────────────────────────────────

    def _check_access(self, user_id: int) -> bool:
        if self.allowed_user_ids is None:
            return True
        return user_id in self.allowed_user_ids

    def _get_session(self, chat_id: int, user_id: int) -> UserSession:
        if chat_id not in self.sessions:
            self.sessions[chat_id] = UserSession(
                telegram_user_id=user_id,
                chat_id=chat_id,
                thread_id=str(uuid.uuid4()),
            )
        session = self.sessions[chat_id]
        session.last_activity = datetime.now(timezone.utc)
        return session

    # ── Command Handlers ────────────────────────────────────────────────

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Welcome message with linking instructions."""
        if not update.effective_user:
            return

        user = update.effective_user
        if not self._check_access(user.id):
            await update.message.reply_text("⛔ Access denied.")
            return

        session = self._get_session(update.effective_chat.id, user.id)

        if session.is_linked:
            await update.message.reply_text(
                f"🌿 Welcome back, **{user.first_name}**!\n\n"
                "Your Telegram is linked to the Sovereign Resource DAO.\n\n"
                "📸 Send me a photo to analyze resources\n"
                "🗺️ Share your location to find nearby resources\n"
                "💬 Ask me anything about the community\n\n"
                "Type /help for all commands.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "🌿 **Welcome to Sovereign Resource DAO!**\n\n"
                "This bot connects you to the DAO's AI-powered resource "
                "management system.\n\n"
                "**To get started, link your account:**\n"
                "1. Open the Sovereign DAO mobile app\n"
                "2. Go to Settings → Channels → Link Telegram\n"
                "3. Copy the code and send it here:\n"
                "   `/link YOUR-CODE`\n\n"
                "📸 Once linked, you can send photos for AI analysis!\n"
                "🗺️ Share locations to discover nearby resources!",
                parse_mode="Markdown",
            )

    async def _handle_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Link Telegram account to DAO identity using a code."""
        if not update.effective_user or not update.message:
            return

        user = update.effective_user
        if not self._check_access(user.id):
            return

        args = context.args
        if not args:
            await update.message.reply_text(
                "📎 Usage: `/link YOUR-CODE`\n\n"
                "Get a code from the Sovereign DAO app:\n"
                "Settings → Channels → Link Telegram",
                parse_mode="Markdown",
            )
            return

        code = args[0].strip().upper()
        session = self._get_session(update.effective_chat.id, user.id)

        try:
            result = await self.backend.verify_link_code(
                code=code,
                telegram_user_id=user.id,
                chat_id=update.effective_chat.id,
            )

            session.is_linked = True
            session.linked_account_id = result.get("account_id")
            session.link_code = None

            await update.message.reply_text(
                "✅ **Account linked successfully!**\n\n"
                f"DAO Account: `{result.get('account_id', 'verified')}`\n"
                f"Community: {result.get('community_name', 'Sovereign Resource DAO')}\n\n"
                "You can now:\n"
                "📸 Send photos for AI resource analysis\n"
                "🗺️ Share locations to find resources\n"
                "💬 Ask questions about your community\n\n"
                "Type /help for all commands.",
                parse_mode="Markdown",
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                await update.message.reply_text(
                    "❌ Invalid or expired code.\n"
                    "Generate a new one in the app and try again."
                )
            elif e.response.status_code == 409:
                await update.message.reply_text(
                    "⚠️ This code has already been used.\n"
                    "Generate a new one in the app."
                )
            else:
                await update.message.reply_text(
                    "❌ Linking failed. Please try again later."
                )
        except Exception:
            logger.exception("Link verification failed")
            await update.message.reply_text("❌ An error occurred. Please try again.")

    async def _handle_unlink(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Unlink Telegram from DAO account."""
        if not update.effective_user or not update.message:
            return
        session = self._get_session(update.effective_chat.id, update.effective_user.id)
        session.is_linked = False
        session.linked_account_id = None
        await update.message.reply_text("🔓 Telegram account unlinked.")

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's DAO status and linked channels."""
        if not update.effective_user or not update.message:
            return

        user = update.effective_user
        session = self._get_session(update.effective_chat.id, user.id)

        if not session.is_linked:
            await update.message.reply_text(
                "❌ Not linked. Use /link to connect your DAO account."
            )
            return

        try:
            ctx = await self.backend.get_user_context(user.id)
            if ctx:
                channels = ctx.get("linked_channels", [])
                channel_list = "\n".join(
                    f"  • {ch['type']}: {'✅' if ch['status'] == 'connected' else '❌'}"
                    for ch in channels
                ) or "  None"

                await update.message.reply_text(
                    f"📊 **Your DAO Status**\n\n"
                    f"Account: `{ctx.get('account_id', 'N/A')}`\n"
                    f"Community: {ctx.get('community_name', 'N/A')}\n"
                    f"Role: {ctx.get('role', 'member')}\n\n"
                    f"**Linked Channels:**\n{channel_list}",
                    parse_mode="Markdown",
                )
            else:
                await update.message.reply_text("📊 Unable to fetch status.")
        except Exception:
            await update.message.reply_text("❌ Failed to fetch status.")

    async def _handle_resources(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Browse community resources with inline keyboard."""
        if not update.effective_user or not update.message:
            return

        keyboard = [
            [
                InlineKeyboardButton("🌲 Forests", callback_data="resources:forest"),
                InlineKeyboardButton("💧 Water", callback_data="resources:water"),
            ],
            [
                InlineKeyboardButton("🌾 Agriculture", callback_data="resources:agriculture"),
                InlineKeyboardButton("⛏️ Minerals", callback_data="resources:minerals"),
            ],
            [
                InlineKeyboardButton("📊 My Reports", callback_data="resources:my_reports"),
                InlineKeyboardButton("🗺️ Map View", callback_data="resources:map"),
            ],
        ]

        await update.message.reply_text(
            "🌍 **Community Resources**\n\n"
            "Select a category to explore:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    async def _handle_propose(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Submit a governance proposal."""
        if not update.effective_user or not update.message:
            return

        session = self._get_session(update.effective_chat.id, update.effective_user.id)
        if not session.is_linked:
            await update.message.reply_text("❌ Link your account first: /link")
            return

        if not context.args:
            await update.message.reply_text(
                "📋 **Submit a Proposal**\n\n"
                "Usage: `/propose Title | Description`\n\n"
                "Example:\n"
                "`/propose New Water Well | Install a solar-powered "
                "well near the northern settlement`\n\n"
                "Or send a detailed proposal with /propose and follow the prompts.",
                parse_mode="Markdown",
            )
            return

        text = " ".join(context.args)
        parts = text.split("|", 1)
        title = parts[0].strip()
        description = parts[1].strip() if len(parts) > 1 else ""

        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"propose:confirm:{title[:50]}"),
                InlineKeyboardButton("❌ Cancel", callback_data="propose:cancel"),
            ],
        ]

        await update.message.reply_text(
            f"📋 **New Proposal**\n\n"
            f"**Title:** {title}\n"
            f"**Description:** {description or '(none)'}\n\n"
            f"Confirm submission?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    async def _handle_vote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vote on active proposals."""
        if not update.effective_user or not update.message:
            return

        session = self._get_session(update.effective_chat.id, update.effective_user.id)
        if not session.is_linked:
            await update.message.reply_text("❌ Link your account first: /link")
            return

        # Fetch active proposals from backend
        try:
            resp = await self.backend._client.get("/api/v1/governance/proposals/active")
            resp.raise_for_status()
            proposals = resp.json().get("proposals", [])

            if not proposals:
                await update.message.reply_text("📭 No active proposals to vote on.")
                return

            for proposal in proposals[:5]:  # Show max 5
                keyboard = [
                    [
                        InlineKeyboardButton("👍 Yes", callback_data=f"vote:yes:{proposal['id']}"),
                        InlineKeyboardButton("👎 No", callback_data=f"vote:no:{proposal['id']}"),
                        InlineKeyboardButton("🤷 Abstain", callback_data=f"vote:abstain:{proposal['id']}"),
                    ],
                ]
                await update.message.reply_text(
                    f"📋 **{proposal['title']}**\n\n"
                    f"{proposal.get('description', '')}\n\n"
                    f"Votes: 👍 {proposal.get('yes_votes', 0)} | "
                    f"👎 {proposal.get('no_votes', 0)} | "
                    f"🤷 {proposal.get('abstain_votes', 0)}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown",
                )
        except Exception:
            await update.message.reply_text("❌ Failed to load proposals.")

    async def _handle_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Prompt user to send a photo for analysis."""
        if not update.message:
            return
        session = self._get_session(update.effective_chat.id, update.effective_user.id)
        session.current_mode = "awaiting_photo"
        await update.message.reply_text(
            "📸 **Ready for Analysis!**\n\n"
            "Send me a photo and I'll analyze it using AI.\n\n"
            "I can identify:\n"
            "• 🌲 Forest cover & deforestation\n"
            "• 💧 Water bodies & quality indicators\n"
            "• 🌾 Crop health & agricultural patterns\n"
            "• 🏗️ Infrastructure & land use\n"
            "• 🐛 Environmental threats\n\n"
            "Just send the photo directly!",
            parse_mode="Markdown",
        )

    async def _handle_fairdeal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Fair Deal Calculator — evaluate if a mining offer is fair or exploitative."""
        if not update.effective_user or not update.message:
            return

        user = update.effective_user
        if not self._check_access(user.id):
            return

        session = self._get_session(update.effective_chat.id, user.id)

        # If no arguments, start interactive flow
        if not context.args:
            session.current_mode = "awaiting_fairdeal"
            session.context["fairdeal_step"] = "offer_amount"
            await update.message.reply_text(
                "⚖️ **Fair Deal Calculator**\n\n"
                "I'll help you check if a mining offer is fair.\n\n"
                "**Step 1:** What is the offer amount (in KES)?\n"
                "Example: `1000000` for 1 million KES\n\n"
                "Or use `/fairdeal valentine` for a pre-loaded analysis "
                "of Valentine's situation in Nyatike.",
                parse_mode="Markdown",
            )
            return

        # Quick command: /fairdeal valentine
        if context.args[0].lower() == "valentine":
            await update.message.reply_text("⚖️ Calculating fair deal analysis...")
            try:
                verdict = evaluate_valentine_offer()
                await self._send_fairdeal_verdict(update, verdict)
            except Exception as e:
                logger.exception("Fair deal calculation failed")
                await update.message.reply_text(f"❌ Calculation failed: {e}")
            return

        # Inline: /fairdeal <amount> <mineral1,mineral2>
        try:
            offer_amount = float(context.args[0])
            minerals_raw = context.args[1] if len(context.args) > 1 else "gold"
            mineral_names = [m.strip() for m in minerals_raw.split(",")]

            minerals = [
                {"mineral": m, "estimated_kg": 100, "confidence": 0.3}
                for m in mineral_names
            ]

            await update.message.reply_text("⚖️ Calculating fair deal analysis...")
            verdict = evaluate_offer(
                offer_amount_kes=offer_amount,
                minerals=minerals,
            )
            await self._send_fairdeal_verdict(update, verdict)
        except (ValueError, IndexError):
            await update.message.reply_text(
                "❌ Invalid format. Use:\n"
                "`/fairdeal valentine` — pre-loaded analysis\n"
                "`/fairdeal 1000000 gold,copper` — custom analysis",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.exception("Fair deal calculation failed")
            await update.message.reply_text(f"❌ Calculation failed: {e}")

    async def _send_fairdeal_verdict(self, update: Update, verdict):
        """Send a bilingual fair deal verdict to the user."""
        verdict_emoji = {
            "FAIR": "✅",
            "BELOW_MARKET": "⚠️",
            "EXPLOITATIVE": "🚨",
            "SEVERELY_EXPLOITATIVE": "🔴",
        }.get(verdict.verdict, "❓")

        text = (
            f"{verdict_emoji} **FAIR DEAL VERDICT: {verdict.verdict}**\n\n"
            f"**📊 Offer:** KES {verdict.offer_amount_kes:,.0f}\n"
            f"**💰 Estimated Land Value:** KES {verdict.estimated_total_value_kes:,.0f}\n"
            f"**⚖️ Fair Share (10-20%):** KES {verdict.fair_share_kes:,.0f}\n"
            f"**📈 Offer/Fair Ratio:** {verdict.exploitation_ratio * 100:.1f}%\n\n"
            f"**── Swahili ──**\n{verdict.explanation_sw}\n\n"
            f"**── English ──**\n{verdict.explanation_en}\n"
        )

        if verdict.recommended_actions:
            actions = "\n".join(f"• {a}" for a in verdict.recommended_actions)
            text += f"\n**📋 Recommended Actions:**\n{actions}"

        await update.message.reply_text(text, parse_mode="Markdown")

    async def _handle_fairdeal_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE,
        session: UserSession, text: str,
    ):
        """Handle multi-step fair deal conversation flow."""
        step = session.context.get("fairdeal_step", "offer_amount")

        if step == "offer_amount":
            # Parse the offer amount
            cleaned = text.replace(",", "").replace(" ", "").upper()
            multiplier = 1.0
            if cleaned.endswith("K"):
                multiplier = 1_000;
                cleaned = cleaned[:-1]
            elif cleaned.endswith("M"):
                multiplier = 1_000_000;
                cleaned = cleaned[:-1]

            try:
                offer_amount = float(cleaned) * multiplier
                session.context["fairdeal_offer"] = offer_amount
                session.context["fairdeal_step"] = "minerals"
                await update.message.reply_text(
                    f"✅ Offer: KES {offer_amount:,.0f}\n\n"
                    f"**Step 2:** What minerals are involved?\n"
                    f"Example: `gold,copper` or `gold`\n\n"
                    f"Common minerals: gold, copper, silver, coltan, cassiterite",
                    parse_mode="Markdown",
                )
            except ValueError:
                await update.message.reply_text(
                    "❌ Please enter a valid number. Example: `1000000` or `1M`",
                    parse_mode="Markdown",
                )
            return

        if step == "minerals":
            mineral_names = [m.strip().lower() for m in text.split(",") if m.strip()]
            if not mineral_names:
                await update.message.reply_text("❌ Please enter at least one mineral name.")
                return

            offer_amount = session.context.get("fairdeal_offer", 0)
            minerals = [
                {"mineral": m, "estimated_kg": 100, "confidence": 0.3}
                for m in mineral_names
            ]

            # Reset session state
            session.current_mode = "default"
            session.context.pop("fairdeal_step", None)
            session.context.pop("fairdeal_offer", None)

            await update.message.reply_text(
                f"⚖️ Calculating: KES {offer_amount:,.0f} for {', '.join(mineral_names)}..."
            )

            try:
                verdict = evaluate_offer(
                    offer_amount_kes=offer_amount,
                    minerals=minerals,
                )
                await self._send_fairdeal_verdict(update, verdict)
            except Exception as e:
                logger.exception("Fair deal calculation failed")
                await update.message.reply_text(f"❌ Calculation failed: {e}")

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show all available commands."""
        if not update.message:
            return
        await update.message.reply_text(
            "🌿 **Sovereign Resource DAO Bot**\n\n"
            "**Account:**\n"
            "/start — Welcome & setup\n"
            "/link CODE — Link your DAO account\n"
            "/unlink — Disconnect Telegram\n"
            "/status — Your DAO status\n\n"
            "**Resources:**\n"
            "/resources — Browse community resources\n"
            "/analyze — Send photo for AI analysis\n"
            "/fairdeal — Check if a mining offer is fair\n\n"
            "**Governance:**\n"
            "/propose Title | Description — Submit proposal\n"
            "/vote — Vote on active proposals\n\n"
            "**Tips:**\n"
            "📸 Just send a photo anytime for instant analysis!\n"
            "🗺️ Share your location to find nearby resources.\n"
            "💬 Ask me anything in plain text!",
            parse_mode="Markdown",
        )

    # ── Media Handlers ──────────────────────────────────────────────────

    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages — download and route to AI agent pipeline."""
        if not update.message or not update.effective_user:
            return

        user = update.effective_user
        if not self._check_access(user.id):
            return

        session = self._get_session(update.effective_chat.id, user.id)
        session.current_mode = "default"

        # Send "processing" indicator
        processing_msg = await update.message.reply_text("🔄 Analyzing your photo...")

        try:
            # Get the largest available photo
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)

            # Download photo bytes
            photo_bytes = bytearray()
            await file.download_as_bytearray(bytearray_obj=photo_bytes)

            # Route to AI agent pipeline via backend
            result = await self.backend.route_message(
                telegram_user_id=user.id,
                chat_id=update.effective_chat.id,
                message_type="photo",
                text=update.message.caption,
                media_bytes=bytes(photo_bytes),
                media_filename=f"tg_photo_{photo.file_id[-8:]}.jpg",
                media_mime="image/jpeg",
                thread_id=session.thread_id,
                raw_update={"file_id": photo.file_id, "width": photo.width, "height": photo.height},
            )

            # Edit the processing message with the AI response
            await processing_msg.delete()

            response_text = result.get("text", "Analysis complete.")
            parse_mode = result.get("parse_mode", "Markdown")

            # If there's a media response (annotated image, etc.)
            media_url = result.get("media_url")
            if media_url:
                await update.message.reply_photo(
                    photo=media_url,
                    caption=response_text[:1024],  # Telegram caption limit
                    parse_mode=parse_mode,
                )
            else:
                # Split long messages (Telegram limit: 4096 chars)
                for chunk in self._split_message(response_text, 4000):
                    await update.message.reply_text(
                        chunk, parse_mode=parse_mode,
                    )

            # Add inline keyboard if provided
            keyboard_data = result.get("inline_keyboard")
            if keyboard_data:
                keyboard = [
                    [InlineKeyboardButton(btn["text"], callback_data=btn["callback_data"])
                     for btn in row]
                    for row in keyboard_data
                ]
                await update.message.reply_text(
                    "What would you like to do next?",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )

            # Send delivery receipt
            await self.backend.send_delivery_receipt(
                result.get("message_id", ""), "delivered"
            )

        except Exception as e:
            logger.exception("Photo handling failed")
            try:
                await processing_msg.edit_text(
                    "❌ Analysis failed. Please try again or contact support."
                )
            except Exception:
                pass

    async def _handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document/file uploads."""
        if not update.message or not update.effective_user:
            return
        user = update.effective_user
        if not self._check_access(user.id):
            return

        session = self._get_session(update.effective_chat.id, user.id)
        processing_msg = await update.message.reply_text("📄 Processing document...")

        try:
            doc = update.message.document
            file = await context.bot.get_file(doc.file_id)
            doc_bytes = bytearray()
            await file.download_as_bytearray(bytearray_obj=doc_bytes)

            result = await self.backend.route_message(
                telegram_user_id=user.id,
                chat_id=update.effective_chat.id,
                message_type="document",
                text=update.message.caption,
                media_bytes=bytes(doc_bytes),
                media_filename=doc.file_name or "document",
                media_mime=doc.mime_type or "application/octet-stream",
                thread_id=session.thread_id,
            )

            await processing_msg.delete()
            for chunk in self._split_message(result.get("text", "Document processed."), 4000):
                await update.message.reply_text(chunk, parse_mode="Markdown")

        except Exception:
            logger.exception("Document handling failed")
            try:
                await processing_msg.edit_text("❌ Failed to process document.")
            except Exception:
                pass

    async def _handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle video uploads."""
        if not update.message or not update.effective_user:
            return
        user = update.effective_user
        if not self._check_access(user.id):
            return

        session = self._get_session(update.effective_chat.id, user.id)
        processing_msg = await update.message.reply_text("🎬 Processing video...")

        try:
            video = update.message.video
            file = await context.bot.get_file(video.file_id)
            video_bytes = bytearray()
            await file.download_as_bytearray(bytearray_obj=video_bytes)

            result = await self.backend.route_message(
                telegram_user_id=user.id,
                chat_id=update.effective_chat.id,
                message_type="video",
                text=update.message.caption,
                media_bytes=bytes(video_bytes),
                media_filename=f"video_{video.file_id[-8:]}.mp4",
                media_mime=video.mime_type or "video/mp4",
                thread_id=session.thread_id,
            )

            await processing_msg.delete()
            for chunk in self._split_message(result.get("text", "Video processed."), 4000):
                await update.message.reply_text(chunk, parse_mode="Markdown")

        except Exception:
            logger.exception("Video handling failed")
            try:
                await processing_msg.edit_text("❌ Failed to process video.")
            except Exception:
                pass

    async def _handle_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice messages and audio files via NVIDIA NIM Whisper."""
        if not update.message or not update.effective_user:
            return
        user = update.effective_user
        if not self._check_access(user.id):
            return

        session = self._get_session(update.effective_chat.id, user.id)
        processing_msg = await update.message.reply_text("🎤 Transcribing audio...")

        try:
            if update.message.voice:
                media = update.message.voice
                mime = "audio/ogg"
                ext = "ogg"
            else:
                media = update.message.audio
                mime = media.mime_type or "audio/mpeg"
                ext = "mp3"

            file = await context.bot.get_file(media.file_id)
            audio_bytes = bytearray()
            await file.download_as_bytearray(bytearray_obj=audio_bytes)

            # Step 1: Transcribe via the voice endpoint (NVIDIA NIM Whisper)
            transcript = await self._transcribe_audio(
                audio_bytes=bytes(audio_bytes),
                filename=f"audio_{media.file_id[-8:]}.{ext}",
                content_type=mime,
            )

            if not transcript:
                await processing_msg.edit_text("🎤 Couldn't transcribe audio. Try again?")
                return

            # Step 2: Route the transcribed text to the AI agent pipeline
            result = await self.backend.route_message(
                telegram_user_id=user.id,
                chat_id=update.effective_chat.id,
                message_type="text",
                text=f"[Voice message transcript]: {transcript}",
                thread_id=session.thread_id,
            )

            await processing_msg.delete()

            # Show the transcript and the AI response
            response_text = result.get("text", "I received your voice message.")
            full_response = f"🎤 *Transcript:* {transcript}\n\n{response_text}"

            for chunk in self._split_message(full_response, 4000):
                await update.message.reply_text(chunk, parse_mode="Markdown")

        except Exception:
            logger.exception("Audio handling failed")
            try:
                await processing_msg.edit_text("❌ Failed to process audio.")
            except Exception:
                pass

    async def _transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> str | None:
        """
        Call the backend's /api/v1/voice/transcribe endpoint.
        Returns the transcript text, or None on failure.
        """
        try:
            resp = await self.backend._client.post(
                "/api/v1/voice/transcribe",
                files={"file": (filename, io.BytesIO(audio_bytes), content_type)},
                timeout=120.0,
            )
            resp.raise_for_status()
            return resp.json().get("text", "").strip() or None
        except httpx.HTTPStatusError as e:
            logger.error("Transcription API error: %d — %s", e.response.status_code, e.response.text[:300])
            return None
        except Exception:
            logger.exception("Transcription request failed")
            return None

    async def _handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle shared locations — find nearby resources."""
        if not update.message or not update.effective_user:
            return
        user = update.effective_user
        if not self._check_access(user.id):
            return

        session = self._get_session(update.effective_chat.id, user.id)
        loc = update.message.location

        processing_msg = await update.message.reply_text("🗺️ Finding nearby resources...")

        try:
            result = await self.backend.route_message(
                telegram_user_id=user.id,
                chat_id=update.effective_chat.id,
                message_type="location",
                location={"lat": loc.latitude, "lng": loc.longitude},
                thread_id=session.thread_id,
            )

            await processing_msg.delete()
            text = result.get("text", "Location received.")
            for chunk in self._split_message(text, 4000):
                await update.message.reply_text(chunk, parse_mode="Markdown")

        except Exception:
            logger.exception("Location handling failed")
            try:
                await processing_msg.edit_text("❌ Failed to find resources.")
            except Exception:
                pass

    # ── Text Messages ───────────────────────────────────────────────────

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle plain text messages — route to conversational AI."""
        if not update.message or not update.effective_user:
            return

        user = update.effective_user
        if not self._check_access(user.id):
            return

        text = update.message.text
        if not text:
            return

        session = self._get_session(update.effective_chat.id, user.id)

        # Check for link code without /link command
        if not session.is_linked and self._looks_like_link_code(text):
            context.args = [text]
            await self._handle_link(update, context)
            return

        # Multi-step fair deal flow
        if session.current_mode == "awaiting_fairdeal":
            await self._handle_fairdeal_text(update, context, session, text)
            return

        try:
            result = await self.backend.route_message(
                telegram_user_id=user.id,
                chat_id=update.effective_chat.id,
                message_type="text",
                text=text,
                thread_id=session.thread_id,
            )

            response_text = result.get("text", "I didn't understand that.")
            parse_mode = result.get("parse_mode", "Markdown")

            for chunk in self._split_message(response_text, 4000):
                await update.message.reply_text(chunk, parse_mode=parse_mode)

        except Exception:
            logger.exception("Text handling failed")
            await update.message.reply_text("❌ Something went wrong. Please try again.")

    # ── Callback Queries ────────────────────────────────────────────────

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses."""
        query = update.callback_query
        if not query or not query.data:
            return

        await query.answer()

        parts = query.data.split(":")
        action = parts[0]

        if action == "resources":
            category = parts[1] if len(parts) > 1 else "all"
            await self._handle_resources_callback(query, category)

        elif action == "propose":
            sub_action = parts[1] if len(parts) > 1 else ""
            await self._handle_propose_callback(query, sub_action, parts[2:])

        elif action == "vote":
            vote_type = parts[1] if len(parts) > 1 else ""
            proposal_id = parts[2] if len(parts) > 2 else ""
            await self._handle_vote_callback(query, vote_type, proposal_id)

        elif action == "analyze_next":
            await query.edit_message_text("📸 Send another photo for analysis!")

    async def _handle_resources_callback(self, query, category: str):
        """Handle resource category selection."""
        try:
            resp = await self.backend._client.get(f"/api/v1/resources?category={category}")
            resp.raise_for_status()
            resources = resp.json().get("resources", [])

            if not resources:
                await query.edit_message_text(f"No {category} resources found.")
                return

            text = f"🌍 **{category.title()} Resources**\n\n"
            for r in resources[:10]:
                text += f"• **{r['name']}** — {r.get('description', 'N/A')}\n"

            await query.edit_message_text(text, parse_mode="Markdown")
        except Exception:
            await query.edit_message_text("❌ Failed to load resources.")

    async def _handle_propose_callback(self, query, action: str, args: list):
        """Handle proposal confirmation/cancellation."""
        if action == "confirm" and args:
            title = args[0]
            try:
                await self.backend._client.post(
                    "/api/v1/governance/proposals",
                    json={"title": title, "source_channel": "telegram"},
                )
                await query.edit_message_text(f"✅ Proposal **{title}** submitted!")
            except Exception:
                await query.edit_message_text("❌ Failed to submit proposal.")
        else:
            await query.edit_message_text("❌ Proposal cancelled.")

    async def _handle_vote_callback(self, query, vote_type: str, proposal_id: str):
        """Handle vote button press."""
        if not query.from_user:
            return
        try:
            await self.backend._client.post(
                f"/api/v1/governance/proposals/{proposal_id}/vote",
                json={
                    "vote": vote_type,
                    "voter_telegram_id": query.from_user.id,
                },
            )
            emoji = {"yes": "👍", "no": "👎", "abstain": "🤷"}.get(vote_type, "❓")
            await query.edit_message_text(f"{emoji} Vote recorded: **{vote_type}**")
        except Exception:
            await query.edit_message_text("❌ Vote failed. You may have already voted.")

    # ── Error Handler ───────────────────────────────────────────────────

    async def _handle_error(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Log errors."""
        logger.error("Exception while handling an update:", exc_info=context.error)

    # ── Utilities ───────────────────────────────────────────────────────

    @staticmethod
    def _split_message(text: str, max_len: int = 4000) -> list[str]:
        """Split a long message into chunks respecting Telegram limits."""
        if len(text) <= max_len:
            return [text]

        chunks = []
        while text:
            if len(text) <= max_len:
                chunks.append(text)
                break

            # Try to split at a newline
            split_idx = text.rfind("\n", 0, max_len)
            if split_idx == -1:
                split_idx = max_len

            chunks.append(text[:split_idx])
            text = text[split_idx:].lstrip("\n")

        return chunks

    @staticmethod
    def _looks_like_link_code(text: str) -> bool:
        """Check if text looks like a link code (e.g., ABCD-1234)."""
        text = text.strip().upper()
        if len(text) < 6 or len(text) > 12:
            return False
        return all(c.isalnum() or c == "-" for c in text)

    # ── Run ─────────────────────────────────────────────────────────────

    async def run_polling(self):
        """Run the bot with long-polling (for development)."""
        app = self.build_application()
        logger.info("Starting Telegram bot (polling mode)...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)

        # Keep running
        try:
            await asyncio.Event().wait()
        finally:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
            await self.backend.close()

    async def run_webhook(self, host: str = "0.0.0.0", port: int = 8443):
        """Run the bot with webhook (for production)."""
        app = self.build_application()
        logger.info(f"Starting Telegram bot (webhook mode on {host}:{port})...")
        await app.initialize()
        await app.start()
        await app.updater.start_webhook(
            listen=host,
            port=port,
            url_path="/webhook/telegram",
            webhook_url=f"{self.webhook_url}/webhook/telegram",
        )

        try:
            await asyncio.Event().wait()
        finally:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
            await self.backend.close()


# ── Factory ──────────────────────────────────────────────────────────────────


def create_telegram_bot() -> TelegramBot:
    """Create a TelegramBot from environment variables."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
    webhook_url = os.environ.get("TELEGRAM_WEBHOOK_URL")

    allowed_ids_raw = os.environ.get("TELEGRAM_ALLOWED_USERS", "")
    allowed_ids = None
    if allowed_ids_raw:
        allowed_ids = {int(uid.strip()) for uid in allowed_ids_raw.split(",") if uid.strip()}

    return TelegramBot(
        token=token,
        backend_url=backend_url,
        webhook_url=webhook_url,
        allowed_user_ids=allowed_ids,
    )


# ── Channel Adapter (for registry integration) ──────────────────────────────


class TelegramBotChannel:
    """
    Adapter that wraps TelegramBot so it satisfies the Channel protocol
    used by ChannelRegistry in channels/__init__.py.

    In polling mode the bot runs in a background task; the FastAPI server
    and the Telegram bot share the same event loop.
    """

    channel_type: str = "telegram"

    def __init__(
        self,
        token: str,
        backend_url: str = "http://localhost:8000",
        webhook_url: str | None = None,
    ):
        self._bot = TelegramBot(
            token=token,
            backend_url=backend_url,
            webhook_url=webhook_url,
        )
        self._app: Application | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Build the Application, start polling in a background task."""
        self._app = self._bot.build_application()
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot started (polling)")

    async def stop(self) -> None:
        if self._app and self._app.updater:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
        await self._bot.backend.close()
        logger.info("Telegram bot stopped")

    async def send_message(
        self,
        recipient_id: str,
        text: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Push a message to a Telegram chat by chat_id."""
        if self._app is None:
            raise RuntimeError("Telegram bot not started")
        chat_id = int(recipient_id)
        msg = await self._app.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=kwargs.get("parse_mode", "Markdown"),
        )
        return {"message_id": str(msg.message_id), "status": "sent"}


# ── CLI Entry Point ──────────────────────────────────────────────────────────


async def main():
    """Run the Telegram bot standalone."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    bot = create_telegram_bot()
    mode = os.environ.get("TELEGRAM_BOT_MODE", "polling")

    if mode == "webhook":
        host = os.environ.get("TELEGRAM_WEBHOOK_HOST", "0.0.0.0")
        port = int(os.environ.get("TELEGRAM_WEBHOOK_PORT", "8443"))
        await bot.run_webhook(host=host, port=port)
    else:
        await bot.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
