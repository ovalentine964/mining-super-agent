"""
Voice Handler
=============
When a miner sends a voice message:
1. Download the OGG/OPUS file from Telegram
2. Transcribe with Whisper
3. Process the transcribed text as a normal query
4. Respond in the same language the miner spoke
"""

import logging
import os
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.conversation import ConversationManager
from bot.middleware.language import LanguageMiddleware
from bot.responses import get_response
from bot.handlers.text import handle_text_message, classify_intent

logger = logging.getLogger(__name__)

VOICE_DIR = Path(tempfile.gettempdir()) / "mining-agent-voice"
VOICE_DIR.mkdir(parents=True, exist_ok=True)

# Whisper model — loaded lazily on first use
_whisper_model = None


def _get_whisper_model():
    """Lazy-load the Whisper model (saves memory until first voice message)."""
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper

            model_size = os.environ.get("WHISPER_MODEL", "base")
            logger.info("Loading Whisper model '%s'…", model_size)
            _whisper_model = whisper.load_model(model_size)
            logger.info("Whisper model loaded.")
        except ImportError:
            logger.error("openai-whisper not installed. Voice transcription unavailable.")
            return None
        except Exception as exc:
            logger.error("Failed to load Whisper model: %s", exc)
            return None
    return _whisper_model


async def handle_voice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    conv_manager: ConversationManager,
    lang_middleware: LanguageMiddleware,
    lang: str,
) -> None:
    """Process a voice message."""
    user_id = update.effective_user.id

    thinking_msg = await update.message.reply_text(
        get_response("voice_transcribing", lang=lang)
    )

    try:
        # 1. Download the voice file
        voice = update.message.voice or update.message.audio
        if not voice:
            await thinking_msg.edit_text(get_response("error_voice", lang=lang))
            return

        file = await context.bot.get_file(voice.file_id)
        voice_path = VOICE_DIR / f"{user_id}_{voice.file_unique_id}.ogg"
        await file.download_to_drive(str(voice_path))
        logger.info("Voice file saved: %s", voice_path)

        # 2. Transcribe
        transcript = await _transcribe(voice_path, lang)

        if not transcript:
            await thinking_msg.edit_text(
                get_response("voice_transcription_failed", lang=lang)
            )
            return

        # 3. Show the transcription to the user
        transcription_text = get_response(
            "voice_transcribed", lang=lang, transcript=transcript
        )
        await thinking_msg.edit_text(transcription_text)

        # 4. Detect language from the transcript
        detected_lang = lang_middleware.detect_language(transcript)
        resolved_lang = lang_middleware.resolve_language(user_id, detected_lang)

        # 5. Classify intent and route
        intent = classify_intent(transcript)
        logger.info(
            "Voice from user %s: transcript='%s' intent=%s lang=%s",
            user_id, transcript[:80], intent, resolved_lang,
        )

        # 6. Process as a normal text message
        # We create a synthetic text message by modifying the update
        original_text = update.message.text
        update.message.text = transcript

        await handle_text_message(
            update, context, conv_manager, lang_middleware, resolved_lang
        )

        # Restore original text (hygiene)
        update.message.text = original_text

        # Store in conversation history
        conv_manager.add_message(
            user_id,
            "user",
            f"[Voice] {transcript}",
            lang=resolved_lang,
            intent=intent,
        )

    except Exception as exc:
        logger.exception("Voice processing failed for user %s: %s", user_id, exc)
        await thinking_msg.edit_text(
            get_response("error_voice", lang=lang)
        )


async def _transcribe(voice_path: Path, lang: str) -> str | None:
    """
    Transcribe a voice file using Whisper.

    Attempts to auto-detect language; falls back to Swahili hint.
    """
    model = _get_whisper_model()
    if model is None:
        return None

    try:
        # Hint Whisper with the user's preferred language
        lang_hint = {"sw": "sw", "en": "en", "luo": "luo"}.get(lang, "sw")

        result = model.transcribe(
            str(voice_path),
            language=lang_hint if lang_hint != "luo" else None,  # Whisper may not know Luo
            fp16=False,  # CPU-safe
        )

        transcript = result.get("text", "").strip()
        if not transcript:
            return None

        # Log detected language for debugging
        detected = result.get("language", "unknown")
        logger.info("Whisper detected language: %s", detected)

        return transcript

    except Exception as exc:
        logger.error("Whisper transcription failed: %s", exc)
        return None
