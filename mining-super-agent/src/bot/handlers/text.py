"""
Text Message Handler
====================
The main conversation brain. Routes natural-language messages to the
right agent based on intent classification, then formats a friendly
Swahili-first response.

This is NOT a command handler — miners talk naturally, like texting
a knowledgeable friend.
"""

import logging
import re
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from bot.conversation import ConversationManager
from bot.middleware.language import LanguageMiddleware
from bot.responses import get_response
from bot.keyboards import quick_actions_keyboard, mineral_id_keyboard

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------
# We use keyword matching + simple heuristics rather than an LLM call for
# speed and zero cost.  The orchestrator LLM is only invoked for complex
# queries that need deep analysis.

INTENT_PATTERNS: dict[str, list[re.Pattern]] = {
    "mineral_query": [
        re.compile(r"\b(dhahabu|gold|copper|shaba|madini|mineral|ore)\b", re.I),
        re.compile(r"\b(rock|mwamba|jiwe|stone|quartz|pyrite)\b", re.I),
        re.compile(r"\b(magnetite|hematite|graphite|manganese)\b", re.I),
    ],
    "price_check": [
        re.compile(r"\b(bei|price|bei ya|gharama|cost|value|thamani)\b", re.I),
        re.compile(r"\b(dollar|dola|ksh|kes|shilling)\b", re.I),
        re.compile(r"\b(sell|kuuza|buy|kununua|market|soko)\b", re.I),
    ],
    "legal_question": [
        re.compile(r"\b(leseni|license|permit|ruhusa|legal|sheria)\b", re.I),
        re.compile(r"\b(mining act|county|government|serikali|kortini|court)\b", re.I),
        re.compile(r"\b(eia|environmental|mazingira|compliance)\b", re.I),
        re.compile(r"\b(claim|mgodi|shaft|tunnel|excavat)\b", re.I),
    ],
    "location_query": [
        re.compile(r"\b(wapi|where|mahali|place|eneo|area|location)\b", re.I),
        re.compile(r"\b(gps|coordinates|latitude|longitude)\b", re.I),
    ],
    "greeting": [
        re.compile(r"^(habari|hello|hi|hey|hujambo|jambo|mambo|sasa|niaje|vipi)\b", re.I),
        re.compile(r"^(good\s*(morning|afternoon|evening)|asubuhi|mchana|jioni)\b", re.I),
    ],
    "thanks": [
        re.compile(r"\b(asante|thank|thanks|shukrani|nashukuru)\b", re.I),
    ],
    "who_are_you": [
        re.compile(r"\b(who\s+are\s+you|wewe\s+ni\s+nani|jina\s+lako|your\s+name|unaitwa)\b", re.I),
        re.compile(r"\b(what\s+can\s+you|unaweza\s+nini|unafanya\s+nini|what\s+do\s+you)\b", re.I),
    ],
}


def classify_intent(text: str) -> str:
    """Return the best-matching intent string for a message."""
    text_lower = text.lower().strip()

    scores: dict[str, int] = {}
    for intent, patterns in INTENT_PATTERNS.items():
        score = sum(1 for p in patterns if p.search(text_lower))
        if score:
            scores[intent] = score

    if not scores:
        return "general"

    # Prioritize greetings and thanks (they're short-circuit)
    if scores.get("greeting", 0) > 0 and len(text_lower.split()) <= 5:
        return "greeting"
    if scores.get("thanks", 0) > 0 and len(text_lower.split()) <= 5:
        return "thanks"
    if scores.get("who_are_you", 0) > 0:
        return "who_are_you"

    # Otherwise return the highest-scoring intent
    return max(scores, key=scores.get)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Agent routing stubs
# ---------------------------------------------------------------------------
# These call the DeerFlow orchestrator / specific agents.  For now they
# return placeholder responses so the bot is fully functional end-to-end
# even before the agent layer is wired up.

async def _query_geological_agent(text: str, lang: str) -> str:
    """Send a geological/mineral query to the orchestrator."""
    # TODO: wire to DeerFlow orchestrator → Geological Agent / Mineral ID Agent
    return get_response("mineral_analysis_pending", lang=lang)


async def _query_market_agent(text: str, lang: str) -> str:
    """Get current commodity prices."""
    # TODO: wire to Market Agent (yfinance / Finnhub)
    return get_response("price_info", lang=lang)


async def _query_legal_agent(text: str, lang: str) -> str:
    """Answer a legal / licensing question."""
    # TODO: wire to Legal Agent
    return get_response("legal_info", lang=lang)


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------

async def handle_text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    conv_manager: ConversationManager,
    lang_middleware: LanguageMiddleware,
    lang: str,
) -> None:
    """
    Process an incoming text message.

    1. Classify intent
    2. Route to the right agent (or respond directly for simple cases)
    3. Send a natural-language reply
    """
    user_id = update.effective_user.id
    text = update.message.text or ""

    intent = classify_intent(text)
    logger.info("User %s intent=%s lang=%s", user_id, intent, lang)

    # ----- Simple intents (no agent needed) -----
    if intent == "greeting":
        reply = get_response("greeting_reply", lang=lang, name=update.effective_user.first_name or "Rafiki")
        await update.message.reply_text(reply, reply_markup=quick_actions_keyboard(lang))
        conv_manager.add_message(user_id, "assistant", reply, lang=lang, intent=intent)
        return

    if intent == "thanks":
        reply = get_response("thanks_reply", lang=lang)
        await update.message.reply_text(reply)
        conv_manager.add_message(user_id, "assistant", reply, lang=lang, intent=intent)
        return

    if intent == "who_are_you":
        reply = get_response("about_me", lang=lang)
        await update.message.reply_text(reply, reply_markup=quick_actions_keyboard(lang))
        conv_manager.add_message(user_id, "assistant", reply, lang=lang, intent=intent)
        return

    # ----- Agent-backed intents -----
    # Show a "thinking" indicator while we wait for the agent
    thinking_msg = await update.message.reply_text(get_response("thinking", lang=lang))

    try:
        if intent == "mineral_query":
            reply = await _query_geological_agent(text, lang)
        elif intent == "price_check":
            reply = await _query_market_agent(text, lang)
        elif intent == "legal_question":
            reply = await _query_legal_agent(text, lang)
        else:
            # General query — pass to orchestrator for routing
            reply = await _query_geological_agent(text, lang)
    except Exception as exc:
        logger.exception("Agent call failed for user %s: %s", user_id, exc)
        reply = get_response("error_agent", lang=lang)

    # Replace the "thinking…" message with the real response
    try:
        await thinking_msg.edit_text(reply)
    except Exception:
        # If editing fails (message too old, etc.), send a new message
        await update.message.reply_text(reply)

    conv_manager.add_message(user_id, "assistant", reply, lang=lang, intent=intent)
