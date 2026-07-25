# Team 20: Telegram Bot Integration for Mining Super-Agent

> **Document Version:** 1.0  
> **Date:** 2026-07-25  
> **Status:** PRIMARY Communication Channel  
> **Author:** Research Team 20 — Telegram Bot API

---

## Table of Contents

1. [Why Telegram is the Best Choice](#1-why-telegram-is-the-best-choice)
2. [Bot Capabilities for Mining](#2-bot-capabilities-for-mining)
3. [Telegram Bot API Technical Details](#3-telegram-bot-api-technical-details)
4. [Integration Architecture with Mining Super-Agent](#4-integration-architecture-with-mining-super-agent)
5. [Multi-Language Support](#5-multi-language-support)
6. [Bot Commands Reference](#6-bot-commands-reference)
7. [User Experience Flows](#7-user-experience-flows)
8. [Security & Privacy](#8-security--privacy)
9. [Cost Comparison](#9-cost-comparison)
10. [Implementation Code](#10-implementation-code)
11. [Deployment Guide](#11-deployment-guide)
12. [Error Handling & Resilience](#12-error-handling--resilience)
13. [Monitoring & Analytics](#13-monitoring--analytics)

---

## 1. Why Telegram is the Best Choice

### 1.1 The Core Argument

Telegram provides an **official, free Bot API** that eliminates every pain point of WhatsApp integration:

| Concern | WhatsApp Solutions | Telegram Solution |
|---------|-------------------|-------------------|
| **Cost** | Meta API: $0.05-0.10/msg; OpenWA: self-hosted | **FREE — forever** |
| **Ban Risk** | OpenWA: HIGH (unofficial); Meta: low | **ZERO** (official API) |
| **Setup Time** | Meta: days/weeks; OpenWA: hours | **5 minutes** |
| **Hosting** | OpenWA: your server; Meta: Meta's servers | **Telegram's servers** |
| **Rate Limits** | Meta: strict rate limits | **30 msgs/sec to different chats; no per-chat limit** |
| **Official Support** | Meta: yes; OpenWA: no | **Yes — actively maintained** |
| **Phone Number** | Required for WhatsApp account | **Not needed for bot** |

### 1.2 Why This Matters for Mining Cooperatives in Kenya

1. **Zero Cost Barrier**: Miners in rural Kenya cannot afford per-message fees. Telegram bots are completely free.
2. **No Ban Risk**: OpenWA sessions get banned. Mining operations cannot afford downtime. Telegram bots never get banned for normal usage.
3. **Works on Any Device**: Android, iOS, Web, Desktop — miners use whatever phone they have.
4. **Group Support**: Mining cooperatives can create groups where the bot serves all members simultaneously.
5. **Channel Support**: Broadcast price updates, geological alerts, and safety warnings to thousands of miners at once.
6. **Offline-Friendly**: Telegram caches messages locally — miners with intermittent connectivity see everything when they reconnect.
7. **File Sharing**: Send/receive PDF reports, high-res rock photos, geological maps, and documents up to 2GB.
8. **Rich Media**: Photos, voice notes, videos, locations, contacts — all natively supported.
9. **Inline Keyboards**: Interactive buttons for quick actions without typing commands.
10. **No Phone Number Needed**: Bot is identified by username (e.g., `@MiningHelperBot`), not a phone number.

### 1.3 Telegram-Specific Advantages for Mining

- **Photo Analysis Pipeline**: Send rock photo → bot downloads → AI analyzes → responds with mineral ID, all in seconds
- **Voice Message Transcription**: Send voice note in Swahili → Whisper transcribes → agent analyzes → responds in Swahili
- **Location-Based Geology**: Share GPS → cross-reference with geological surveys → provide area-specific analysis
- **Document Generation**: Bot can generate and send PDF geological reports directly in chat
- **Ephemeral Messages** (Bot API 10.2+): Group messages visible only to specific user + bot — perfect for private mineral analysis in group settings
- **Rich Messages** (Bot API 10.1+): Stream AI-generated replies with seamless formatting — ideal for real-time analysis results

---

## 2. Bot Capabilities for Mining

### 2.1 Photo Analysis Pipeline

```
Miner sends rock photo → Telegram Bot receives → Downloads image →
Sends to MIMO Vision API → Analyzes mineral composition →
Formats response in miner's language → Sends back to Telegram
```

**Supported scenarios:**
- Single rock photo with caption describing location/context
- Multiple photos in one message (album) — analyzed together
- Photo with voice note — combined analysis
- High-resolution photos — Telegram supports up to 10MB photos natively

**Response format:**
```
🪨 Mineral Analysis Results

📍 Photo: [thumbnail]
🔍 Identified: Quartz with Pyrite inclusions
⚖️ Confidence: 87%
💰 Gold association: Likely (pyrite often indicates gold)

📊 Current Prices:
  Gold: $4,051/oz (+0.3% today)
  Pyrite: N/A (low commercial value)

💡 Recommendation: This rock sample shows promising indicators.
   Consider professional assaying for gold content.

🌐 Share location for area-specific geological data.
```

### 2.2 Voice Message Processing

```
Miner sends voice note (Swahili) → Telegram Bot receives .ogg file →
Converts to WAV → Whisper transcribes → MIMO Agent analyzes →
Responds in Swahili with text + optional voice reply
```

**Supported languages for voice:**
- Swahili (primary)
- English
- Luo
- Kamba
- Luhya
- Auto-detect

**Voice message flow:**
1. Miner holds mic button, speaks in Swahili
2. Bot receives OGG/Opus audio file
3. Converts to 16kHz WAV for Whisper
4. Transcribes with language detection
5. Agent processes the query
6. Responds with text (and optionally TTS voice reply)

### 2.3 Location-Based Geological Analysis

```
Miner shares GPS location → Telegram Bot receives (lat, lon) →
Cross-references with geological survey databases →
Returns area-specific mineral potential →
Optionally fetches satellite imagery for analysis
```

**Location data integration:**
- Geological survey databases (Kenya, Tanzania, Uganda, DRC)
- Satellite imagery analysis (Sentinel-2, Landsat)
- Historical mining data for the area
- Known mineral deposits in proximity
- Terrain and elevation analysis

**Response format:**
```
📍 Geological Analysis for (-1.2921, 36.8219)

🗺️ Location: Nairobi County, Kenya
⛰️ Elevation: 1,795m
🪨 Geological Formation: Precambrian Basement Complex

💎 Known Minerals in Area:
  - Gold (alluvial deposits reported)
  - Gemstones (tsavorite, garnet)
  - Limestone

⚠️ Mining Potential: MEDIUM
   Historical artisanal mining activity reported.

📊 Nearest Active Mining Sites:
  1. Kilimapesa Gold Mine (45km SW)
  2. Macalder Mines (280km W)

📞 Local Mining Office: +254-XXX-XXXX
```

### 2.4 Document Sharing

**Inbound (Miner → Bot):**
- PDF geological reports for analysis
- Lab assay results for interpretation
- Mining license documents for verification
- Photos of maps, charts, handwritten notes

**Outbound (Bot → Miner):**
- Generated PDF geological reports
- Price history charts (PNG)
- Mineral identification reports
- Mining safety guidelines
- Multi-language documentation

### 2.5 Inline Keyboards (Quick Actions)

```
[📸 Analyze Photo] [💰 Gold Price]
[📍 Share Location] [📊 Generate Report]
[🌐 Language]       [❓ Help]
```

**Callback query handling:**
- Button press → callback_query → bot processes → edits message or sends new
- State machine for multi-step flows (e.g., select mineral → select timeframe → get price chart)
- Per-user state tracking for complex interactions

### 2.6 Group Bot for Mining Cooperatives

**Group features:**
- Bot responds when mentioned (`@MiningHelperBot analyze this`)
- Shared mineral price updates (scheduled)
- Group-wide geological alerts
- Multi-user photo analysis sessions
- Cooperative report generation
- Ephemeral messages for private analysis in group context

**Group commands:**
```
/groupreport — Generate report for the cooperative
/groupprices — Price summary for tracked minerals
/groupalert — Set up area-specific alerts
```

---

## 3. Telegram Bot API Technical Details

### 3.1 Bot Creation (5 minutes)

```
1. Open Telegram → search @BotFather
2. Send /newbot
3. Choose display name: "Mining Super-Agent"
4. Choose username: "MiningHelperBot" (must end in 'bot')
5. Receive token: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
6. Set description, about, profile picture
7. Set commands with /setcommands
```

### 3.2 Webhook vs Polling

| Aspect | Webhook | Polling |
|--------|---------|---------|
| **How it works** | Telegram pushes updates to your URL | Bot constantly asks "any new messages?" |
| **Latency** | ~50ms (instant push) | ~1-5s (depends on poll interval) |
| **Server requirements** | Public HTTPS URL required | Works behind NAT, no public URL |
| **CPU usage** | Near zero (event-driven) | Constant polling uses resources |
| **Scalability** | Excellent (stateless) | Limited by poll frequency |
| **SSL required** | Yes (Telegram requires HTTPS) | No |
| **Best for** | Production deployment | Development/testing |

**Recommendation: WEBHOOK for production, POLLING for development.**

The mining bot should use **webhook mode** in production because:
1. Lower latency = faster responses for miners
2. No constant polling = lower server resource usage
3. Works with FastAPI natively
4. Better for handling bursts (e.g., price alerts to many users)

### 3.3 Message Types Supported

| Type | Telegram Field | Use Case |
|------|---------------|----------|
| Text | `message.text` | Questions, commands, chat |
| Photo | `message.photo[]` | Rock/mineral photo analysis |
| Voice | `message.voice` | Voice notes in Swahili/other languages |
| Video | `message.video` | Video of mining site |
| Document | `message.document` | PDF reports, lab results |
| Location | `message.location` | GPS for geological analysis |
| Contact | `message.contact` | Share contact info |
| Sticker | `message.sticker` | (acknowledge, don't process) |
| Animation/GIF | `message.animation` | (acknowledge) |
| Audio | `message.audio` | (voice notes use `voice` type) |

### 3.4 Inline Keyboard Implementation

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Main menu keyboard
main_menu = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📸 Analyze Photo", callback_data="action:photo"),
        InlineKeyboardButton("💰 Gold Price", callback_data="action:price:gold"),
    ],
    [
        InlineKeyboardButton("📍 Share Location", callback_data="action:location"),
        InlineKeyboardButton("📊 Generate Report", callback_data="action:report"),
    ],
    [
        InlineKeyboardButton("🌐 Language", callback_data="action:language"),
        InlineKeyboardButton("❓ Help", callback_data="action:help"),
    ],
])

# Language selection keyboard
language_menu = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
        InlineKeyboardButton("🇰🇪 Kiswahili", callback_data="lang:sw"),
    ],
    [
        InlineKeyboardButton("🇰🇪 Dholuo", callback_data="lang:luo"),
        InlineKeyboardButton("🇰🇪 Kamba", callback_data="lang:kam"),
    ],
    [
        InlineKeyboardButton("🇰🇪 Luhya", callback_data="lang:luy"),
    ],
])
```

### 3.5 Callback Query Handling

```python
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Required to stop loading indicator

    action, *params = query.data.split(":")

    if action == "action":
        if params[0] == "photo":
            await query.edit_message_text(
                "📸 Please send a photo of the rock/mineral you want analyzed.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="action:menu")
                ]])
            )
        elif params[0] == "price":
            mineral = params[1] if len(params) > 1 else "gold"
            price = await get_mineral_price(mineral)
            await query.edit_message_text(
                f"💰 {mineral.title()} Price: ${price}/oz",
                reply_markup=main_menu
            )

    elif action == "lang":
        lang_code = params[0]
        context.user_data["language"] = lang_code
        await query.edit_message_text(
            get_text(lang_code, "language_set"),
            reply_markup=main_menu
        )
```

### 3.6 File Download and Upload

```python
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download and process photos sent by miners."""
    message = update.message

    # Get the highest resolution photo
    photo = message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    # Download to local storage
    file_path = f".openclaw/tmp/photos/{photo.file_unique_id}.jpg"
    await file.download_to_drive(file_path)

    # Process with MIMO Vision
    analysis = await analyze_mineral_photo(file_path, message.caption)

    # Send response
    await message.reply_text(analysis, reply_markup=main_menu)


async def send_report_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and send a PDF report."""
    report_path = await generate_geological_report(context.user_data)

    await update.message.reply_document(
        document=open(report_path, "rb"),
        filename="geological_report.pdf",
        caption="📊 Your geological report is ready!"
    )
```

---

## 4. Integration Architecture with Mining Super-Agent

### 4.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TELEGRAM CLOUD                           │
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐                │
│   │ Miner A  │    │ Miner B  │    │ Coop     │                │
│   │ (Phone)  │    │ (Phone)  │    │ Group    │                │
│   └────┬─────┘    └────┬─────┘    └────┬─────┘                │
│        │               │               │                       │
│        └───────────────┼───────────────┘                       │
│                        │                                       │
│                  ┌─────▼─────┐                                 │
│                  │ Telegram  │                                 │
│                  │ Bot API   │                                 │
│                  └─────┬─────┘                                 │
└────────────────────────┼───────────────────────────────────────┘
                         │
                    HTTPS Webhook
                         │
┌────────────────────────┼───────────────────────────────────────┐
│                  ┌─────▼─────┐                                 │
│                  │  FastAPI   │  (Webhook Endpoint)             │
│                  │  Server    │                                 │
│                  └─────┬─────┘                                 │
│                        │                                       │
│           ┌────────────┼────────────┐                          │
│           │            │            │                          │
│    ┌──────▼──────┐ ┌───▼────┐ ┌────▼─────┐                   │
│    │ Message     │ │Session │ │ Language  │                   │
│    │ Router      │ │Manager │ │ Detector  │                   │
│    └──────┬──────┘ └────────┘ └──────────┘                   │
│           │                                                    │
│    ┌──────▼──────────────────────────────────┐                │
│    │        Mining Super-Agent (DeerFlow)     │                │
│    │                                          │                │
│    │  ┌─────────┐ ┌──────────┐ ┌──────────┐ │                │
│    │  │ Photo   │ │ Voice    │ │ Location │ │                │
│    │  │ Analyzer│ │Transcribe│ │ Geology  │ │                │
│    │  └─────────┘ └──────────┘ └──────────┘ │                │
│    │  ┌─────────┐ ┌──────────┐ ┌──────────┐ │                │
│    │  │ Price   │ │ Report   │ │ Memory   │ │                │
│    │  │ Tracker │ │Generator │ │ Store    │ │                │
│    │  └─────────┘ └──────────┘ └──────────┘ │                │
│    └─────────────────────────────────────────┘                │
│                                                               │
│                    MINING PLATFORM                             │
└───────────────────────────────────────────────────────────────┘
```

### 4.2 Webhook → FastAPI → Agent → Response → Telegram

```python
# webhook_server.py — Complete FastAPI + Telegram integration

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters
)
import os

app = FastAPI()

# Initialize Telegram bot application
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://your-domain.com/webhook")

# Create the Telegram Application
telegram_app = (
    Application.builder()
    .token(TELEGRAM_TOKEN)
    .updater(None)  # Disable updater for webhook mode
    .build()
)

# Register handlers
telegram_app.add_handler(CommandHandler("start", start_handler))
telegram_app.add_handler(CommandHandler("help", help_handler))
telegram_app.add_handler(CommandHandler("price", price_handler))
telegram_app.add_handler(CommandHandler("report", report_handler))
telegram_app.add_handler(CommandHandler("language", language_handler))
telegram_app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
telegram_app.add_handler(MessageHandler(filters.VOICE, voice_handler))
telegram_app.add_handler(MessageHandler(filters.LOCATION, location_handler))
telegram_app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
telegram_app.add_handler(CallbackQueryHandler(callback_handler))


@app.on_event("startup")
async def startup():
    """Initialize bot and set webhook on startup."""
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        allowed_updates=Update.ALL_TYPES
    )
    await telegram_app.start()


@app.on_event("shutdown")
async def shutdown():
    """Clean shutdown."""
    await telegram_app.stop()
    await telegram_app.shutdown()


@app.post("/webhook")
async def webhook(request: Request):
    """Receive Telegram updates via webhook."""
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "bot": "Mining Super-Agent"}
```

### 4.3 Message Routing Based on Type

```python
# handlers/router.py — Message routing logic

from telegram import Update
from telegram.ext import ContextTypes
from mining_agent import MiningAgent
from language import detect_language, get_text

agent = MiningAgent()


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route text messages to the agent."""
    user_id = update.effective_user.id
    lang = context.user_data.get("language", "auto")

    # Detect language if auto
    if lang == "auto":
        lang = detect_language(update.message.text)

    # Get session context
    session = get_or_create_session(user_id)

    # Process through Mining Super-Agent
    response = await agent.chat(
        user_id=user_id,
        message=update.message.text,
        session=session,
        language=lang
    )

    await update.message.reply_text(response, reply_markup=main_menu)


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route photo messages to the photo analysis pipeline."""
    user_id = update.effective_user.id
    lang = context.user_data.get("language", "en")

    # Send "analyzing..." indicator
    await update.message.reply_text(get_text(lang, "analyzing_photo"))

    # Download highest-res photo
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_path = f".openclaw/tmp/photos/{photo.file_unique_id}.jpg"
    await file.download_to_drive(file_path)

    # Analyze with Mining Agent
    caption = update.message.caption or ""
    analysis = await agent.analyze_photo(
        user_id=user_id,
        photo_path=file_path,
        caption=caption,
        language=lang
    )

    # Send result with inline keyboard
    await update.message.reply_text(
        analysis,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Get Report", callback_data="action:report"),
                InlineKeyboardButton("📍 Share Location", callback_data="action:location"),
            ],
            [InlineKeyboardButton("💰 Check Price", callback_data="action:price")],
        ])
    )


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route voice messages to the transcription + analysis pipeline."""
    user_id = update.effective_user.id
    lang = context.user_data.get("language", "auto")

    await update.message.reply_text(get_text(lang, "processing_voice"))

    # Download voice file (OGG/Opus)
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    ogg_path = f".openclaw/tmp/voice/{voice.file_unique_id}.ogg"
    await file.download_to_drive(ogg_path)

    # Convert to WAV for Whisper
    wav_path = ogg_path.replace(".ogg", ".wav")
    await convert_audio(ogg_path, wav_path)

    # Transcribe with Whisper
    transcription = await transcribe_voice(wav_path, language=lang)

    # Process transcription through agent
    response = await agent.chat(
        user_id=user_id,
        message=transcription,
        session=get_or_create_session(user_id),
        language=lang
    )

    # Send text response
    await update.message.reply_text(
        f"🎤 *You said:* {transcription}\n\n{response}",
        parse_mode="Markdown",
        reply_markup=main_menu
    )


async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route location messages to the geological analysis pipeline."""
    user_id = update.effective_user.id
    lang = context.user_data.get("language", "en")
    lat = update.message.location.latitude
    lon = update.message.location.longitude

    await update.message.reply_text(get_text(lang, "analyzing_location"))

    # Geological analysis through agent
    analysis = await agent.analyze_location(
        user_id=user_id,
        latitude=lat,
        longitude=lon,
        language=lang
    )

    await update.message.reply_text(analysis, reply_markup=main_menu)


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route document messages to the document analysis pipeline."""
    user_id = update.effective_user.id
    lang = context.user_data.get("language", "en")
    doc = update.message.document

    # Check file size (max 20MB)
    if doc.file_size > 20 * 1024 * 1024:
        await update.message.reply_text(get_text(lang, "file_too_large"))
        return

    await update.message.reply_text(get_text(lang, "processing_document"))

    # Download document
    file = await context.bot.get_file(doc.file_id)
    file_path = f".openclaw/tmp/docs/{doc.file_unique_id}_{doc.file_name}"
    await file.download_to_drive(file_path)

    # Process through agent
    analysis = await agent.analyze_document(
        user_id=user_id,
        file_path=file_path,
        file_name=doc.file_name,
        language=lang
    )

    await update.message.reply_text(analysis, reply_markup=main_menu)
```

### 4.4 Session Management Per User

```python
# session.py — Per-user session management

import json
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

SESSION_DIR = Path(".openclaw/data/sessions")
SESSION_DIR.mkdir(parents=True, exist_ok=True)

SESSION_TIMEOUT = 3600 * 24  # 24 hours


@dataclass
class UserSession:
    user_id: int
    username: str = ""
    first_name: str = ""
    language: str = "en"
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    conversation_history: list = field(default_factory=list)
    location: Optional[dict] = None  # {"lat": ..., "lon": ...}
    last_analysis: Optional[dict] = None
    preferences: dict = field(default_factory=dict)

    def is_expired(self) -> bool:
        return (time.time() - self.last_active) > SESSION_TIMEOUT

    def touch(self):
        self.last_active = time.time()

    def add_message(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        # Keep last 50 messages
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]
        self.touch()

    def save(self):
        path = SESSION_DIR / f"{self.user_id}.json"
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, user_id: int) -> Optional["UserSession"]:
        path = SESSION_DIR / f"{user_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        session = cls(**data)
        if session.is_expired():
            path.unlink()
            return None
        return session


def get_or_create_session(user_id: int, username: str = "", first_name: str = "") -> UserSession:
    session = UserSession.load(user_id)
    if session is None:
        session = UserSession(
            user_id=user_id,
            username=username,
            first_name=first_name
        )
        session.save()
    return session
```

---

## 5. Multi-Language Support

### 5.1 Supported Languages

| Code | Language | Region | Speakers (Kenya) | Priority |
|------|----------|--------|-------------------|----------|
| `en` | English | National | ~20M | Default |
| `sw` | Kiswahili | National | ~40M | Primary |
| `luo` | Dholuo | Nyanza | ~6M | Valentine's community |
| `kam` | Kamba | Eastern | ~5M | Mining communities |
| `luy` | Luhya | Western | ~7M | Mining communities |

### 5.2 Language Detection

```python
# language.py — Language detection and text management

import re
from typing import Optional

# Swahili common words
SWAHILI_WORDS = {
    "habari", "nzuri", "sana", "na", "ya", "wa", "kwa", "ni",
    "hii", "hiyo", "ile", "hizi", "hizo", "zile", "mimi", "wewe",
    "yeye", "sisi", "nyao", "wao", "dhahabu", "mawe", "madini",
    "uchimbaji", "mgodi", "shaba", "fedha", "jiwe", "mwamba"
}

# Luo common words
LUO_WORDS = {
    "maber", "ka", "gi", "e", "to", "nyo", "onge", "nade",
    "koro", "chuth", "thuolo", "ot", "apwoyo", "eyo", "in",
    "dhahabu", "wuod", "nyako", "nyar", "los", "piny"
}

# Kamba common words
KAMBA_WORDS = {
    "wĩ", "ya", "wa", "na", "ũũ", "ĩĩ", "aa", "mũnene",
    "ndũ", "mũ", "ũ", "ĩ", "syĩ", "we", "ndwa"
}

# Luhya common words
LUHYA_WORDS = {
    "muno", "khu", "na", "va", "khu", "múla", "sì", "tsino",
    "inyu", "niye", "khutsa", "omúla", "amúla", "evo"
}


def detect_language(text: str) -> str:
    """Detect language from text content."""
    words = set(text.lower().split())
    clean_words = {re.sub(r'[^\w]', '', w) for w in words}

    scores = {
        "sw": len(clean_words & SWAHILI_WORDS),
        "luo": len(clean_words & LUO_WORDS),
        "kam": len(clean_words & KAMBA_WORDS),
        "luy": len(clean_words & LUHYA_WORDS),
    }

    best = max(scores, key=scores.get)
    if scores[best] >= 2:
        return best
    return "en"  # Default to English


# Text translations for bot UI
TRANSLATIONS = {
    "welcome": {
        "en": "⛏️ Welcome to Mining Super-Agent!\n\nI can help you with:\n📸 Rock/mineral photo analysis\n💰 Real-time mineral prices\n📍 Location-based geological data\n📊 Geological reports\n🎤 Voice message analysis\n\nSend a photo, voice note, or location to get started!",
        "sw": "⛏️ Karibu kwenye Mining Super-Agent!\n\nNinaweza kukusaidia na:\n📸 Kuchambua picha za mawe/madini\n💰 Bei za madini kwa wakati halisi\n📍 Data ya kijiolojia kulingana na eneo\n📊 Ripoti za kijiolojia\n🎤 Kuchambua ujumbe wa sauti\n\nTuma picha, ujumbe wa sauti, au eneo kuanza!",
        "luo": "⛏️ Maribea e Mining Super-Agent!\n\nAbiro konyi gi:\n📸 Ng'enyi/misawa mag picha\n💰 Pes mar madini seche\n📍 Data mag jiolojia mag piny\n📊 Ripoti mag jiolojia\n🎤 Ng'enyi mag law mar sauti\n\nOro picha, law mar sauti, kata piny ka chakri!",
        "kam": "⛏️ Wĩ mwĩa wa Mining Super-Agent!\n\nNĩngũkwĩsyĩa na:\n📸 Kũchambua mawe/madini\n💰 Athĩĩ ma madini\n📍 Data ya jiolojia yaũũ\n📊 Ripoti za jiolojia\n🎤 Kũchambua lawa ya sauti\n\nOra picha, lawa ya sauti, kana ũũ!",
        "luy": "⛏️ Múla khutsa Mining Super-Agent!\n\nNdzakhusĩtsa na:\n📸 Khulenga mawe/madini\n💰 Pesa sya madini siche\n📍 Data ya jiolojia ya piny\n📊 Ripoti sya jiolojia\n🎤 Khulenga lawa sa sauti\n\nOla picha, lawa sa sauti, kana piny!",
    },
    "analyzing_photo": {
        "en": "🔍 Analyzing your photo... Please wait.",
        "sw": "🔍 Ninachambua picha yako... Tafadhali subiri.",
        "luo": "🔍 Analo ng'enyi pichani ni... Karia wachamo.",
        "kam": " "Nĩnĩchambua picha yaku... Ndũa kũthĩĨĨa.",
        "luy": " "NĨkhulengela picha yoye... Khali khutsa.",
    },
    "processing_voice": {
        "en": "🎤 Processing your voice message...",
        "sw": "🎤 Ninachakata ujumbe wako wa sauti...",
        "luo": "🎤 Analo ng'enyi law mar sauti ni...",
        "kam": " "Nĩnĩchakata lawa yaku ya sauti...",
        "luy": " "NĨkhulengela lawa yoye sa sauti...",
    },
    "analyzing_location": {
        "en": "📍 Analyzing geological data for your location...",
        "sw": "📍 Ninachambua data ya kijiolojia ya eneo lako...",
        "luo": " "Analo ng'enyi data mag jiolojia mag piny ni...",
        "kam": " "Nĩnĩchambua data ya jiolojia yaũũ...",
        "luy": " "NĨkhulengela data ya jiolojia ya piny...",
    },
    "processing_document": {
        "en": "📄 Processing your document...",
        "sw": "📄 Ninachakata hati yako...",
        "luo": " "Analo ng'enyi hati ni...",
        "kam": " "Nĩnĩchakata hati yaku...",
        "luy": " "NĨkhulengela hati yoye...",
    },
    "language_set": {
        "en": "✅ Language set to English",
        "sw": "✅ Lugha imewekwa Kiswahili",
        "luo": " "Dhok oseto e Dholuo",
        "kam": " "Kĩĩĩ kĩĩseto kĩĩKamba",
        "luy": " "Olushakha lũseto kũLũhya",
    },
    "error_generic": {
        "en": "❌ Something went wrong. Please try again.",
        "sw": "❌ Kuna hitilafu. Tafadhali jaribu tena.",
        "luo": " "En gini moro. Karia tem duto.",
        "kam": " "Kũna kĩĩũ. Ndũa kũũa.",
        "luy": " "Khutsa muno. Khali tem.",
    },
}


def get_text(lang: str, key: str) -> str:
    """Get translated text for a given language and key."""
    return TRANSLATIONS.get(key, {}).get(lang, TRANSLATIONS.get(key, {}).get("en", key))
```

### 5.3 Language Switching Flow

```python
async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show language selection menu."""
    await update.message.reply_text(
        "🌐 Select your language / Chagua lugha yako:",
        reply_markup=language_menu
    )


async def callback_language(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_code: str):
    """Handle language selection callback."""
    context.user_data["language"] = lang_code
    session = get_or_create_session(update.effective_user.id)
    session.language = lang_code
    session.save()

    await update.callback_query.edit_message_text(
        get_text(lang_code, "language_set")
    )
```

---

## 6. Bot Commands Reference

### 6.1 Command Registration with BotFather

```
start - Start the bot and see welcome message
help - Show all available commands
photo - Instructions for sending a rock photo
price - Get current mineral price (e.g., /price gold)
location - Share GPS for geological analysis
report - Generate a geological report
language - Change language (English, Swahili, Luo, etc.)
voice - Instructions for sending voice messages
status - Check bot and service status
about - About Mining Super-Agent
```

### 6.2 Command Handlers

```python
# handlers/commands.py

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    lang = context.user_data.get("language", "en")

    # Create/update session
    session = get_or_create_session(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or ""
    )
    session.save()

    welcome_text = get_text(lang, "welcome")
    await update.message.reply_text(welcome_text, reply_markup=main_menu)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    lang = context.user_data.get("language", "en")

    help_texts = {
        "en": """📖 **Available Commands:**

/start — Welcome message and bot introduction
/help — Show this help message
/photo — How to send a rock photo for analysis
/price [mineral] — Get current price (e.g., /price gold)
/location — Share GPS location for geological analysis
/report — Generate a geological report
/language — Change language
/voice — How to send a voice message
/status — Check bot status

**Or just:**
📸 Send a photo of a rock → mineral analysis
🎤 Send a voice note → transcribed and analyzed
📍 Share location → geological data
📄 Send a document → analyzed and interpreted""",
        "sw": """📖 **Amri Zinazopatikana:**

/start — Ujumbe wa kukaribisha na utambulisho wa bot
/help — Onyesha ujumbe huu wa msaada
/photo — Jinsi ya kutuma picha ya mawe kuchambuliwa
/price [madini] — Pata bei ya sasa (mfano: /price gold)
/location — Shiriki eneo la GPS kwa uchambuzi wa kijiolojia
/report — Tengeneza ripoti ya kijiolojia
/language — Badilisha lugha
/voice — Jinsi ya kutuma ujumbe wa sauti
/status — Angalia hali ya bot

**Au tu:**
📸 Tuma picha ya mawe → uchambuzi wa madini
🎤 Tuma ujumbe wa sauti → kunakiliwa na kuchambuliwa
📍 Shiriki eneo → data ya kijiolojia
📄 Tuma hati → kuchambuliwa na kutafsiriwa""",
    }

    await update.message.reply_text(
        help_texts.get(lang, help_texts["en"]),
        parse_mode="Markdown"
    )


async def price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /price [mineral] command."""
    lang = context.user_data.get("language", "en")
    args = context.args

    if not args:
        await update.message.reply_text(
            "💰 Usage: /price [mineral]\n"
            "Examples: /price gold, /price silver, /price copper\n\n"
            "Or use the button below:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💰 Gold", callback_data="action:price:gold"),
                InlineKeyboardButton("🥈 Silver", callback_data="action:price:silver"),
                InlineKeyboardButton("🥉 Copper", callback_data="action:price:copper"),
            ]])
        )
        return

    mineral = " ".join(args).lower()
    price_data = await get_mineral_price(mineral)

    if price_data:
        response = (
            f"💰 **{mineral.title()} Price**\n\n"
            f"💵 Current: ${price_data['price']:,.2f}/{price_data['unit']}\n"
            f"📈 24h change: {price_data['change']:+.2f}%\n"
            f"📊 7d change: {price_data['week_change']:+.2f}%\n"
            f"🕐 Updated: {price_data['timestamp']}"
        )
    else:
        response = f"❌ Could not find price data for '{mineral}'.\nTry: gold, silver, copper, tin, coltan"

    await update.message.reply_text(response, parse_mode="Markdown")


async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /report command — generate geological report."""
    lang = context.user_data.get("language", "en")
    session = get_or_create_session(update.effective_user.id)

    if not session.location:
        await update.message.reply_text(
            get_text(lang, "location_required_for_report"),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📍 Share Location", callback_data="action:location")
            ]])
        )
        return

    await update.message.reply_text(get_text(lang, "generating_report"))

    # Generate report through Mining Agent
    report_path = await agent.generate_report(
        user_id=update.effective_user.id,
        session=session,
        language=lang
    )

    # Send PDF
    await update.message.reply_document(
        document=open(report_path, "rb"),
        filename=f"geological_report_{update.effective_user.id}.pdf",
        caption=get_text(lang, "report_ready")
    )
```

---

## 7. User Experience Flows

### 7.1 First-Time User Flow (Swahili)

```
Miner: [Searches "MiningHelperBot" in Telegram]
       [Taps "Start"]

Bot:   ⛏️ Karibu kwenye Mining Super-Agent!

       Ninaweza kukusaidia na:
       📸 Kuchambua picha za mawe/madini
       💰 Bei za madini kwa wakati halisi
       📍 Data ya kijiolojia kulingana na eneo
       📊 Ripoti za kijiolojia
       🎤 Kuchambua ujumbe wa sauti

       [📸 Analyze Photo] [💰 Gold Price]
       [📍 Share Location] [📊 Generate Report]
       [🌐 Language]       [❓ Help]

Miner: [Taps "🌐 Language"]
Bot:   🌐 Select your language / Chagua lugha yako:
       [🇬🇧 English] [🇰🇪 Kiswahili]
       [🇰🇪 Dholuo]  [🇰🇪 Kamba]
       [🇰🇪 Luhya]

Miner: [Taps "🇰🇪 Kiswahili"]
Bot:   ✅ Lugha imewekwa Kiswahili
```

### 7.2 Photo Analysis Flow

```
Miner: [Sends photo of rock with caption: "Nilipata hii mgodini"]

Bot:   🔍 Ninachambua picha yako... Tafadhali subiri.
       [⏳ typing indicator...]

Bot:   🪨 **Matokeo ya Uchambuzi wa Madini**

       📍 Picha: [thumbnail]
       🔍 Iliyotambuliwa: Quartz yenye Pyrite
       ⚖️ Uhakika: 87%
       💰 Uhusiano na dhahabu: Unawezekana
          (Pyrite mara nyingi inaonyesha dhahabu)

       📊 Bei za Sasa:
         Dhahabu: $4,051/oz (+0.3% leo)
         Pyrite: N/A (thamani ya chini ya kibiashara)

       💡 Mapendekezo: Sampuli hii ya mawe inaonyesha
          dalili zinazotia matumaini.
          Fikiria kupimwa kitaalamu kwa maudhui ya dhahabu.

       🌐 Shiriki eneo lako kwa data ya kijiolojia
          ya eneo husika.

       [📊 Get Report] [📍 Share Location]
       [💰 Check Price]
```

### 7.3 Voice Message Flow

```
Miner: [Holds mic button, speaks in Swahili]
       "Habari, nimepata mawe ya njano mgodini.
        Je, ni dhahabu?"

Bot:   🎤 Ninachakata ujumbe wako wa sauti...
       [⏳ typing indicator...]

Bot:   🎤 *Ulilosema:* "Habari, nimepata mawe ya njano mgodini. Je, ni dhahabu?"

       🪨 Kulingana na maelezo yako, mawe ya njano
       mgodini yanaweza kuwa:

       1. **Dhahabu** (Au) - Rangi ya njano, inang'aa
          chini ya jua, laini
       2. **Pyrite** (FeS₂) - "Dhahabu ya mpumbavu" -
          ngumu, inavunjika
       3. **Chalcopyrite** (CuFeS₂) - Shaba yenye rangi
          ya njano

       🔬 Jinsi ya kutambua:
       - Dhahabu: laini, haivunjiki, inang'aa daima
       - Pyrite: ngumu, inavunjika, rangi inapungua

       📸 Tuma picha ya mawe hayo kwa uchambuzi
       wa uhakika zaidi.

       [📸 Analyze Photo] [💰 Gold Price]
```

### 7.4 Location-Based Geological Flow

```
Miner: [Taps 📍 button, shares GPS location]
       Location: -1.2921, 36.8219

Bot:   📍 Ninachambua data ya kijiolojia ya eneo lako...

Bot:   📍 **Uchambuzi wa Kijiolojia**

       🗺️ Eneo: Kaunti ya Nairobi, Kenya
       ⛰️ Kimo: 1,795m
       🪨 Mfumo wa Kijiolojia: Precambrian Basement Complex

       💎 Madini Yanayojulikana Eneo Hili:
         - Dhahabu (mapato ya alluvial yameripotiwa)
         - Vito (tsavorite, garnet)
         - Chokaa

       ⚠️ Uwezo wa Uchimbaji: WASTANI
          Shughuli za uchimbaji wa jadi zimeripotiwa.

       📊 Maeneo ya Uchimbaji Yanayokaribu:
         1. Kilimapesa Gold Mine (45km SW)
         2. Macalder Mines (280km W)

       [📊 Generate Report] [📸 Analyze Photo]
```

---

## 8. Security & Privacy

### 8.1 Telegram's Security Model

| Feature | Description |
|---------|-------------|
| **MTProto 2.0** | Telegram's proprietary encryption protocol |
| **Cloud Chats** | Encrypted client-to-server (default for bots) |
| **Secret Chats** | End-to-end encryption (not available for bots) |
| **Data Storage** | Encrypted at rest on Telegram's distributed servers |
| **No Meta Data** | No data shared with Meta/Facebook |
| **Open Source** | Client apps are open source |
| **Self-Destruct** | Messages can auto-delete |

### 8.2 Bot-Specific Security

1. **Bot Token Security**:
   - Store in environment variables, NEVER in code
   - Rotate if compromised (BotFather → /revoke)
   - Use separate tokens for dev/staging/production

2. **User Data Handling**:
   - Store user sessions locally (not on Telegram servers)
   - Encrypt sensitive data at rest
   - Implement data retention policies (auto-delete after 30 days)
   - Allow users to delete their data (`/delete_my_data`)

3. **No Analytics/Tracking**:
   - No third-party analytics
   - No advertising networks
   - No cross-platform tracking

4. **GDPR Compliance**:
   - Users can request data export (`/mydata`)
   - Users can delete all data (`/delete_my_data`)
   - Clear privacy policy accessible via `/privacy`

### 8.3 Security Implementation

```python
# security.py — Privacy and security handlers

async def privacy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show privacy policy."""
    lang = context.user_data.get("language", "en")
    await update.message.reply_text(
        get_text(lang, "privacy_policy"),
        parse_mode="Markdown"
    )


async def delete_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user data deletion request."""
    user_id = update.effective_user.id
    session_path = Path(f".openclaw/data/sessions/{user_id}.json")

    if session_path.exists():
        session_path.unlink()

    # Also delete any cached files
    for dir_path in [".openclaw/tmp/photos", ".openclaw/tmp/voice", ".openclaw/tmp/docs"]:
        for f in Path(dir_path).glob(f"*{user_id}*"):
            f.unlink()

    await update.message.reply_text(
        "✅ All your data has been deleted.\n"
        "You can start fresh with /start"
    )


async def my_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export user's data."""
    user_id = update.effective_user.id
    session = UserSession.load(user_id)

    if session:
        data = json.dumps(asdict(session), indent=2, ensure_ascii=False)
        # Send as file
        data_path = Path(f".openclaw/tmp/export_{user_id}.json")
        data_path.write_text(data)

        await update.message.reply_document(
            document=open(data_path, "rb"),
            filename=f"my_data_{user_id}.json",
            caption="📊 Your data export"
        )
        data_path.unlink()
    else:
        await update.message.reply_text("No data stored for your account.")
```

---

## 9. Cost Comparison

### 9.1 Comprehensive Cost Analysis

| Feature | Telegram Bot API | OpenWA (WhatsApp) | Meta WhatsApp Cloud API |
|---------|-----------------|-------------------|------------------------|
| **Monthly Cost** | **$0** | $5-20 (server) | $0.05-0.10 per message |
| **Messages/Month** | **Unlimited** | Unlimited | Rate-limited |
| **Ban Risk** | **None** | Medium-High | None |
| **Setup Time** | **5 minutes** | Hours | Days-weeks |
| **Hosting** | **Telegram's servers** | Your server | Meta's servers |
| **Server Required** | **No** (webhook needs one) | Yes | No |
| **Phone Number** | **Not needed** | Required | Required |
| **Official API** | **Yes** | No (unofficial) | Yes |
| **Group Support** | **Yes** (up to 200K members) | Yes (limited) | Yes (limited) |
| **Channel Support** | **Yes** (unlimited subscribers) | No | No |
| **File Size Limit** | **2GB** | 100MB | 100MB |
| **Inline Buttons** | **Yes** | No | Yes (limited) |
| **Voice Messages** | **Yes** | Yes | Yes |
| **Location Sharing** | **Yes** | Yes | Yes |
| **Photo Analysis** | **Yes** (up to 10MB) | Yes | Yes |
| **Webhook Support** | **Yes** (native) | No | Yes |
| **Bot Discovery** | **Search in Telegram** | No | No |
| **Multi-Device** | **Yes** | Limited | Limited |

### 9.2 Cost Projection for 10,000 Miners

| Metric | Telegram | Meta WhatsApp | Notes |
|--------|----------|---------------|-------|
| Users | 10,000 | 10,000 | Same user base |
| Messages/day | 50,000 | 50,000 | 5 msgs/user/day |
| Messages/month | 1,500,000 | 1,500,000 | |
| Cost/month | **$0** | **$75,000-150,000** | At $0.05-0.10/msg |
| Cost/year | **$0** | **$900,000-1,800,000** | |
| Server cost/month | $20-50 | $0 | FastAPI + worker |
| **Total/year** | **$240-600** | **$900,000-1,800,000** | |

**Savings: $899,400 - $1,799,400 per year by using Telegram.**

### 9.3 Break-Even Analysis

Even if we need to self-host the bot server:
- **Telegram server cost**: ~$20-50/month (small VPS for FastAPI)
- **Meta WhatsApp cost**: $75,000+/month for 10K users
- **Break-even**: Never — Telegram is always cheaper for bots

---

## 10. Implementation Code

### 10.1 Project Structure

```
mining-telegram-bot/
├── main.py                    # FastAPI entry point
├── config.py                  # Configuration
├── requirements.txt           # Dependencies
├── .env.example              # Environment template
│
├── bot/
│   ├── __init__.py
│   ├── app.py                # Telegram Application setup
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── commands.py       # /start, /help, /price, etc.
│   │   ├── messages.py       # Text, photo, voice, location, document
│   │   ├── callbacks.py      # Inline keyboard callbacks
│   │   └── errors.py         # Error handlers
│   └── keyboards.py          # Inline keyboard definitions
│
├── agent/
│   ├── __init__.py
│   ├── mining_agent.py       # Mining Super-Agent interface
│   ├── photo_analyzer.py     # Photo analysis pipeline
│   ├── voice_processor.py    # Voice transcription pipeline
│   ├── location_analyzer.py  # Geological analysis
│   ├── price_tracker.py      # Mineral price tracking
│   └── report_generator.py   # PDF report generation
│
├── i18n/
│   ├── __init__.py
│   ├── detector.py           # Language detection
│   ├── translations.py       # All UI translations
│   └── languages/
│       ├── en.json
│       ├── sw.json
│       ├── luo.json
│       ├── kam.json
│       └── luy.json
│
├── session/
│   ├── __init__.py
│   └── manager.py            # Per-user session management
│
├── utils/
│   ├── __init__.py
│   ├── audio.py              # Audio conversion (OGG → WAV)
│   └── file.py               # File handling utilities
│
└── tests/
    ├── test_handlers.py
    ├── test_agent.py
    └── test_i18n.py
```

### 10.2 Complete main.py

```python
# main.py — FastAPI + Telegram Bot entry point

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters
)

from config import Settings
from bot.handlers.commands import (
    start_handler, help_handler, price_handler,
    report_handler, language_handler, status_handler,
    delete_data_handler, my_data_handler
)
from bot.handlers.messages import (
    text_handler, photo_handler, voice_handler,
    location_handler, document_handler
)
from bot.handlers.callbacks import callback_handler
from bot.handlers.errors import error_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage Telegram bot lifecycle with FastAPI."""
    # Startup
    logger.info("Starting Mining Super-Agent Telegram Bot...")

    telegram_app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .updater(None)
        .build()
    )

    # Register all handlers
    telegram_app.add_handler(CommandHandler("start", start_handler))
    telegram_app.add_handler(CommandHandler("help", help_handler))
    telegram_app.add_handler(CommandHandler("price", price_handler))
    telegram_app.add_handler(CommandHandler("report", report_handler))
    telegram_app.add_handler(CommandHandler("language", language_handler))
    telegram_app.add_handler(CommandHandler("status", status_handler))
    telegram_app.add_handler(CommandHandler("delete_my_data", delete_data_handler))
    telegram_app.add_handler(CommandHandler("mydata", my_data_handler))

    telegram_app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    telegram_app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    telegram_app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    telegram_app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    telegram_app.add_handler(CallbackQueryHandler(callback_handler))
    telegram_app.add_error_handler(error_handler)

    # Initialize and set webhook
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(
        url=f"{settings.WEBHOOK_URL}/webhook",
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )
    await telegram_app.start()

    # Store in app state
    app.state.telegram_app = telegram_app
    logger.info(f"Bot started. Webhook set to {settings.WEBHOOK_URL}/webhook")

    yield  # App is running

    # Shutdown
    logger.info("Shutting down bot...")
    await telegram_app.stop()
    await telegram_app.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Mining Super-Agent Telegram Bot",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/webhook")
async def webhook(request: Request):
    """Receive Telegram updates via webhook."""
    data = await request.json()
    update = Update.de_json(data, app.state.telegram_app.bot)
    await app.state.telegram_app.process_update(update)
    return Response(status_code=200)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "mining-telegram-bot",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Mining Super-Agent Telegram Bot",
        "status": "running",
        "docs": "/docs"
    }
```

### 10.3 Configuration

```python
# config.py

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    WEBHOOK_URL: str = "https://your-domain.com"

    # Mining Agent
    MINING_AGENT_URL: str = "http://localhost:8000"
    MIMO_API_KEY: Optional[str] = None

    # Database
    SESSION_DIR: str = ".openclaw/data/sessions"

    # Audio
    WHISPER_MODEL: str = "whisper-1"
    AUDIO_SAMPLE_RATE: int = 16000

    # Rate Limiting
    MAX_MESSAGES_PER_MINUTE: int = 30
    MAX_PHOTO_SIZE_MB: int = 10
    MAX_DOCUMENT_SIZE_MB: int = 20

    class Config:
        env_file = ".env"
```

### 10.4 Requirements

```txt
# requirements.txt

python-telegram-bot[webhooks]==22.8
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic-settings==2.5.0
httpx==0.27.0
Pillow==10.4.0
pydub==0.25.1
openai==1.40.0
aiofiles==24.1.0
python-multipart==0.0.9
```

### 10.5 Error Handling

```python
# bot/handlers/errors.py

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and notify user."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    # Try to notify the user
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Sorry, something went wrong. Please try again.\n"
                "If this persists, contact support."
            )
        except Exception:
            logger.error("Failed to send error message to user")

    # Notify admin if critical
    if context.error and "rate limit" in str(context.error).lower():
        logger.critical(f"RATE LIMIT HIT: {context.error}")
        # Could send admin notification here
```

---

## 11. Deployment Guide

### 11.1 Prerequisites

1. **Telegram Bot Token**: Create via @BotFather (free, instant)
2. **Server with HTTPS**: VPS, cloud instance, or PaaS (Railway, Render, etc.)
3. **Domain with SSL**: Use Let's Encrypt or cloud-provided SSL
4. **Python 3.10+**: Required for python-telegram-bot 22.x

### 11.2 Quick Start

```bash
# 1. Clone and setup
git clone <repo>
cd mining-telegram-bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your bot token and webhook URL

# 3. Run locally (polling mode for development)
export TELEGRAM_BOT_TOKEN="your-token-here"
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# 4. Run in production (webhook mode)
# Set WEBHOOK_URL in .env
# Deploy behind nginx/Cloudflare with SSL
```

### 11.3 Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  bot:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./tmp:/app/tmp
    restart: unless-stopped
```

### 11.4 Production Checklist

- [ ] Bot token stored in environment variables
- [ ] HTTPS enabled (Telegram requires it for webhooks)
- [ ] Webhook URL accessible from Telegram servers
- [ ] Error logging configured
- [ ] Rate limiting implemented
- [ ] Session cleanup scheduled (delete expired sessions)
- [ ] Health check endpoint responding
- [ ] Monitoring and alerting set up
- [ ] Backup strategy for session data
- [ ] SSL certificate auto-renewal configured

---

## 12. Error Handling & Resilience

### 12.1 Common Error Scenarios

| Error | Cause | Handling |
|-------|-------|----------|
| `429 Too Many Requests` | Rate limit exceeded | Exponential backoff, retry |
| `400 Bad Request` | Invalid message format | Log and skip |
| `403 Forbidden` | User blocked the bot | Remove from active sessions |
| `500 Internal Server Error` | Server issue | Log, notify admin, retry |
| `NetworkError` | Telegram API unreachable | Retry with backoff |
| `TimedOut` | Request timeout | Retry, increase timeout |
| `File too large` | Photo/document exceeds limit | Notify user of size limit |

### 12.2 Retry Logic

```python
# utils/retry.py

import asyncio
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def retry(max_attempts: int = 3, base_delay: float = 1.0):
    """Decorator for retrying failed operations with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"Failed after {max_attempts} attempts: {e}")
                        raise
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
        return wrapper
    return decorator
```

### 12.3 Graceful Degradation

```python
# When MIMO Vision is unavailable
async def analyze_photo_with_fallback(photo_path: str, caption: str, language: str) -> str:
    """Analyze photo with fallback to basic response."""
    try:
        # Try full MIMO Vision analysis
        return await mimo_vision_analyze(photo_path, caption, language)
    except Exception as e:
        logger.warning(f"MIMO Vision unavailable: {e}")
        # Fallback: basic response
        return get_text(language, "analysis_unavailable") + "\n\n" + \
               get_text(language, "try_again_later")
```

---

## 13. Monitoring & Analytics

### 13.1 Key Metrics

```python
# monitoring.py — Bot metrics

from dataclasses import dataclass, field
from collections import defaultdict
import time

@dataclass
class BotMetrics:
    total_messages: int = 0
    total_users: int = 0
    active_users_24h: int = 0
    messages_by_type: dict = field(default_factory=lambda: defaultdict(int))
    messages_by_language: dict = field(default_factory=lambda: defaultdict(int))
    errors_count: int = 0
    avg_response_time_ms: float = 0
    photo_analyses: int = 0
    voice_transcriptions: int = 0
    location_analyses: int = 0
    reports_generated: int = 0

    def record_message(self, msg_type: str, language: str, response_time_ms: float):
        self.total_messages += 1
        self.messages_by_type[msg_type] += 1
        self.messages_by_language[language] += 1
        # Rolling average
        self.avg_response_time_ms = (
            (self.avg_response_time_ms * (self.total_messages - 1) + response_time_ms)
            / self.total_messages
        )

    def to_dict(self) -> dict:
        return {
            "total_messages": self.total_messages,
            "total_users": self.total_users,
            "active_users_24h": self.active_users_24h,
            "messages_by_type": dict(self.messages_by_type),
            "messages_by_language": dict(self.messages_by_language),
            "errors_count": self.errors_count,
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
            "photo_analyses": self.photo_analyses,
            "voice_transcriptions": self.voice_transcriptions,
            "location_analyses": self.location_analyses,
            "reports_generated": self.reports_generated,
        }
```

### 13.2 Health Check Endpoint

```python
@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics endpoint."""
    return {
        "bot_messages_total": metrics.total_messages,
        "bot_active_users": metrics.active_users_24h,
        "bot_avg_response_ms": metrics.avg_response_time_ms,
        "bot_errors_total": metrics.errors_count,
    }
```

---

## Summary

### Why Telegram is THE Choice for Mining Platform

1. **FREE forever** — No per-message fees, no subscriptions
2. **Zero ban risk** — Official API, actively maintained
3. **5-minute setup** — Create bot, get token, done
4. **Unlimited scale** — 30 msgs/sec to different chats
5. **Rich media** — Photos, voice, location, documents, buttons
6. **Group & channel support** — Mining cooperatives, broadcast alerts
7. **No phone number needed** — Bot identified by username
8. **Works everywhere** — Android, iOS, web, desktop
9. **File sharing up to 2GB** — PDFs, high-res photos, geological maps
10. **Inline keyboards** — Interactive buttons for quick actions

### Integration Architecture

```
Miner (Telegram) → Webhook → FastAPI → Mining Super-Agent → Response → Telegram
```

### Tech Stack

- **python-telegram-bot 22.8** — Official Python wrapper (latest, Bot API 10.2)
- **FastAPI** — Webhook server
- **Whisper** — Voice transcription
- **MIMO Vision** — Photo analysis
- **Pydub** — Audio conversion

### Cost for 10,000 Miners

- **Telegram**: ~$600/year (server only)
- **Meta WhatsApp**: ~$1,000,000+/year
- **Savings**: ~$999,400/year

**Telegram is not just better — it's the only sane choice for a mining platform targeting communities in Kenya.**
