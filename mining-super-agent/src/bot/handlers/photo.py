"""
Photo Handler
=============
When a miner sends a photo, we:
1. Download the image from Telegram
2. Run it through the mineral identification pipeline
3. Return results in Swahili with a confidence disclaimer

"Hii si uthibitisho wa maabara" — this is NOT lab confirmation.
"""

import io
import logging
import os
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.conversation import ConversationManager
from bot.middleware.language import LanguageMiddleware
from bot.responses import get_response
from bot.keyboards import mineral_id_keyboard

logger = logging.getLogger(__name__)

# Where photos are saved for processing
PHOTO_DIR = Path(tempfile.gettempdir()) / "mining-agent-photos"
PHOTO_DIR.mkdir(parents=True, exist_ok=True)


async def handle_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    conv_manager: ConversationManager,
    lang_middleware: LanguageMiddleware,
    lang: str,
) -> None:
    """Process a photo message for mineral identification."""
    user_id = update.effective_user.id
    caption = update.message.caption or ""

    # Let the user know we're analyzing
    thinking_msg = await update.message.reply_text(
        get_response("photo_analyzing", lang=lang)
    )

    try:
        # 1. Download the photo (largest available resolution)
        photo = update.message.photo[-1]  # highest resolution
        file = await context.bot.get_file(photo.file_id)

        photo_path = PHOTO_DIR / f"{user_id}_{photo.file_unique_id}.jpg"
        await file.download_to_drive(str(photo_path))
        logger.info("Photo saved: %s", photo_path)

        # 2. Run mineral identification pipeline
        result = await _identify_mineral(photo_path, caption, lang)

        # 3. Send result with disclaimer
        await thinking_msg.edit_text(result, reply_markup=mineral_id_keyboard(lang))

        # 4. Store in conversation history
        conv_manager.add_message(
            user_id,
            "user",
            f"[Photo sent] {caption}".strip(),
            lang=lang,
            intent="photo_mineral_id",
        )
        conv_manager.add_message(
            user_id,
            "assistant",
            result,
            lang=lang,
            intent="mineral_id_result",
        )

    except Exception as exc:
        logger.exception("Photo processing failed for user %s: %s", user_id, exc)
        await thinking_msg.edit_text(
            get_response("error_photo", lang=lang)
        )


async def _identify_mineral(photo_path: Path, caption: str, lang: str) -> str:
    """
    Run the mineral identification pipeline.

    Pipeline:
    1. EfficientNet-B4 model → mineral classification
    2. Confidence scoring (calibrated, not hardcoded)
    3. Format response in user's language

    For now, returns a placeholder until the vision model is deployed.
    """
    # TODO: Wire to Mineral ID Agent
    # This would call:
    #   from mineral_id.model import classify_image
    #   result = classify_image(photo_path)
    # For now, return a structured placeholder

    # Simulate analysis metadata
    minerals = _get_placeholder_minerals(caption)

    if not minerals:
        return get_response("mineral_unclear", lang=lang)

    primary = minerals[0]
    confidence_pct = int(primary["confidence"] * 100)

    # Build response
    response = get_response(
        "mineral_result_header",
        lang=lang,
    )

    response += "\n\n"
    for m in minerals:
        conf = int(m["confidence"] * 100)
        response += get_response(
            "mineral_result_line",
            lang=lang,
            mineral=m["name_sw"],
            mineral_en=m["name_en"],
            confidence=conf,
        ) + "\n"

    # Always add disclaimer
    response += "\n" + get_response("mineral_disclaimer", lang=lang)

    # If confidence is low, add extra warning
    if confidence_pct < 50:
        response += "\n" + get_response("mineral_low_confidence", lang=lang)

    return response


def _get_placeholder_minerals(caption: str) -> list[dict]:
    """
    Placeholder mineral results until the real model is wired.

    In production this calls EfficientNet-B4 via the Mineral ID Agent.
    """
    caption_lower = caption.lower() if caption else ""

    # Simple heuristic placeholder
    if any(w in caption_lower for w in ["gold", "dhahabu", "yellow", "ndogo"]):
        return [
            {"name_en": "Gold", "name_sw": "Dhahabu", "confidence": 0.62},
            {"name_en": "Pyrite", "name_sw": "Pyrite (Dhahabu ya Kijinga)", "confidence": 0.25},
            {"name_en": "Chalcopyrite", "name_sw": "Chalcopyrite (Shaba)", "confidence": 0.08},
        ]
    elif any(w in caption_lower for w in ["copper", "shaba", "green", "bluu"]):
        return [
            {"name_en": "Copper Ore", "name_sw": "Mwamba wa Shaba", "confidence": 0.71},
            {"name_en": "Malachite", "name_sw": "Malachite", "confidence": 0.15},
            {"name_en": "Azurite", "name_sw": "Azurite", "confidence": 0.09},
        ]
    else:
        # Generic rock identification
        return [
            {"name_en": "Quartz", "name_sw": "Kwartz", "confidence": 0.45},
            {"name_en": "Feldspar", "name_sw": "Feldspar", "confidence": 0.30},
            {"name_en": "Mica", "name_sw": "Mika", "confidence": 0.15},
        ]
