"""
Mining Super-Agent Telegram Bot
================================
Natural conversation bot for Kenyan miners.
Speaks Swahili first, English, and Luo.
Feels like talking to a knowledgeable friend — NOT a command-line tool.
"""

import asyncio
import logging
import os
from pathlib import Path

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from bot.conversation import ConversationManager
from bot.handlers.text import handle_text_message
from bot.handlers.photo import handle_photo
from bot.handlers.voice import handle_voice
from bot.handlers.location import handle_location
from bot.handlers.document import handle_document
from bot.keyboards import (
    language_selection_keyboard,
    quick_actions_keyboard,
    help_keyboard,
)
from bot.responses import get_response
from bot.middleware.auth import AuthMiddleware, rate_limit_check
from bot.middleware.language import LanguageMiddleware

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))

# ---------------------------------------------------------------------------
# Global managers (created once, shared across handlers)
# ---------------------------------------------------------------------------
conversation_manager = ConversationManager()
auth_middleware = AuthMiddleware(admin_user_id=ADMIN_USER_ID)
language_middleware = LanguageMiddleware()


# ===================================================================
# Command handlers — minimal, only for onboarding / admin
# ===================================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message — warm, friendly, in Swahili by default."""
    user = update.effective_user
    auth_middleware.register_user(user)

    welcome = get_response(
        "welcome",
        lang="sw",
        name=user.first_name or "Rafiki",
    )
    await update.message.reply_text(
        welcome,
        reply_markup=language_selection_keyboard(),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show what the bot can do — in the user's language."""
    user_id = update.effective_user.id
    lang = language_middleware.get_language(user_id)
    text = get_response("help", lang=lang)
    await update.message.reply_text(text, reply_markup=help_keyboard(lang))


async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Let user pick their preferred language."""
    user_id = update.effective_user.id
    lang = language_middleware.get_language(user_id)
    text = get_response("choose_language", lang=lang)
    await update.message.reply_text(text, reply_markup=language_selection_keyboard())


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a summary report of recent analysis."""
    user_id = update.effective_user.id
    lang = language_middleware.get_language(user_id)
    history = conversation_manager.get_history(user_id)

    if not history:
        await update.message.reply_text(get_response("no_history", lang=lang))
        return

    # Build a summary from conversation history
    summary_parts = []
    for entry in history[-10:]:
        if entry.get("analysis"):
            summary_parts.append(entry["analysis"])

    if not summary_parts:
        await update.message.reply_text(get_response("no_analysis", lang=lang))
        return

    report_text = get_response("report_header", lang=lang) + "\n\n"
    report_text += "\n---\n".join(summary_parts)
    await update.message.reply_text(report_text)


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin-only stats (Valentine)."""
    user_id = update.effective_user.id
    if not auth_middleware.is_admin(user_id):
        await update.message.reply_text("⛔ Huna ruhusa ya admin.")
        return

    stats = auth_middleware.get_stats()
    lang = language_middleware.get_language(user_id)
    text = get_response("admin_stats", lang=lang, **stats)
    await update.message.reply_text(text)


# ===================================================================
# Callback query handler (inline keyboard buttons)
# ===================================================================

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # Language selection
    if data.startswith("lang_"):
        chosen = data.removeprefix("lang_")
        language_middleware.set_language(user_id, chosen)
        confirmation = get_response("language_set", lang=chosen)
        await query.edit_message_text(confirmation)
        return

    # Quick actions
    if data == "action_price":
        lang = language_middleware.get_language(user_id)
        await query.edit_message_text(get_response("price_loading", lang=lang))
        # Route to market agent via text handler
        fake_update = _make_text_update(query, "Bei za madini sasa hivi")
        await handle_text_message(
            fake_update, context, conversation_manager, language_middleware, lang
        )
        return

    if data == "action_report":
        lang = language_middleware.get_language(user_id)
        await query.edit_message_text(get_response("report_loading", lang=lang))
        return

    if data == "action_help":
        lang = language_middleware.get_language(user_id)
        text = get_response("help", lang=lang)
        await query.edit_message_text(text, reply_markup=help_keyboard(lang))
        return

    if data == "quick_swahili":
        language_middleware.set_language(user_id, "sw")
        await query.edit_message_text(get_response("language_set", lang="sw"))
        return

    if data == "quick_english":
        language_middleware.set_language(user_id, "en")
        await query.edit_message_text(get_response("language_set", lang="en"))
        return

    if data == "quick_luo":
        language_middleware.set_language(user_id, "luo")
        await query.edit_message_text(get_response("language_set", lang="luo"))
        return

    # Mineral identification confirmation
    if data.startswith("mineral_confirm_"):
        mineral = data.removeprefix("mineral_confirm_")
        lang = language_middleware.get_language(user_id)
        confirmation = get_response("mineral_confirmed", lang=lang, mineral=mineral)
        await query.edit_message_text(confirmation)
        return

    if data == "mineral_retry":
        lang = language_middleware.get_language(user_id)
        await query.edit_message_text(get_response("mineral_retry_prompt", lang=lang))
        return


# ===================================================================
# Text message handler — the main conversation entry point
# ===================================================================

async def on_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route all text messages through the conversation pipeline."""
    user_id = update.effective_user.id

    # Rate limiting
    if not rate_limit_check(user_id):
        lang = language_middleware.get_language(user_id)
        await update.message.reply_text(get_response("rate_limited", lang=lang))
        return

    # Detect or use preferred language
    text = update.message.text or ""
    detected_lang = language_middleware.detect_language(text)
    lang = language_middleware.resolve_language(user_id, detected_lang)

    # Register user if new
    auth_middleware.register_user(update.effective_user)

    # Store message in conversation history
    conversation_manager.add_message(user_id, "user", text, lang=lang)

    # Handle the message through the text handler
    await handle_text_message(
        update, context, conversation_manager, language_middleware, lang
    )


# ===================================================================
# Media handlers
# ===================================================================

async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route photos to mineral identification."""
    user_id = update.effective_user.id
    if not rate_limit_check(user_id):
        lang = language_middleware.get_language(user_id)
        await update.message.reply_text(get_response("rate_limited", lang=lang))
        return

    lang = language_middleware.get_language(user_id)
    auth_middleware.register_user(update.effective_user)
    await handle_photo(update, context, conversation_manager, language_middleware, lang)


async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route voice messages for transcription + analysis."""
    user_id = update.effective_user.id
    if not rate_limit_check(user_id):
        lang = language_middleware.get_language(user_id)
        await update.message.reply_text(get_response("rate_limited", lang=lang))
        return

    lang = language_middleware.get_language(user_id)
    auth_middleware.register_user(update.effective_user)
    await handle_voice(update, context, conversation_manager, language_middleware, lang)


async def on_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route GPS locations for geological analysis."""
    user_id = update.effective_user.id
    if not rate_limit_check(user_id):
        lang = language_middleware.get_language(user_id)
        await update.message.reply_text(get_response("rate_limited", lang=lang))
        return

    lang = language_middleware.get_language(user_id)
    auth_middleware.register_user(update.effective_user)
    await handle_location(update, context, conversation_manager, language_middleware, lang)


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route documents (PDFs) for processing."""
    user_id = update.effective_user.id
    if not rate_limit_check(user_id):
        lang = language_middleware.get_language(user_id)
        await update.message.reply_text(get_response("rate_limited", lang=lang))
        return

    lang = language_middleware.get_language(user_id)
    auth_middleware.register_user(update.effective_user)
    await handle_document(update, context, conversation_manager, language_middleware, lang)


# ===================================================================
# Error handler
# ===================================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and send friendly message to user."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        user_id = update.effective_user.id if update.effective_user else 0
        lang = language_middleware.get_language(user_id) if user_id else "sw"
        await update.effective_message.reply_text(
            get_response("error_generic", lang=lang)
        )


# ===================================================================
# Helpers
# ===================================================================

def _make_text_update(query, text: str) -> Update:
    """Create a synthetic Update object from a callback query for routing."""
    # This is a minimal shim so callback buttons can reuse text handlers
    query.message.text = text
    query.message.from_user = query.from_user
    return Update(update_id=query.id, message=query.message)


# ===================================================================
# Application factory
# ===================================================================

def create_application() -> Application:
    """Build and configure the telegram bot application."""
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is required")

    app = Application.builder().token(BOT_TOKEN).build()

    # -- Commands (only for onboarding & admin, not the main UX) --
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("admin", cmd_admin))

    # -- Inline keyboard callbacks --
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # -- Media handlers --
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))
    app.add_handler(MessageHandler(filters.LOCATION, on_location))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))

    # -- Text messages (the main conversation path) --
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_message)
    )

    # -- Error handler --
    app.add_error_handler(error_handler)

    return app


def main() -> None:
    """Entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("⛏️  Mining Super-Agent Telegram Bot starting…")

    app = create_application()
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
