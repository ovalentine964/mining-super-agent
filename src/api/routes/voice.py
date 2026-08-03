"""
Voice Processing Endpoint — NVIDIA NIM Whisper Transcription

Accepts audio uploads (voice messages, audio files) and returns transcripts
using NVIDIA's hosted Whisper NIM model.

Endpoints:
    POST /api/v1/voice/transcribe   — Upload audio → get transcript
    GET  /api/v1/voice/models        — List available transcription models

Environment:
    NVIDIA_API_KEY          — Required. Your NVIDIA NIM API key.
    NVIDIA_NIM_BASE_URL     — Optional. Defaults to https://integrate.api.nvidia.com/v1
    WHISPER_MODEL           — Optional. Defaults to nvidia/parakeet-ctc-0.6b-en
                              (or nvidia/canary-1b for multilingual)

The endpoint follows the OpenAI-compatible /audio/transcriptions spec so it
can be swapped to any Whisper-compatible API without code changes.
"""

from __future__ import annotations

import io
import logging
import os
import time
from typing import Any

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

# ── Config ───────────────────────────────────────────────────────────────────

_DEFAULT_NIM_BASE = "https://integrate.api.nvidia.com/v1"
_DEFAULT_MODEL = "nvidia/parakeet-ctc-0.6b-en"
_MULTILINGUAL_MODEL = "nvidia/canary-1b"

# Acceptable audio MIME types from Telegram and general clients
_ALLOWED_MIMES = {
    "audio/ogg",
    "audio/oga",
    "audio/opus",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/webm",
    "audio/flac",
}

# Max upload: 25 MB (NIM limit)
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


# ── Models ───────────────────────────────────────────────────────────────────


class TranscriptionResponse(BaseModel):
    text: str
    language: str | None = None
    duration_seconds: float | None = None
    model: str
    processing_ms: int


class VoiceError(BaseModel):
    detail: str
    code: str


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_nim_config() -> tuple[str, str]:
    """Return (api_key, base_url) from environment."""
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    base_url = os.environ.get("NVIDIA_NIM_BASE_URL", _DEFAULT_NIM_BASE)
    return api_key, base_url


def _pick_model(language: str | None) -> str:
    """Select model based on language hint."""
    env_model = os.environ.get("WHISPER_MODEL")
    if env_model:
        return env_model
    if language and language.lower() not in ("en", "english"):
        return _MULTILINGUAL_MODEL
    return _DEFAULT_MODEL


def _guess_extension(content_type: str) -> str:
    """Map MIME type to file extension for the NIM API."""
    mapping = {
        "audio/ogg": "ogg",
        "audio/oga": "ogg",
        "audio/opus": "ogg",
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/mp4": "m4a",
        "audio/m4a": "m4a",
        "audio/wav": "wav",
        "audio/wave": "wav",
        "audio/x-wav": "wav",
        "audio/webm": "webm",
        "audio/flac": "flac",
    }
    return mapping.get(content_type, "ogg")


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    responses={
        400: {"model": VoiceError},
        401: {"model": VoiceError},
        413: {"model": VoiceError},
        502: {"model": VoiceError},
    },
    summary="Transcribe audio to text using NVIDIA NIM Whisper",
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file (ogg, mp3, wav, m4a, flac, webm)"),
    language: str | None = Form(None, description="ISO 639-1 language code (e.g. 'en', 'sw')"),
    model: str | None = Form(None, description="Override the NIM model name"),
) -> TranscriptionResponse:
    """
    Upload an audio file and receive a text transcription.

    Designed to be called from the Telegram bot's voice pipeline or any
    client that has raw audio bytes.

    Accepts the same formats Telegram sends:
      - Voice messages: OGG/Opus
      - Audio files: MP3, M4A, WAV, etc.
    """
    api_key, base_url = _get_nim_config()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail={
                "detail": "NVIDIA_API_KEY not configured",
                "code": "MISSING_API_KEY",
            },
        )

    # Validate MIME type
    content_type = file.content_type or ""
    if content_type and content_type not in _ALLOWED_MIMES:
        # Be lenient — some clients send application/octet-stream
        if "audio" not in content_type and "octet-stream" not in content_type:
            raise HTTPException(
                status_code=400,
                detail={
                    "detail": f"Unsupported audio type: {content_type}",
                    "code": "INVALID_MIME",
                },
            )

    # Read and validate size
    audio_data = await file.read()
    if len(audio_data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "detail": f"Audio too large: {len(audio_data)} bytes (max {_MAX_UPLOAD_BYTES})",
                "code": "FILE_TOO_LARGE",
            },
        )

    if len(audio_data) == 0:
        raise HTTPException(
            status_code=400,
            detail={"detail": "Empty audio file", "code": "EMPTY_FILE"},
        )

    chosen_model = model or _pick_model(language)
    ext = _guess_extension(content_type)
    filename = file.filename or f"audio.{ext}"

    logger.info(
        "Transcribing %s (%d bytes, model=%s, lang=%s)",
        filename, len(audio_data), chosen_model, language,
    )

    t0 = time.monotonic()

    # ── Call NVIDIA NIM Whisper ──────────────────────────────────────────
    # The NIM audio transcription endpoint follows the OpenAI spec:
    #   POST {base_url}/audio/transcriptions
    #   multipart/form-data: file, model, language, response_format

    form_data = {
        "model": (None, chosen_model),
        "response_format": (None, "json"),
    }
    if language:
        form_data["language"] = (None, language)

    files_payload = {
        "file": (filename, io.BytesIO(audio_data), content_type or "audio/ogg"),
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
            resp = await client.post(
                f"{base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={**files_payload, **form_data},
            )
    except httpx.ConnectError as e:
        logger.error("NIM connection failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail={"detail": "Failed to connect to NVIDIA NIM", "code": "NIM_UNREACHABLE"},
        )
    except httpx.TimeoutException:
        logger.error("NIM transcription timed out")
        raise HTTPException(
            status_code=502,
            detail={"detail": "NIM transcription timed out", "code": "NIM_TIMEOUT"},
        )

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    if resp.status_code == 401:
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid NVIDIA API key", "code": "NIM_AUTH_FAILED"},
        )

    if resp.status_code != 200:
        logger.error("NIM returned %d: %s", resp.status_code, resp.text[:500])
        raise HTTPException(
            status_code=502,
            detail={
                "detail": f"NIM transcription failed (HTTP {resp.status_code})",
                "code": "NIM_ERROR",
            },
        )

    result = resp.json()
    text = result.get("text", "").strip()

    logger.info("Transcription complete: %d chars in %dms", len(text), elapsed_ms)

    return TranscriptionResponse(
        text=text,
        language=result.get("language", language),
        duration_seconds=result.get("duration"),
        model=chosen_model,
        processing_ms=elapsed_ms,
    )


@router.get(
    "/models",
    summary="List available transcription models",
)
async def list_models() -> dict[str, Any]:
    """Return available NIM Whisper models and which one is currently active."""
    default = os.environ.get("WHISPER_MODEL")
    return {
        "models": [
            {
                "id": "nvidia/parakeet-ctc-0.6b-en",
                "name": "Parakeet CTC 0.6B (English)",
                "languages": ["en"],
            },
            {
                "id": "nvidia/canary-1b",
                "name": "Canary 1B (Multilingual)",
                "languages": ["en", "es", "fr", "de", "sw", "hi", "zh", "ja", "ko"],
            },
        ],
        "default": default or _DEFAULT_MODEL,
        "nim_base_url": os.environ.get("NVIDIA_NIM_BASE_URL", _DEFAULT_NIM_BASE),
    }
