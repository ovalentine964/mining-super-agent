# Council Report 16: Voice + NVIDIA Integration Alignment Audit

**Council:** VALIDATION COUNCIL 2 — Voice + NVIDIA Integration  
**Date:** 2026-08-03  
**Status:** 🔴 CRITICAL GAPS — Voice pipeline is structurally incomplete; NVIDIA NIM underutilized  
**Verdict:** 3 of 7 components exist in skeleton form; 4 are entirely missing

---

## Executive Summary

The Sovereign Resource DAO has **partial voice infrastructure** in the Telegram bot (message handler exists, routes audio to backend), but the backend has **no actual transcription, analysis, or TTS pipeline**. The Flutter app has **zero voice capability**. NVIDIA NIM is used only for text LLM inference — no voice models are integrated. The system cannot currently process a voice message end-to-end.

| Component | Status | Location |
|---|---|---|
| Telegram voice message handler | ✅ Exists (skeleton) | `src/channels/telegram_bot.py:_handle_audio` |
| Audio routing to backend | ✅ Exists | `BackendClient.route_message(message_type="audio")` |
| Whisper transcription | ❌ MISSING | Listed in `requirements-bot.txt` but never imported/used |
| NVIDIA NIM voice models | ❌ MISSING | NIM used for text LLM only (`superagent.py:_call_llm`) |
| TTS (text-to-speech) | ❌ MISSING | No TTS library, no synthesis code anywhere |
| Flutter voice input | ❌ MISSING | No mic/audio packages in `pubspec.yaml` |
| Flutter voice output | ❌ MISSING | No audio playback for agent responses |
| Offline voice fallback | ❌ MISSING | No on-device Whisper or speech recognition |

---

## 1. Telegram Bot Voice Handling — AUDIT

### What Exists

`telegram_bot.py` lines ~370-410 — `_handle_audio()`:

```python
app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, self._handle_audio))
```

The handler:
- ✅ Distinguishes `voice` (OGG) from `audio` (MP3/other)
- ✅ Downloads audio bytes via Telegram Bot API
- ✅ Routes to backend via `route_message(message_type="audio", media_bytes=...)`
- ✅ Shows "🎤 Transcribing audio..." status message
- ❌ **Does NOT actually transcribe** — just forwards raw bytes to backend
- ❌ **No language detection** — doesn't identify Swahili vs English
- ❌ **No TTS response** — returns text only, never sends voice reply

### Critical Gap

The backend receives `message_type="audio"` but the `superagent.py` `chat()` method only accepts `user_message: str`. There is **no audio processing pipeline** — the audio bytes are uploaded to object storage via `_upload_media()` and then the backend returns a generic response. The transcription never happens.

---

## 2. NVIDIA NIM Integration — AUDIT

### What Exists

`superagent.py` lines ~200-240 — `_call_llm()`:

```python
base_url = os.environ.get("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
model = "nvidia/nemotron-3-ultra"  # primary
fallback = "meta/llama-3.1-405b-instruct"
```

This uses the **OpenAI-compatible chat completions API** for text-only LLM inference with function calling. It works for geological analysis, market queries, etc.

### What's Missing for Voice

- ❌ **No NVIDIA RIVA integration** — RIVA provides both ASR (speech-to-text) and TTS (text-to-speech) via NIM
- ❌ **No Parakeet model** — `nvidia/parakeet-ctc-0.6b-asr` is a NIM-hosted ASR model with strong multilingual support including Swahili
- ❌ **No voice-specific model routing** — the model registry (`src/ml/model_registry.py`) only tracks ML models, not voice models
- ❌ **`langchain-nvidia-ai-endpoints`** is in `pyproject.toml` but only used for text LLM, not voice

### NVIDIA NIM Voice Capabilities Available

| Model | Type | Capability |
|---|---|---|
| `nvidia/parakeet-ctc-0.6b-asr` | ASR | Speech-to-text, multilingual |
| `nvidia/riva-tts` | TTS | Text-to-speech, multiple languages |
| `nvidia/canary-1b` | ASR | Multi-language transcription |

---

## 3. Flutter App Voice Capability — AUDIT

### What Exists

- `pubspec.yaml` — **No voice/audio packages**. Has `camera`, `image_picker`, `geolocator` but nothing for:
  - `speech_to_text` (on-device STT)
  - `record` or `flutter_sound` (audio recording)
  - `flutter_tts` (on-device TTS)
  - `just_audio` or `audioplayers` (audio playback)
- `agent_chat_screen.dart` — **Text-only chat**. Has a `TextField` for input and `Text` widgets for output. No microphone button, no voice input, no audio playback.
- `channel_manager.dart` — Has `MessageType.audio` enum defined but **no actual audio handling** — the enum exists in the data model but no code sends or receives audio.

### Critical Gap

The target users are **Kenyan miners in Migori County** — many are semi-literate and would benefit enormously from voice interaction in Swahili. The app currently requires typing, which is a significant barrier.

---

## 4. Whisper Integration — AUDIT

### What Exists

`requirements-bot.txt` lists:
```
openai-whisper>=20231117
```

### What's Actually Happening

Whisper is **never imported or used** anywhere in the codebase. No file contains `import whisper`. The dependency is declared but the integration is completely absent.

### What's Needed

A `TranscriptionService` that:
1. Receives audio bytes (OGG from Telegram, various formats)
2. Converts to WAV (Whisper's preferred format)
3. Runs Whisper inference with language detection
4. Returns transcribed text + detected language + confidence

---

## 5. Complete Voice Pipeline — DESIGN

### Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    VOICE PIPELINE (PROPOSED)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ Telegram  │───▶│ Audio Download│───▶│ Transcription Service │  │
│  │ Voice Msg │    │ (OGG/MP3)    │    │ (Whisper or NIM ASR) │  │
│  └──────────┘    └──────────────┘    └──────────┬───────────┘  │
│                                                  │               │
│  ┌──────────┐    ┌──────────────┐    ┌──────────▼───────────┐  │
│  │ Flutter   │───▶│ Audio Upload │───▶│  Superagent (NIM LLM)│  │
│  │ Voice Rec │    │ (Multipart)  │    │  + Function Calling  │  │
│  └──────────┘    └──────────────┘    └──────────┬───────────┘  │
│                                                  │               │
│                                      ┌──────────▼───────────┐  │
│                                      │   TTS Service         │  │
│                                      │ (edge-tts or NIM TTS) │  │
│                                      └──────────┬───────────┘  │
│                                                  │               │
│                    ┌──────────────────────────────┤               │
│                    ▼                              ▼               │
│            ┌──────────────┐            ┌──────────────┐         │
│            │ Telegram Voice│            │ Flutter Audio │         │
│            │ Response (OGG)│            │ Playback      │         │
│            └──────────────┘            └──────────────┘         │
│                                                                  │
│  OFFLINE FALLBACK:                                               │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ Flutter   │───▶│ on-device STT│───▶│ Cached Response +    │  │
│  │ (no net)  │    │ (platform)   │    │ on-device TTS        │  │
│  └──────────┘    └──────────────┘    └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Pipeline Steps

1. **Voice Input**: User sends voice message via Telegram or records in Flutter
2. **Audio Download**: Backend downloads/receives audio bytes
3. **Transcription**: Whisper or NVIDIA Parakeet converts speech → text + language detection
4. **AI Analysis**: Transcribed text goes to `superagent.chat()` with NIM LLM + function calling
5. **TTS Synthesis**: Response text converted to audio via edge-tts or NIM RIVA TTS
6. **Voice Response**: Audio sent back via Telegram voice message or Flutter audio playback
7. **Offline Fallback**: On-device platform STT + cached responses + on-device TTS

---

## 6. All Gaps Identified

### GAP 1: No Transcription Service (CRITICAL)

**Impact**: Voice messages are received but never understood. The bot says "Transcribing audio..." but nothing is transcribed.

**Fix**: Create `src/services/transcription.py` with Whisper integration.

```python
# Required: import whisper, pydub for audio conversion
# Key method: transcribe(audio_bytes, mime_type) → {text, language, confidence}
```

### GAP 2: No Audio→Text Routing in Backend (CRITICAL)

**Impact**: Even if transcription existed, `superagent.chat()` only accepts string input. There's no path from audio bytes to the LLM.

**Fix**: Create `src/channels/audio_handler.py` that:
1. Receives audio from channel router
2. Calls transcription service
3. Passes transcribed text to superagent
4. Optionally synthesizes TTS response

### GAP 3: No TTS Service (HIGH)

**Impact**: All responses are text-only. Voice users get text back, which defeats the purpose.

**Fix**: Create `src/services/tts_service.py`:
- **Primary**: `edge-tts` (free, supports Swahili `sw-KE-Standard-A`)
- **Upgrade path**: NVIDIA RIVA TTS via NIM for higher quality
- Output format: OGG for Telegram, WAV/MP3 for Flutter

### GAP 4: No Flutter Voice Packages (HIGH)

**Impact**: Mobile app cannot record or play voice.

**Fix**: Add to `pubspec.yaml`:
```yaml
dependencies:
  speech_to_text: ^6.6.0    # On-device STT (offline capable)
  record: ^5.0.0            # Audio recording
  flutter_tts: ^3.8.0       # On-device TTS playback
  just_audio: ^0.9.36       # Audio playback for responses
```

### GAP 5: No Flutter Voice UI (HIGH)

**Impact**: Agent chat screen is text-only.

**Fix**: Modify `agent_chat_screen.dart` to add:
- Hold-to-record microphone button
- Audio waveform visualization during recording
- Voice message bubbles with playback controls
- Auto-play TTS responses option

### GAP 6: No NVIDIA NIM Voice Model Integration (MEDIUM)

**Impact**: Using only text LLM via NIM. Missing Parakeet ASR and RIVA TTS which may outperform Whisper for domain-specific vocabulary.

**Fix**: Add NIM voice model support as an alternative to local Whisper:
```python
# NVIDIA NIM ASR endpoint
POST https://integrate.api.nvidia.com/v1/audio/transcriptions
# Model: nvidia/parakeet-ctc-0.6b-asr
```

### GAP 7: No Offline Voice Fallback (MEDIUM)

**Impact**: Rural Kenyan users with poor connectivity cannot use voice features.

**Fix**: 
- Flutter: Use `speech_to_text` package (uses iOS/Android native STT, works offline)
- Flutter: Use `flutter_tts` (uses platform TTS engine, works offline)
- Cache common responses for offline playback

### GAP 8: No Language Detection in Voice Pipeline (LOW)

**Impact**: System doesn't know if user spoke Swahili, English, Dholuo, etc.

**Fix**: Whisper automatically detects language. Pass `detected_language` to superagent context so it can respond in the same language.

---

## 7. Implementation Recommendations

### Phase 1: Backend Transcription (Week 1)

**Priority**: CRITICAL — Without this, voice is completely non-functional.

1. Create `src/services/transcription.py`:
   - Load Whisper model (`base` for speed, `medium` for accuracy)
   - Accept audio bytes + MIME type
   - Convert OGG→WAV using `pydub`
   - Return `{text, language, confidence}`
   - Support both local Whisper and NIM Parakeet as backends

2. Create `src/services/tts_service.py`:
   - Use `edge-tts` (free, Swahili support: `sw-KE-Standard-A`)
   - Accept text + language
   - Return audio bytes (OGG for Telegram)
   - Support NIM RIVA TTS as upgrade path

3. Create `src/channels/audio_handler.py`:
   - Orchestrate: download → transcribe → analyze → synthesize → respond
   - Wire into existing `route_message(message_type="audio")` path

4. Update `requirements-bot.txt`:
   ```
   pydub>=0.25.1
   edge-tts>=6.1.0
   ```

### Phase 2: Telegram Voice Responses (Week 1-2)

**Priority**: HIGH — Telegram already handles voice input; just needs output.

1. Modify `_handle_audio` in `telegram_bot.py`:
   - Call transcription service instead of just forwarding bytes
   - Pass transcribed text to superagent
   - If TTS available, send voice response via `update.message.reply_voice()`
   - Include text transcript alongside voice response

2. Add voice response capability:
   ```python
   # Send voice reply
   tts_bytes = await tts_service.synthesize(response_text, language)
   await update.message.reply_voice(
       voice=InputFile(io.BytesIO(tts_bytes), filename="response.ogg"),
       caption=response_text[:1024]
   )
   ```

### Phase 3: Flutter Voice Input/Output (Week 2-3)

**Priority**: HIGH — Critical for the target user base.

1. Add packages to `pubspec.yaml`
2. Create `lib/services/voice_service.dart`:
   - Recording with `record`
   - STT with `speech_to_text` (offline-capable)
   - TTS with `flutter_tts` (offline-capable)
   - Audio playback with `just_audio`
3. Modify `agent_chat_screen.dart`:
   - Add microphone button (hold-to-record)
   - Add voice message display with playback
   - Add auto-TTS toggle for responses
4. Add voice upload to `api_client.dart`:
   - `uploadAudio()` method for sending voice recordings to backend

### Phase 4: NVIDIA NIM Voice Models (Week 3-4)

**Priority**: MEDIUM — Upgrade path for better quality.

1. Add NIM ASR support to `transcription_service.py`:
   - Parakeet model for domain-specific accuracy
   - Fallback chain: NIM → local Whisper
2. Add NIM TTS support to `tts_service.py`:
   - RIVA TTS for higher quality voice synthesis
   - Fallback chain: NIM → edge-tts → platform TTS
3. Register voice models in `model_registry.py`:
   - A/B test Whisper vs Parakeet accuracy
   - Track latency and accuracy metrics

### Phase 5: Offline Fallback (Week 4)

**Priority**: MEDIUM — Essential for rural deployment.

1. Flutter offline STT: `speech_to_text` uses native platform engines (works offline)
2. Flutter offline TTS: `flutter_tts` uses native platform engines (works offline)
3. Cache common responses in local DB for offline playback
4. Queue voice messages for processing when connectivity returns

---

## 8. Dependencies Required

### Python (Backend)

```toml
# Add to pyproject.toml
"openai-whisper>=20231117",   # Already in requirements-bot.txt
"pydub>=0.25.1",              # Audio format conversion
"edge-tts>=6.1.0",            # Free TTS with Swahili support
```

### Flutter (Mobile)

```yaml
# Add to pubspec.yaml
speech_to_text: ^6.6.0
record: ^5.0.0
flutter_tts: ^3.8.0
just_audio: ^0.9.36
```

### Environment Variables

```bash
# Already exists
NVIDIA_API_KEY=...
NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1

# New (optional)
WHISPER_MODEL_SIZE=base        # tiny|base|small|medium|large
TTS_BACKEND=edge-tts           # edge-tts|nvidia-riva
VOICE_RESPONSE_ENABLED=true
```

---

## 9. Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| Whisper model size on server | MEDIUM | Use `base` model (~150MB); `medium` if accuracy critical |
| edge-tts Swahili voice quality | LOW | Swahili voices available; upgrade to NIM RIVA if needed |
| Flutter STT accuracy for Swahili | MEDIUM | Android has good Swahili support; iOS varies |
| Audio format compatibility | LOW | pydub handles OGG/MP3/WAV conversion |
| Latency for full pipeline | MEDIUM | Target <5s for transcription + analysis + TTS |
| Offline mode limitations | LOW | Native platform STT/TTS works well for common phrases |

---

## 10. Verdict

**The voice pipeline is architecturally desired but functionally absent.**

The Telegram bot has a voice message handler that says "Transcribing audio..." but never actually transcribes anything. The backend has no transcription service, no TTS service, and no audio processing pipeline. The Flutter app cannot record or play voice. NVIDIA NIM is used only for text LLM, not voice models.

The `requirements-bot.txt` includes `openai-whisper` but it's never imported — it's a dependency declaration without implementation.

**To achieve the stated goal** ("speak in Swahili → AI responds"), the minimum viable pipeline requires:
1. Whisper transcription service (~200 lines)
2. TTS synthesis service (~100 lines)
3. Audio handler wiring (~150 lines)
4. Flutter voice packages + UI (~300 lines)

**Estimated effort**: 2-3 weeks for full implementation across all phases.

**The good news**: The existing architecture supports this well. The Telegram bot already handles voice messages and routes them to the backend. The `route_message` API already accepts `message_type="audio"`. The NVIDIA NIM integration works and can be extended to voice models. The Flutter app has a clean service architecture that makes adding voice straightforward.

---

*Council 2 Assessment: Voice capability is the single largest gap between the DAO's ambition (accessible to semi-literate miners) and its reality (text-only interface). This should be the #1 priority after core stability.*
