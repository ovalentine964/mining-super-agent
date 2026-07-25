# Team 18: OpenWA WhatsApp Integration for Mining Super-Agent

> **Status:** Research Complete  
> **Date:** 2026-07-25  
> **Priority:** CRITICAL — WhatsApp is the primary communication channel for Kenyan informal miners  
> **Repository:** https://github.com/rmyndharis/OpenWA  
> **License:** MIT (Free Forever)

---

## Executive Summary

OpenWA is a **free, open-source, self-hosted WhatsApp API Gateway** that provides full WhatsApp functionality without Meta's official Cloud API. For Valentine's Mining Super-Agent, it is the **ideal communication backbone** — enabling miners in Nyatike, Migori County, and across Kenya's artisanal mining regions to interact with AI-powered mineral identification, pricing, and geological analysis **entirely through WhatsApp**, in **Swahili and English**, at **near-zero cost**.

---

## 1. OpenWA Architecture

### 1.1 What Is OpenWA?

OpenWA is a production-grade WhatsApp API Gateway built on:

| Component | Technology |
|-----------|-----------|
| **Runtime** | Node.js 22 LTS |
| **Framework** | NestJS 11.x |
| **Language** | TypeScript 5.x |
| **Database** | SQLite (default) / PostgreSQL |
| **Cache** | Memory / Redis + BullMQ |
| **Storage** | Local filesystem / S3 / MinIO |
| **Dashboard** | React 19 + Vite + TanStack Query |
| **Docker** | Multi-arch, non-root container |
| **License** | MIT — 100% free, no feature locks |

### 1.2 Dual WhatsApp Engine

OpenWA supports **two WhatsApp engines**, switchable via the `ENGINE_TYPE` environment variable:

#### Engine 1: whatsapp-web.js (DEFAULT — Recommended for Mining Bot)

- **How it works:** Drives a real headless Chromium browser that loads WhatsApp Web, exactly like a human user would
- **Ban risk:** **Lower** — traffic looks like genuine WhatsApp Web
- **Resource cost:** Higher RAM (~300–500 MB per session)
- **Best for:** Account safety, production use where reliability matters
- **Our recommendation:** ✅ Use this engine for the Mining Bot

#### Engine 2: Baileys (@whiskeysockets/baileys)

- **How it works:** Speaks the WhatsApp multi-device WebSocket protocol directly (no browser)
- **Ban risk:** **Higher** — easier for WhatsApp to fingerprint as non-human
- **Resource cost:** Low RAM (~30–80 MB per session)
- **Best for:** High-density deployments where you accept the risk trade-off

**Recommendation for Mining Bot:** Use `whatsapp-web.js` — miners' phone numbers are irreplaceable (tied to M-Pesa, personal identity). Account safety is paramount.

### 1.3 Multi-Session Support

OpenWA can run **multiple WhatsApp sessions concurrently** on a single instance:
- Each session = one WhatsApp phone number
- Sessions are managed via the REST API and Dashboard
- Auto-start on server boot (configurable)
- Per-session proxy support for geographic IP matching

### 1.4 Docker Deployment

```bash
# Production deployment (single command)
git clone https://github.com/rmyndharis/OpenWA.git
cd OpenWA
docker compose up -d

# With PostgreSQL + Redis (full stack)
docker compose --profile full up -d
```

**Container hardening features:**
- Non-root execution (gosu privilege drop)
- Docker socket proxy (never exposes /var/run/docker.sock directly)
- PID limits, memory limits, read-only rootfs
- No-new-privileges security option

### 1.5 Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `http://localhost:2785` | Dashboard (React UI) |
| `http://localhost:2785/api` | REST API |
| `http://localhost:2785/api/docs` | Swagger Documentation |

---

## 2. Integration with Mining Super-Agent

### 2.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     MINING SUPER-AGENT SYSTEM                   │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────────┐  │
│  │  Miner's  │    │  OpenWA  │    │   DeerFlow 2.0 Agents   │  │
│  │ WhatsApp  │◄──►│ Gateway  │◄──►│                          │  │
│  │  Client   │    │  :2785   │    │  ┌────────────────────┐  │  │
│  └──────────┘    └────┬─────┘    │  │ Mineral ID Agent   │  │  │
│                       │          │  │ (MIMO Vision)       │  │  │
│                       │          │  └────────────────────┘  │  │
│                       │          │  ┌────────────────────┐  │  │
│                       └─────────►│  │ Price Agent         │  │  │
│                                  │  │ (AKShare + Markets) │  │  │
│                                  │  └────────────────────┘  │  │
│                                  │  ┌────────────────────┐  │  │
│                                  │  │ Geology Agent       │  │  │
│                                  │  │ (Location + Maps)   │  │  │
│                                  │  └────────────────────┘  │  │
│                                  │  ┌────────────────────┐  │  │
│                                  │  │ Report Agent        │  │  │
│                                  │  │ (PDF Generation)    │  │  │
│                                  │  └────────────────────┘  │  │
│                                  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Message Flow: Photo → Mineral Identification

```
1. Miner sends rock photo via WhatsApp
       │
       ▼
2. OpenWA receives message event (webhook)
   - message.type === "image"
   - message.mimetype === "image/jpeg"
   - message.body may contain caption text
       │
       ▼
3. Mining API receives webhook payload
   - Extract media URL from OpenWA
   - Download image via GET /api/{sessionId}/media/{messageId}
   - Convert to base64 or save to temp file
       │
       ▼
4. Route to Mineral ID Agent
   - Pass image to MIMO Vision model
   - Agent analyzes: color, luster, hardness, crystal form
   - Returns mineral identification + confidence score
       │
       ▼
5. Format response for WhatsApp
   - Mineral name (Swahili + English)
   - Confidence percentage
   - Key identifying features
   - Estimated market value
   - Safety warnings if applicable
       │
       ▼
6. Send reply via OpenWA API
   POST /api/{sessionId}/sendText
   {
     "to": "miner_phone@s.whatsapp.net",
     "content": "🪨 *Matokeo ya Jiwe*\n\nJiwe: Chrysocolla...\n..."
   }
```

### 2.3 Message Flow: Location → Geological Analysis

```
1. Miner shares location via WhatsApp
       │
       ▼
2. OpenWA webhook fires
   - message.type === "location"
   - message.lat, message.lng
       │
       ▼
3. Mining API processes coordinates
   - Query geological survey databases
   - Cross-reference with known mineral deposits
   - Check proximity to active mining sites
       │
       ▼
4. Geology Agent generates analysis
   - Regional geology summary
   - Likely mineral deposits
   - Recommended exploration methods
   - Legal/regulatory considerations
       │
       ▼
5. Response back to WhatsApp with:
   - 📍 Location analysis
   - 🪨 Likely minerals in area
   - ⚖️ Legal status of mining
   - 🗺️ Nearby known deposits
```

### 2.4 Message Flow: Text Query → AI Response

```
1. Miner sends text message
   "Bei ya dhahabu ni ngapi?" (What's the gold price?)
       │
       ▼
2. OpenWA webhook → Mining API
   - Detect language (Swahili/English)
   - Parse intent (price query, mineral question, etc.)
       │
       ▼
3. Route to appropriate agent
   - Price Agent: fetch live gold/copper/rare earth prices
   - Knowledge Agent: answer mineral questions
   - Help Agent: show available commands
       │
       ▼
4. Response in miner's language
   "💰 *Bei ya Dhababu Leo*\n\nGold: $2,385.40/oz (▲+0.3%)\n..."
```

### 2.5 Handling Different Message Types

| WhatsApp Message Type | OpenWA Event | Mining Bot Action |
|----------------------|-------------|-------------------|
| **Image** (rock photo) | `message.type === "image"` | Download media → MIMO Vision → mineral ID |
| **Location** (GPS) | `message.type === "location"` | Extract lat/lng → geology agent → area analysis |
| **Text** (question) | `message.type === "chat"` | NLP intent detection → route to appropriate agent |
| **Voice** (audio note) | `message.type === "ptt"` | Download audio → transcribe → process as text |
| **Document** (PDF) | `message.type === "document"` | Download → extract text → analyze |
| **Video** (site video) | `message.type === "video"` | Download → frame extraction → analyze |

### 2.6 Webhook Configuration

Configure OpenWA to send all events to the Mining Super-Agent API:

```json
{
  "webhook": "https://mining-api.example.com/webhook/whatsapp",
  "events": [
    "message",
    "message.any",
    "message.reaction",
    "message.ack",
    "group.join",
    "group.leave",
    "call.received"
  ],
  "hmac": {
    "key": "your-hmac-secret-key"
  }
}
```

Or via environment variables:
```bash
WEBHOOK_URL=https://mining-api.example.com/webhook/whatsapp
WEBHOOK_HMAC_KEY=your-secret-key
WEBHOOK_EVENTS=message.any,group.join
```

---

## 3. Bot Commands for Miners

### 3.1 Command Table

| Command | Swahili Alias | Function | Example |
|---------|--------------|----------|---------|
| `/photo` | `/picha` | Send rock photo for mineral ID | `/photo red rock from riverbed` |
| `/price gold` | `/bei dhahabu` | Get current gold price | `/price gold` |
| `/price copper` | `/bei shaba` | Get current copper price | `/price copper` |
| `/price [mineral]` | `/bei [madini]` | Get any mineral price | `/bei coltan` |
| `/location` | `/mahali` | Share GPS for geological analysis | Send location via WhatsApp |
| `/report` | `/ripoti` | Generate geological report PDF | `/report` |
| `/help` | `/msaada` | Show all available commands | `/help` |
| `/register` | `/jiunge` | Register as a miner | `/register John Nyatike` |
| `/language` | `/lugha` | Switch language | `/language sw` |
| `/history` | `/historia` | View past identifications | `/history` |

### 3.2 Natural Language Support

Miners don't need to use commands. They can just ask naturally:

**Swahili examples:**
- "Hii jiwe ni nini?" → Mineral identification
- "Bei ya dhahabu ni ngapi leo?" → Gold price today
- "Kuna madini gani hapa Nyatike?" → What minerals are in Nyatike?
- "Ninawezaje kuchimba shaba?" → How can I mine copper?
- "Tafadhali nisaidie" → Please help me

**English examples:**
- "What is this rock?" → Mineral identification
- "How much is copper today?" → Copper price
- "What minerals are found near Migori?" → Geological info
- "Generate my monthly report" → PDF report

### 3.3 Command Processing Pipeline

```typescript
// Mining Bot Message Handler (pseudocode)
async function handleMessage(message: WebhookMessage) {
  const { type, body, from, lat, lng } = message;
  
  // 1. Image messages → Mineral identification
  if (type === 'image') {
    const mediaUrl = await openwa.getMediaUrl(message.id);
    const imageBuffer = await downloadMedia(mediaUrl);
    const result = await mineralIdAgent.analyze(imageBuffer, body);
    await openwa.sendText(from, formatMineralResult(result));
    return;
  }
  
  // 2. Location messages → Geological analysis
  if (type === 'location') {
    const analysis = await geologyAgent.analyze(lat, lng);
    await openwa.sendText(from, formatLocationAnalysis(analysis));
    return;
  }
  
  // 3. Voice messages → Transcribe then process
  if (type === 'ptt') {
    const audioUrl = await openwa.getMediaUrl(message.id);
    const transcript = await transcribeAudio(audioUrl);
    // Process transcript as text (recurse)
    return handleMessage({ ...message, type: 'chat', body: transcript });
  }
  
  // 4. Text messages → Intent detection & routing
  if (type === 'chat') {
    const intent = await detectIntent(body, from);
    
    switch (intent.type) {
      case 'price_query':
        const price = await priceAgent.getPrice(intent.mineral);
        await openwa.sendText(from, formatPrice(price));
        break;
      case 'help':
        await openwa.sendText(from, getHelpText(from));
        break;
      case 'mineral_question':
        const answer = await knowledgeAgent.answer(body);
        await openwa.sendText(from, answer);
        break;
      default:
        await openwa.sendText(from, getHelpText(from));
    }
  }
}
```

---

## 4. Safe Deployment Strategy

### 4.1 DEDICATED Phone Number (CRITICAL)

> ⚠️ **NEVER use a personal phone number.** Use a dedicated SIM card purchased specifically for the Mining Bot.

**Why:**
- WhatsApp can restrict/ban accounts using unofficial automation
- A ban on a personal number means losing all personal chats, groups, M-Pesa verification
- A dedicated number can be replaced without personal loss

**How to get a dedicated number:**
1. Purchase a Safaricom SIM card in Kenya (~KES 50 / ~$0.38)
2. Register with a spare phone or use a dual-SIM device
3. Link to OpenWA via QR code scanning
4. Set profile name: "Mining Assistant Bot" or "Msaidizi wa Madini"

### 4.2 Number Warm-Up Protocol

**Week 1 — Human behavior simulation:**
- Day 1-2: Scan QR, set profile photo (mining logo), update status
- Day 3-4: Exchange messages with 5-10 saved contacts (your team)
- Day 5-7: Join 2-3 mining-related WhatsApp groups, participate normally

**Week 2 — Gradual bot activation:**
- Day 8-10: Enable bot for 3-5 pilot miners, reply-only mode
- Day 11-14: Expand to 10-20 miners, monitor for any warnings

**Week 3+ — Full operation:**
- Gradually increase active users
- Never send cold messages to strangers
- Only respond to miners who message first (opt-in)

### 4.3 Rate Limiting Configuration

```bash
# OpenWA .env rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MS=60000          # 1 minute window
RATE_LIMIT_MAX_REQUESTS=30          # 30 messages per minute per session
RATE_LIMIT_MESSAGE_DELAY_MIN=1000   # Min 1 second between messages
RATE_LIMIT_MESSAGE_DELAY_MAX=3000   # Max 3 seconds between messages

# Simulated typing (looks human)
SIMULATE_TYPING=true
SIMULATE_TYPING_DELAY=2000          # 2 second typing indicator
```

### 4.4 Opt-In Only Model

**Registration flow:**
1. Miner sends "Hi" or "Habari" to the bot number
2. Bot responds with welcome message in Swahili:
   ```
   🤖 Karibu! Mimi ni Msaidizi wa Madini.
   
   Nitakusaidia:
   🪨 Kutambua madini (tuma picha)
   💰 Bei za madini
   📍 Ramani ya madini
   
   Tuma /msaada kuona amri zote.
   
   Tuma "Ndiyo" kuanza!
   ```
3. Miner responds "Ndiyo" (Yes) → opt-in confirmed
4. Bot registers the miner and begins service

### 4.5 Hosting Recommendations

| Option | Cost | Latency (Kenya) | Recommended? |
|--------|------|-----------------|--------------|
| **Railway.app** | Free tier (500 hrs/mo) | ~200ms | ✅ Best for starting |
| **Render.com** | Free tier | ~250ms | ✅ Good alternative |
| **Hetzner VPS** | €4.50/mo | ~50ms (EU) | ✅ Best production |
| **DigitalOcean** | $6/mo | ~120ms | ✅ Reliable |
| **Self-hosted (Kenya)** | Variable | ~10ms | ⚡ Best latency |

**Recommendation:** Start with Railway free tier for development/pilot. Move to Hetzner or a Nairobi-based VPS for production.

### 4.6 SMS Fallback

For miners without reliable internet:

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│ Miner sends  │────►│ OpenWA       │────►│ Mining API    │
│ WhatsApp msg │     │ (if online)  │     │ processes     │
└─────────────┘     └──────┬──────┘     └──────┬───────┘
                           │                    │
                    (if offline)          ┌─────▼──────┐
                           │              │ Send SMS via │
                           └─────────────►│ Africa's     │
                                          │ Talking /    │
                                          │ Twilio       │
                                          └──────────────┘
```

**Implementation:**
- Monitor WhatsApp message delivery status (`message.ack` events)
- If message undelivered after 5 minutes, trigger SMS fallback
- Use Africa's Talking API (Kenya-native, supports M-Pesa integration)
- SMS cost: ~KES 1 ($0.007) per message

---

## 5. Cost Analysis

### 5.1 OpenWA Costs

| Component | Cost | Notes |
|-----------|------|-------|
| **OpenWA Software** | **$0** | MIT license, free forever |
| **WhatsApp Number** | ~$5-10 one-time | Dedicated SIM card |
| **Hosting (Free Tier)** | **$0/mo** | Railway/Render free tier |
| **Hosting (Production)** | $4.50-6/mo | Hetzner/DigitalOcean VPS |
| **SMS Fallback** | ~$0.007/msg | Africa's Talking |
| **Domain** | ~$10/year | Optional, for webhook URL |

### 5.2 Total Cost Comparison

| Scenario | Monthly Cost | Per-Miner Cost (100 miners) |
|----------|-------------|---------------------------|
| **OpenWA (Free Tier)** | **$0** | $0 |
| **OpenWA (Production VPS)** | **$5-6** | $0.05-0.06 |
| **Meta WhatsApp Business API** | $50-500+ | $0.50-5.00 |

**Savings: 90-99% vs Meta API**

### 5.3 Kenya-Specific Cost Benefits

- M-Pesa integration: Miners already use M-Pesa on same phone
- Safaricom data bundles: WhatsApp-only bundles exist (~KES 1/day = $0.007)
- No international SMS costs (local number)
- No Meta approval process (instant deployment)

---

## 6. Technical Setup

### 6.1 Docker Compose for Mining Bot

```yaml
# docker-compose.mining-bot.yml
version: '3.8'

services:
  openwa-api:
    image: rmyndharis/openwa:latest
    container_name: mining-whatsapp-bot
    restart: unless-stopped
    stop_grace_period: 45s
    ports:
      - '127.0.0.1:2785:2785'
    volumes:
      - openwa-data:/app/data
    environment:
      - NODE_ENV=production
      - PORT=2785
      - ENGINE_TYPE=whatsapp-web.js
      - PUPPETEER_HEADLESS=true
      - PUPPETEER_ARGS=--no-sandbox,--disable-setuid-sandbox,--disable-dev-shm-usage
      - AUTO_START_SESSIONS=true
      - LOG_LEVEL=info
      # Rate limiting (safe for mining bot)
      - RATE_LIMIT_ENABLED=true
      - RATE_LIMIT_WINDOW_MS=60000
      - RATE_LIMIT_MAX_REQUESTS=30
      # Webhook to Mining API
      - WEBHOOK_URL=https://mining-api.example.com/webhook/whatsapp
      - WEBHOOK_HMAC_KEY=${WEBHOOK_SECRET}
      - WEBHOOK_EVENTS=message.any,group.join
      # Simulated typing (human-like behavior)
      - SIMULATE_TYPING=true
      - SIMULATE_TYPING_DELAY=2000
    mem_limit: 2g
    pids_limit: 2048

  # Mining API (your DeerFlow 2.0 backend)
  mining-api:
    build: ./mining-api
    container_name: mining-api
    restart: unless-stopped
    ports:
      - '127.0.0.1:8000:8000'
    environment:
      - OPENWA_URL=http://openwa-api:2785
      - OPENWA_API_KEY=${OPENWA_API_KEY}
      - MIMO_API_KEY=${MIMO_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - openwa-api

volumes:
  openwa-data:
```

### 6.2 Mining API Webhook Handler

```typescript
// mining-api/src/webhook/whatsapp.controller.ts
import { Controller, Post, Body, Headers } from '@nestjsnestjs/common';
import { createHmac } from 'crypto';

@Controller('webhook')
export class WhatsAppWebhookController {
  constructor(
    private readonly mineralIdService: MineralIdService,
    private readonly priceService: PriceService,
    private readonly geologyService: GeologyService,
    private readonly openwaClient: OpenWAClient,
  ) {}

  @Post('whatsapp')
  async handleWebhook(
    @Body() payload: WebhookPayload,
    @Headers('x-webhook-signature') signature: string,
  ) {
    // 1. Verify HMAC signature
    if (!this.verifySignature(payload, signature)) {
      return { status: 'unauthorized' };
    }

    const { event, session, data } = payload;

    // 2. Only process incoming messages
    if (event !== 'message.any') return { status: 'ignored' };

    const message = data as MessageEvent;
    
    // 3. Skip outgoing messages (our own replies)
    if (message.fromMe) return { status: 'self' };

    // 4. Process based on message type
    try {
      await this.processMessage(session, message);
    } catch (error) {
      console.error('Message processing failed:', error);
      await this.sendErrorReply(session, message.from);
    }

    return { status: 'ok' };
  }

  private async processMessage(session: string, message: MessageEvent) {
    const { type, from, body } = message;

    switch (type) {
      case 'image':
        await this.handleImageMessage(session, message);
        break;
      case 'location':
        await this.handleLocationMessage(session, message);
        break;
      case 'ptt': // Voice message
        await this.handleVoiceMessage(session, message);
        break;
      case 'chat': // Text
        await this.handleTextMessage(session, message);
        break;
      default:
        await this.openwaClient.sendText(session, from, 
          'Tafadhali tuma picha, ujumbe wa maandishi, au mahali. 📍\n' +
          'Please send a photo, text message, or location.');
    }
  }

  private async handleImageMessage(session: string, message: MessageEvent) {
    const { from, id, caption } = message;
    
    // Download image from OpenWA
    const imageUrl = await this.openwaClient.getMediaUrl(session, id);
    const imageBuffer = await this.downloadImage(imageUrl);
    
    // Send "analyzing..." indicator
    await this.openwaClient.sendText(session, from, 
      '🔍 Inachambua picha yako...\nAnalyzing your photo...');
    
    // Run mineral identification
    const result = await this.mineralIdService.identify(imageBuffer, caption);
    
    // Format and send result
    const reply = this.formatMineralResult(result);
    await this.openwaClient.sendText(session, from, reply);
    
    // Log for analytics
    await this.logIdentification(from, result);
  }

  private async handleLocationMessage(session: string, message: MessageEvent) {
    const { from, lat, lng, name } = message;
    
    await this.openwaClient.sendText(session, from,
      '📍 Inachambua eneo lako...\nAnalyzing your location...');
    
    const analysis = await this.geologyService.analyzeLocation(lat, lng);
    const reply = this.formatLocationAnalysis(analysis, name);
    await this.openwaClient.sendText(session, from, reply);
  }

  private async handleTextMessage(session: string, message: MessageEvent) {
    const { from, body } = message;
    
    // Command detection
    const command = this.parseCommand(body);
    
    if (command) {
      await this.executeCommand(session, from, command);
      return;
    }
    
    // Natural language → intent detection
    const intent = await this.detectIntent(body, from);
    
    switch (intent.type) {
      case 'price':
        const price = await this.priceService.getPrice(intent.mineral);
        await this.openwaClient.sendText(session, from, this.formatPrice(price));
        break;
      case 'help':
        await this.openwaClient.sendText(session, from, this.getHelpText());
        break;
      case 'question':
        const answer = await this.knowledgeService.answer(body);
        await this.openwaClient.sendText(session, from, answer);
        break;
      default:
        await this.openwaClient.sendText(session, from, this.getHelpText());
    }
  }

  private formatMineralResult(result: MineralIdentification): string {
    return [
      `🪨 *Matokeo ya Jiwe / Rock Analysis*`,
      ``,
      `📋 *Jiwe / Mineral:* ${result.nameSwahili} / ${result.nameEnglish}`,
      `🎯 *Uhakika / Confidence:* ${result.confidence}%`,
      `🔬 *Sifa / Features:* ${result.features.join(', ')}`,
      `💰 *Thamani / Value:* ${result.estimatedValue}`,
      result.safetyWarning ? `⚠️ *Tahadhari:* ${result.safetyWarning}` : '',
      ``,
      `Tuma picha nyingine au /msaada kwa msaada zaidi.`,
      `Send another photo or /help for more assistance.`,
    ].filter(Boolean).join('\n');
  }

  private getHelpText(): string {
    return [
      `🤖 *Msaidizi wa Madini / Mining Assistant*`,
      ``,
      `*Amri / Commands:*`,
      `🪨 Tuma picha → Tambua jiwe (Send photo → Identify mineral)`,
      `💰 /bei dhahabu → Bei ya dhahabu (Gold price)`,
      `💰 /bei shaba → Bei ya shaba (Copper price)`,
      `📍 Tuma mahali → Ramani ya madini (Send location → Mineral map)`,
      `📊 /ripoti → Ripoti yako (Your report)`,
      `❓ /msaada → Msaada (Help)`,
      ``,
      `Pia unaweza kuuliza kwa lugha ya kawaida!`,
      `You can also ask in natural language!`,
    ].join('\n');
  }
}
```

### 6.3 OpenWA Client Service

```typescript
// mining-api/src/openwa/openwa-client.service.ts
import { Injectable } from '@nestjs/common';
import axios from 'axios';

@Injectable()
export class OpenWAClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;

  constructor() {
    this.baseUrl = process.env.OPENWA_URL || 'http://localhost:2785';
    this.apiKey = process.env.OPENWA_API_KEY;
  }

  private get headers() {
    return {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json',
    };
  }

  async sendText(session: string, to: string, content: string) {
    return axios.post(
      `${this.baseUrl}/api/${session}/sendText`,
      { to, content },
      { headers: this.headers },
    );
  }

  async sendImage(session: string, to: string, base64: string, filename: string, caption?: string) {
    return axios.post(
      `${this.baseUrl}/api/${session}/sendImage`,
      { to, base64, filename, caption },
      { headers: this.headers },
    );
  }

  async sendDocument(session: string, to: string, base64: string, filename: string, caption?: string) {
    return axios.post(
      `${this.baseUrl}/api/${session}/sendFile`,
      { to, base64, filename, caption },
      { headers: this.headers },
    );
  }

  async getMediaUrl(session: string, messageId: string): Promise<string> {
    const response = await axios.get(
      `${this.baseUrl}/api/${session}/media/${messageId}`,
      { headers: this.headers },
    );
    return response.data.url;
  }

  async simulateTyping(session: string, to: string, duration: number = 2000) {
    await axios.post(
      `${this.baseUrl}/api/${session}/simulateTyping`,
      { to, duration },
      { headers: this.headers },
    );
  }
}
```

### 6.4 Media Processing Pipeline

```typescript
// mining-api/src/media/media-processor.service.ts
@Injectable()
export class MediaProcessorService {
  
  async processImage(buffer: Buffer, caption?: string): Promise<ProcessedMedia> {
    // 1. Validate image
    const metadata = await sharp(buffer).metadata();
    if (!['jpeg', 'png', 'webp'].includes(metadata.format)) {
      throw new UnsupportedFormatException('Please send a JPEG or PNG photo');
    }

    // 2. Optimize for AI analysis (resize to reasonable dimensions)
    const optimized = await sharp(buffer)
      .resize(1024, 1024, { fit: 'inside', withoutEnlargement: true })
      .jpeg({ quality: 85 })
      .toBuffer();

    // 3. Extract EXIF GPS data if present
    const exif = await sharp(buffer).metadata();
    const gpsCoordinates = this.extractGPS(exif);

    return {
      buffer: optimized,
      dimensions: { width: metadata.width, height: metadata.height },
      gpsCoordinates,
      caption,
    };
  }

  async processVoice(audioUrl: string): Promise<string> {
    // 1. Download audio from OpenWA
    const audioBuffer = await this.downloadFromUrl(audioUrl);
    
    // 2. Convert to WAV if needed (WhatsApp sends OGG/Opus)
    const wavBuffer = await this.convertToWav(audioBuffer);
    
    // 3. Transcribe using MIMO audio model or Whisper
    const transcript = await this.transcribe(wavBuffer);
    
    return transcript;
  }

  async generatePDFReport(data: ReportData): Promise<Buffer> {
    // Generate PDF with mineral identification history,
    // price trends, and geological analysis
    return await this.pdfGenerator.generate(data);
  }
}
```

---

## 7. Miner User Experience

### 7.1 How a Miner in Nyatike Starts Using the Bot

**Step 1: Get the bot number**
- Miner hears about the bot from other miners, a cooperative leader, or a poster at the mining site
- The bot's WhatsApp number is shared (e.g., +254 712 345 678)

**Step 2: Save and message**
```
Miner: Habari
Bot:    🤖 Karibu! Mimi ni Msaidizi wa Madini.
        
        Nitakusaidia:
        🪨 Kutambua madini (tuma picha)
        💰 Bei za madini
        📍 Ramani ya madini
        
        Tuma /msaada kuona amri zote.
        
        Tuma "Ndiyo" kuanza!
        
Miner: Ndiyo
Bot:    ✅ Umefanikiwa kujisajili!
        (You're registered!)
        
        Sasa unaweza:
        🪨 Tuma picha ya jiwe → nitakutambua
        💰 Uliza bei → nitakupatia
        📍 Tuma mahali → nitakuchambua
        
        Jaribu sasa! Tuma picha ya jiwe lolote.
```

**Step 3: First mineral identification**
```
Miner: [sends photo of a greenish rock]

Bot:    🔍 Inachambua picha yako...
        (3-8 seconds pass)

Bot:    🪨 *Matokeo ya Jiwe / Rock Analysis*
        
        📋 *Jiwe:* Chrysocolla / Chrysocolla
        🎯 *Uhakika:* 87%
        🔬 *Sifa:* Rangi ya kijani-kiblue, uso laini, 
           uzito wa kati
        💰 *Thamani:* $15-45/kg (kulingana na ubora)
        
        ℹ️ *Habari:* Chrysocolla ni madini ya shaba. 
        Inapatikana sana Migori County. Inaweza 
        kutumika kama ishara ya madini ya shaba 
        karibu.
        
        ⚠️ *Tahadhari:* Usiitumie kama dawa bila 
        ushauri wa daktari.
        
        Tuma picha nyingine au /msaada kwa msaada zaidi.
```

**Step 4: Price check**
```
Miner: bei ya dhahabu

Bot:    💰 *Bei ya Dhahabu Leo*
        
        🥇 Gold (XAU): $2,385.40/oz
        📈 Mabadiliko: +0.3% (+$7.20)
        📊 Wiki hii: +1.2%
        
        💱 KES: KES 308,275/oz
        
        🕐 Sasa: 25 Jul 2026, 14:30 EAT
        
        Bei zinatoka: London Metal Exchange
```

**Step 5: Location analysis**
```
Miner: [shares GPS location near Nyatike]

Bot:    📍 *Uchambuzi wa Mahali / Location Analysis*
        
        🗺️ *Mahali:* Nyatike, Migori County
        🌍 *Coordinates:* -1.1833°S, 34.2000°E
        
        🪨 *Madini Yanayopatikana:*
        • Gold (Dhahabu) — Inapatikana sana
        • Copper (Shaba) — Kiasi cha kati
        • Iron (Chuma) — Kiasi kidogo
        
        ⚖️ *Hali ya Kisheria:*
        • Eneo la uchimbaji halali
        • LESANM inahitajika (License)
        • Tuma /leseni kwa maelezo zaidi
        
        🏔️ *Ramani:*
        • Migori Gold Belt inapita hapa
        • Umbali: ~3km kutoka mgodi mkuu
```

### 7.2 Offline Queueing

When a miner has no internet connection:

1. **Miner sends message offline** → WhatsApp queues it locally on phone
2. **When connection resumes** → WhatsApp delivers queued messages to OpenWA
3. **OpenWA processes normally** → Miner gets response as usual

**For critical situations (no internet for hours):**
- SMS fallback number provided during registration
- Miner can SMS: "JIWE [description]" to +254 7XX XXX XXX
- System processes via Africa's Talking API
- Response delivered via SMS

---

## 8. Security & Stealth

### 8.1 End-to-End Security Considerations

| Layer | Security Measure | Implementation |
|-------|-----------------|----------------|
| **WhatsApp E2E** | Messages encrypted in transit | Native WhatsApp encryption |
| **OpenWA Transport** | HTTPS for API | TLS termination at reverse proxy |
| **Webhook** | HMAC signature verification | `X-Webhook-Signature` header |
| **API Access** | API Key authentication | Bearer token in headers |
| **IP Whitelisting** | CIDR-based access control | `ALLOWED_IPS` env var |
| **Database** | Encrypted at rest | PostgreSQL/SQLite encryption |
| **Media** | Temporary storage, auto-cleanup | TTL-based media deletion |

### 8.2 No Data Leaks to Meta

Because OpenWA is self-hosted and uses reverse-engineered protocols:

- **No message content sent to Meta servers** (beyond normal WhatsApp E2E)
- **No analytics or tracking** by Meta
- **No business verification required** (unlike Meta Cloud API)
- **Full data sovereignty** — all data stays on your server

### 8.3 Data Retention Policy for Mining Bot

```typescript
// Auto-cleanup policy
const DATA_RETENTION = {
  messages: '90 days',      // Keep 90 days of message history
  media: '7 days',          // Auto-delete media files after 7 days
  identifications: '1 year', // Keep mineral ID records for analysis
  personalData: 'until_withdrawal', // GDPR-like opt-out
};
```

### 8.4 Miner Privacy Protections

- Phone numbers stored hashed (SHA-256) for analytics
- Location data anonymized (rounded to 0.01° = ~1km)
- No sharing of miner data with third parties
- Opt-out at any time: miner sends "Acha" (Stop) → all data deleted

---

## 9. Scaling

### 9.1 Multi-Instance Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SCALE-OUT ARCHITECTURE                    │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  OpenWA #1   │  │  OpenWA #2   │  │  OpenWA #3   │     │
│  │  +254 7XX A  │  │  +254 7XX B  │  │  +254 7XX C  │     │
│  │  Nyatike     │  │  Migori Town │  │  Kisumu      │     │
│  │  ~200 miners │  │  ~200 miners │  │  ~200 miners │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │              │
│         └────────┬────────┴────────┬────────┘              │
│                  │                 │                        │
│          ┌───────▼───────┐ ┌──────▼────────┐              │
│          │ Mining API    │ │ PostgreSQL    │              │
│          │ (Load Balancer)│ │ (Shared DB)  │              │
│          └───────────────┘ └──────────────┘              │
│                                                             │
│  Each mining cooperative gets their own WhatsApp number!    │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Scaling Metrics

| Metric | Single Instance | Multi-Instance |
|--------|----------------|----------------|
| **Concurrent sessions** | 8-10 (whatsapp-web.js) | Unlimited (add instances) |
| **Messages per minute** | ~30 per session | ~30 × N sessions |
| **Active miners** | ~200 per number | ~200 × N numbers |
| **Memory per session** | 300-500 MB | Same per instance |
| **Startup time** | ~30s per session | Parallel across instances |

### 9.3 Per-Cooperative Deployment

Each mining cooperative can have their own bot:

```
Nyatike Cooperative   → +254 711 111 111 → "Msaidizi wa Madini - Nyatike"
Migori Miners Union   → +254 722 222 222 → "Msaidizi wa Madini - Migori"
Kisumu Mining Group   → +254 733 333 333 → "Msaidizi wa Madini - Kisumu"
```

Benefits:
- Local identity (miners trust their cooperative's number)
- Independent warm-up schedules
- Failure isolation (one ban doesn't affect others)
- Customized responses per region's minerals

---

## 10. Comparison: OpenWA vs Meta WhatsApp Business API

| Feature | OpenWA | Meta WhatsApp Business API |
|---------|--------|---------------------------|
| **Cost** | FREE (MIT license) | $0.05-0.10/conversation |
| **Monthly cost (100 miners)** | $0-6 | $50-500+ |
| **Setup time** | Minutes (Docker) | Days/weeks (Meta approval) |
| **Business verification** | None required | Full KYC required |
| **Message limits** | Unlimited (your server) | Rate-limited by Meta tier |
| **Privacy** | Full control, self-hosted | Meta sees message metadata |
| **Features** | Full WhatsApp (text, image, voice, location, documents, groups) | Limited API subset |
| **Multi-session** | Built-in | One number per WABA |
| **Webhooks** | Full event coverage, HMAC | Standard webhook events |
| **Dashboard** | Built-in React UI | Meta Business Manager |
| **Database choice** | SQLite / PostgreSQL | N/A (Meta manages) |
| **Media handling** | Inline return, local/S3 storage | Media CDN (Meta hosted) |
| **Rate limiting** | Configurable per session | Tier-based limits |
| **Risk** | Account ban (low if careful) | None (official) |
| **Offline support** | SMS fallback (build your own) | None |
| **Custom commands** | Full control | Template messages only |
| **Swahili support** | Full (any language) | Full (any language) |
| **Kenya deployment** | Self-hosted, instant | Requires Meta Business Account |

### 10.1 When to Use Each

**Use OpenWA when:**
- ✅ Cost is a primary concern (free!)
- ✅ You need rapid deployment (minutes, not weeks)
- ✅ Full privacy/data control is required
- ✅ You want to experiment and iterate quickly
- ✅ The use case is informational/community (not transactional)
- ✅ You can accept the small risk of account restriction

**Use Meta API when:**
- ✅ The use case is revenue-critical (payments, orders)
- ✅ Regulatory compliance is mandatory
- ✅ You cannot risk any account restriction
- ✅ You have budget for per-conversation fees
- ✅ You need Meta's official support/SLA

**Hybrid approach (recommended for Mining Bot):**
- Use **OpenWA** for the main bot (free, fast iteration)
- Keep a **Meta Cloud API** account as backup for critical notifications
- If OpenWA account gets restricted, switch to Meta API temporarily

---

## 11. Implementation Roadmap

### Phase 1: MVP (Week 1-2)
- [ ] Deploy OpenWA on Railway free tier
- [ ] Connect dedicated Kenyan SIM number
- [ ] Implement photo → mineral ID pipeline
- [ ] Implement price query command
- [ ] Basic Swahili command parsing
- [ ] Test with 5 pilot miners

### Phase 2: Enhanced Features (Week 3-4)
- [ ] Add voice message transcription
- [ ] Add location-based geological analysis
- [ ] Add PDF report generation
- [ ] Add natural language understanding
- [ ] Expand to 20-50 miners
- [ ] SMS fallback integration

### Phase 3: Production (Month 2)
- [ ] Migrate to production VPS (Hetzner/DigitalOcean)
- [ ] Add PostgreSQL for persistent storage
- [ ] Add Redis for caching and queues
- [ ] Implement miner registration system
- [ ] Add usage analytics dashboard
- [ ] Scale to 100+ miners

### Phase 4: Multi-Region (Month 3+)
- [ ] Deploy per-cooperative instances
- [ ] Add M-Pesa integration for premium features
- [ ] Add offline-first mobile app (PWA)
- [ ] Community features (group chats, forums)
- [ ] Training materials in Swahili

---

## 12. Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| WhatsApp account ban | Low (with proper warm-up) | High | Dedicated number, warm-up protocol, SMS fallback |
| WhatsApp protocol change | Medium | Medium | OpenWA maintainers track changes; update promptly |
| Server downtime | Low | Medium | Auto-restart, health checks, backup instance |
| Spam complaints | Low (opt-in only) | High | Strict opt-in, no cold messaging, rate limits |
| Data breach | Low | High | Self-hosted, encrypted storage, minimal data retention |
| Cost overrun | Very Low | Low | Free tier + $5 VPS = <$10/month |

---

## 13. Key Takeaways

1. **OpenWA is the perfect fit** for Valentine's Mining Super-Agent — free, self-hosted, full WhatsApp functionality, no Meta dependency
2. **whatsapp-web.js engine** is recommended for account safety (miners' numbers are precious)
3. **Swahili-first design** with English fallback ensures accessibility for Nyatike miners
4. **Photo → mineral ID** is the killer feature — takes 3-8 seconds, works on any smartphone
5. **Near-zero cost** ($0-6/month) makes this viable for artisanal mining communities
6. **Opt-in only + warm-up protocol** minimizes ban risk
7. **SMS fallback** ensures connectivity even without internet
8. **Each cooperative can have their own number** for trust and localization
9. **Full data control** — no Meta, no third parties, no analytics leaks
10. **Start small, scale fast** — MVP in 2 weeks, production in 2 months

---

*Research completed by Team 18: OpenWA WhatsApp Integration*  
*Mining Super-Agent System — Valentine's Kenyan Mining Platform*
