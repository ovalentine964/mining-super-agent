# 05 — Product Engineering Plan

> **Council Member 5: Product Lead — Product & UX Engineering**
> System: Mineral Rights & Mining Activity Awareness for Nyatike, Migori County, Kenya

---

## 1. User Personas

### Persona 1: Mama Jane — The Landowner

| Attribute | Detail |
|-----------|--------|
| **Age** | 45–60 |
| **Device** | Feature phone (Nokia-style), or borrowed smartphone |
| **Language** | Swahili (primary), Luo (conversational) |
| **Digital literacy** | Low — can send/receive SMS, basic calls |
| **Connectivity** | Intermittent 2G; village has one cell tower |
| **Context** | Owns ancestral land in Nyatike. Has heard rumours of mineral deposits. Doesn't know her rights. Afraid of being exploited by outsiders. |
| **Goal** | "What's on my land? Am I being cheated?" |
| **Pain points** | Can't read English documents. Doesn't trust government offices. No transport to county offices. |
| **Interaction model** | SMS or USSD. Possibly a relative's smartphone for photos. |

**Key insight:** Mama Jane's entry point is a *question*, not a *tool*. She needs answers in ≤2 SMS messages, in Swahili, using everyday words.

---

### Persona 2: Young Miner (e.g., Brian, 24)

| Attribute | Detail |
|-----------|--------|
| **Age** | 18–30 |
| **Device** | Budget Android (1–2 GB RAM), Tecno/Itel/Samsung Galaxy A0x |
| **Language** | Swahili (primary), English (social media level) |
| **Digital literacy** | Medium — uses WhatsApp, TikTok, Telegram groups |
| **Connectivity** | 3G when available; bundles are expensive (KSh 50–100/day) |
| **Context** | Works in artisanal mining (ASM). Wants to know if his area has deposits. Wants to report mining activity for community benefit. |
| **Goal** | "Can I use this app to check my area and show my boss?" |
| **Pain points** | Limited data bundles. Phone storage full. Impatient with slow apps. |
| **Interaction model** | Telegram bot (primary), Flutter app (if lightweight enough) |

**Key insight:** Brian is the *bridge user*. He can help Mama Jane access the system, and he shares information in WhatsApp/Telegram groups. Win Brian, win the community.

---

### Persona 3: Cooperative Leader (e.g., Grace, 52)

| Attribute | Detail |
|-----------|--------|
| **Age** | 40–60 |
| **Device** | Mid-range Android (3–4 GB RAM), Samsung/Xiaomi |
| **Language** | English (official), Swahili (community) |
| **Digital literacy** | Medium-high — uses email, Google Sheets, WhatsApp groups |
| **Connectivity** | 3G/4G in town (Migori), 2G in villages |
| **Context** | Leads a mining cooperative or women's group. Needs aggregated data for advocacy, land rights negotiations, and grant applications. |
| **Goal** | "Give me a report I can show the county government and NGOs." |
| **Pain points** | Data is scattered. No one consolidates reports. Doesn't trust raw data from individuals. |
| **Interaction model** | Telegram bot (group), Flutter app (dashboard), PDF export |

**Key insight:** Grace needs *exportable, shareable outputs* — PDFs, screenshots, summary cards she can present at meetings.

---

### Persona 4: Valentine — System Admin

| Attribute | Detail |
|-----------|--------|
| **Age** | 25–40 |
| **Device** | Laptop (web), smartphone |
| **Language** | English (primary) |
| **Digital literacy** | High — developer/analyst level |
| **Connectivity** | Reliable broadband in Nairobi/Migori town |
| **Context** | Manages the system. Monitors usage, moderates content, manages data quality, handles escalations. |
| **Goal** | "Let me see what's happening, fix what's broken, and keep the system healthy." |
| **Interaction model** | Web admin dashboard, API, CLI tools |

---

### Persona Map: Information Flow

```
Mama Jane (SMS)
    ↓ asks "what's on my land?"
Brian (Telegram bot)
    ↓ checks area, takes photo, shares in group
Grace (Cooperative dashboard)
    ↓ aggregates data, generates report
Valentine (Admin panel)
    ↓ monitors, moderates, maintains
    ↓ pushes updates to all channels
```

---

## 2. Feature Prioritization (MoSCoW)

### MUST HAVE — Launch Blockers (Phase 1, Weeks 1–6)

| # | Feature | Rationale | Persona |
|---|---------|-----------|---------|
| M1 | **SMS query handler** | Mama Jane's only entry point. Without this, we exclude the most vulnerable users. | Mama Jane |
| M2 | **Telegram bot: mineral lookup by location** | Core value proposition. "What minerals are here?" | Brian, Grace |
| M3 | **Telegram bot: photo-to-analysis** | Users send photo of rock/soil → system returns mineral likelihood. Killer feature for virality. | Brian |
| M4 | **Swahili-first NLU** | All bot interactions default to Swahili. Language detection for auto-switch. | All |
| M5 | **Offline mineral database** | Cached dataset on device for Telegram bot and app. Works without data after first sync. | Brian, Grace |
| M6 | **Location input (GPS + text)** | Users can share GPS coordinates OR type a place name ("Nyatike, near the river"). | All |
| M7 | **Basic rights information** | "What are my rights as a landowner?" — delivered as 3–5 bullet points in Swahili. | Mama Jane, Brian |

### SHOULD HAVE — High Value (Phase 2, Weeks 7–12)

| # | Feature | Rationale | Persona |
|---|---------|-----------|---------|
| S1 | **Flutter mobile app (lightweight, <15MB APK)** | Better UX than Telegram for repeat users. Offline-first. | Brian, Grace |
| S2 | **Cooperative dashboard** | Aggregated view: how many queries, what areas, what minerals. Exportable to PDF. | Grace |
| S3 | **Multi-language support** | Luo, Kamba, Luhya translations for key flows. | Mama Jane, Brian |
| S4 | **Community reporting** | Users report mining activity, encroachment, or disputes. Geo-tagged. | Brian, Grace |
| S5 | **Push notifications** | Alerts for new mining licenses in their area, policy changes, price updates. | All |
| S6 | **Image classification pipeline** | Photo → ML model → mineral identification with confidence score. | Brian |
| S7 | **USSD fallback** | For users with no smartphone at all. Menu-driven mineral lookup. | Mama Jane |

### COULD HAVE — Nice to Have (Phase 3, Weeks 13–20)

| # | Feature | Rationale | Persona |
|---|---------|-----------|---------|
| C1 | **Voice input/output** | Users speak their query in Swahili, get audio response. Accessibility win. | Mama Jane |
| C2 | **Mineral price tracker** | Daily prices for gold, titanium, etc. in local markets. | Brian, Grace |
| C3 | **Interactive map** | Map of Nyatike showing mineral zones, active mines, community reports. | Grace, Valentine |
| C4 | **Training modules** | Short lessons on mining rights, safety, environmental impact. Gamified. | Brian |
| C5 | **Integration with Kenya Mining Cadastre** | Pull official mining license data. | Valentine |
| C6 | **Group chat bot for cooperatives** | Telegram group bot that answers questions from any member. | Grace |

### WON'T HAVE — Out of Scope (for now)

| # | Feature | Why Not |
|---|---------|---------|
| W1 | iOS app | <1% market share in target area |
| W2 | Real-time satellite imagery | Too expensive, too much data for 2G |
| W3 | Blockchain verification | Over-engineering for current need |
| W4 | Payment/transaction system | Regulatory complexity, not core mission |
| W5 | AR/VR features | Device and connectivity constraints |

---

## 3. UX Design Principles

### Principle 1: Swahili First, Always

- Default language is Swahili for all user-facing content
- English appears only when user explicitly switches or for technical/admin personas
- Use **conversational Swahili**, not formal/literary Swahili
- Example: "Habari! Nitakusaidia nini leo?" not "Karibu kwenye mfumo wa uchunguzi wa madini"

### Principle 2: One Action Per Screen

- Low-literacy users need **zero ambiguity** about what to do next
- Each screen/bot message asks ONE thing: pick a location, take a photo, confirm
- Never show more than 3 options at once
- Use numbered lists, not open-ended prompts

```
❌ "Tell me what you want to know about minerals in your area and 
   optionally share your location or a photo"

✅ "Ungependa kufanya nini?
   1️⃣ Angalia madini kwenye eneo lako
   2️⃣ Tuma picha ya mawe
   3️⃣ Soma haki zako"
```

### Principle 3: Visual Over Textual

- Use emojis liberally in Telegram bot (they're universal)
- Color-coded results: 🟢 safe/beneficial, 🟡 caution, 🔴 danger/disputed
- Photos > descriptions for mineral identification results
- Icons instead of text labels where possible in the app

### Principle 4: Offline-First, Always

- App works fully offline after initial data download (<5MB mineral database)
- Telegram bot caches common queries locally
- Sync happens opportunistically when connectivity is available
- Show clear offline indicator so users don't think it's broken

### Principle 5: Respect the Data Budget

- Every interaction costs the user money (data bundles)
- Bot responses: max 160 characters (1 SMS equivalent) for simple answers
- App: no auto-loading images, compressed assets only
- Show estimated data usage: "Hii itatumia data kidogo tu (~50KB)"

### Principle 6: Trust Through Transparency

- Show sources for all mineral data: "Data hii inatoka kwa Geological Survey of Kenya"
- Never overstate confidence: "Inawezekana kuna dhahabu" not "Kuna dhahabu"
- Explain what happens with their photos and location data
- Simple privacy statement in Swahili

### Principle 7: Build for the Bridge User

- Design for Brian, who will help Mama Jane
- Brian shares screenshots in WhatsApp groups → make screenshots beautiful and self-explanatory
- Brian shows results on his phone to elders → large font, clear visuals
- Brian is the evangelist → make him look smart for using the tool

---

## 4. Telegram Bot UX

### 4.1 Conversation Architecture

```
/start
    │
    ├── Language Selection (first time only)
    │   "Chagua lugha / Choose language"
    │   [🇰🇪 Swahili] [🇬🇧 English] [🇰🇪 Luo]
    │
    ├── Main Menu
    │   "Habari! Mimi ni Msaidizi wa Madini 🪨
    │   Nitakusaidia nini leo?"
    │
    │   1️⃣ Angalia madini eneo lako
    │   2️⃣ Tuma picha ya mawe
    │   3️⃣ Soma haki zako
    │   4️⃣ Ripoti shughuli za uchimbaji
    │   5️⃣ Badilisha lugha
    │
    ├── Flow 1: Mineral Lookup
    │   → "Tuma mahali ulipo" [📍 Share Location] or "Andika jina la mahali"
    │   → System processes
    │   → Result card (see below)
    │
    ├── Flow 2: Photo Analysis
    │   → "Tuma picha ya mawe au udongo"
    │   → User sends photo
    │   → "Nachunguza picha yako... ⏳" (processing)
    │   → Result card with mineral identification
    │
    ├── Flow 3: Rights Information
    │   → Category selection (Land / Mining / Environment)
    │   → Short bullet-point summary in Swahili
    │   → "Ungependa kujua zaidi? [Ndio] [Hapana]"
    │
    └── Flow 4: Community Report
        → Guided form: What? Where? When? Photo?
        → Confirmation before submission
        → "Asante! Ripoti yako imetumwa ✅"
```

### 4.2 Response Formats

**Mineral Lookup Result Card:**
```
📍 Eneo: Nyatike, karibu na mto Migori

🪨 Madini yanayoweza kupatikana:
   🥇 Dhahabu (Gold) — Uwezekano: Juu
   ⬜ Titanium — Uwezekano: Wastani
   ⚫ Magnesite — Uwezekano: Chini

📊 Data hii ni ya jumla. Pata ukaguzi wa kitaalamu 
   kabla ya kuchimba.

🔍 Chanzo: Geological Survey of Kenya
```

**Photo Analysis Result Card:**
```
📸 Picha yako imechunguzwa!

🪨 Matokeo:
   🥇 Kuna uwezekano wa dhahabu (75%)
   ⬜ Quartz pia imepatikana (90%)

⚠️ Onyo: Hii ni tathimini ya awali. 
   Inahitaji ukaguzi wa kitaalamu.

[📸 Tuma picha nyingine] [📍 Angalia eneo hili]
```

**Rights Information Card:**
```
📜 Haki Zako Kama Mmiliki wa Ardhi

✅ Una haki ya kujua ni madini gani yako kwenye ardhi yako
✅ Hakuna mtu anayeweza kuchimba bila ruhusa yako
✅ Unastahili fidia ikiwa ardhi yako inatumika
✅ Unaweza kuomba leseni ya uchimbaji mwenyewe
📞 Piga simu: +254-XXX-XXXX (Mining Office Migori)

[Soma zaidi] [Rudi nyuma]
```

### 4.3 Error Handling

```
❌ "Samahani, sijaelewa. Tafadhali chagua moja:
   1️⃣ Angalia madini
   2️⃣ Tuma picha
   3️⃣ Soma haki zako"

📍 (if location fails): "Sijapata mahali pako. 
   Andika jina la mahali mfano: Nyatike, Migori"

📸 (if photo unclear): "Picha haionekani vizuri. 
   Tafadhali piga picha karibu zaidi na mwanga mzuri"
```

### 4.4 Bot Personality

- **Tone:** Helpful elder sibling, not government official
- **Humor:** Light, appropriate — "Mawe ya dhahabu hayajitambulishi 😄"
- **Empathy:** Acknowledge uncertainty — "Sijui kwa uhakika, lakini..."
- **Urgency:** Clear when something matters — "⚠️ Hii ni muhimu!"
- **Never:** Condescending, overly technical, or bureaucratic

---

## 5. Flutter App UX

### 5.1 App Architecture: Offline-First

```
┌─────────────────────────────────────────────┐
│                 Flutter App                   │
│                                               │
│  ┌─────────────┐  ┌──────────────────────┐  │
│  │  Local DB    │  │  Cached Mineral Data  │  │
│  │  (SQLite)    │  │  (<5MB)              │  │
│  └──────┬──────┘  └──────────┬───────────┘  │
│         │                     │               │
│  ┌──────┴──────────────────────┴──────────┐  │
│  │          Sync Engine (Background)       │  │
│  │  - Syncs when connectivity available   │  │
│  │  - Queues reports for upload           │  │
│  │  - Downloads updates opportunistically │  │
│  └────────────────────────────────────────┘  │
│                                               │
│  ┌────────────────────────────────────────┐  │
│  │          UI Layer (Material Design)    │  │
│  │  - Large touch targets (48dp min)      │  │
│  │  - High contrast colors               │  │
│  │  - Swahili-first text                 │  │
│  │  - Offline indicator always visible   │  │
│  └────────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### 5.2 Screen Flow

```
Splash Screen (2s max)
    │
    ├── Onboarding (first launch only, 3 screens)
    │   Screen 1: "Karibu! 🪨" — What the app does
    │   Screen 2: "Angalia madini eneo lako" — Core feature
    │   Screen 3: "Tuma picha ya mawe" — Photo feature
    │   → [Anza!] button
    │
    ├── Home Screen
    │   ┌─────────────────────────────────────┐
    │   │  🪨 Msaidizi wa Madini              │
    │   │                                      │
    │   │  ┌─────────┐  ┌─────────┐          │
    │   │  │ 📍      │  │ 📸      │          │
    │   │  │ Angalia │  │ Picha   │          │
    │   │  │ Eneo    │  │         │          │
    │   │  └─────────┘  └─────────┘          │
    │   │                                      │
    │   │  ┌─────────┐  ┌─────────┐          │
    │   │  │ 📜      │  │ 📊      │          │
    │   │  │ Haki   │  │ Ripoti  │          │
    │   │  │ Zako   │  │         │          │
    │   │  └─────────┘  └─────────┘          │
    │   │                                      │
    │   │  ──────────────────────────         │
    │   │  📰 Habari za Madini                 │
    │   │  • Dhahabu: KSh 7,500/g             │
    │   │  • Leseni mpya: 3 wilayani           │
    │   │                                      │
    │   │  🟢 Online  |  Data: 2.3MB imetumika │
    │   └─────────────────────────────────────┘
    │
    ├── Mineral Lookup Screen
    │   → Map view (simplified, offline tiles)
    │   → OR text search for location
    │   → Results: list of minerals with likelihood
    │   → Detail screen per mineral
    │
    ├── Photo Analysis Screen
    │   → Camera viewfinder with guide overlay
    │   → "Piga picha ya mawe hapa"
    │   → Capture → Process → Results
    │
    ├── Rights Screen
    │   → Categorized: Land / Mining / Environment / Disputes
    │   → Simple bullet points
    │   → "Piga simu" button for each relevant office
    │
    └── Profile/Settings
        → Language switch
        → Data usage tracker
        → Clear cache
        → About / Privacy
```

### 5.3 Performance Targets

| Metric | Target | Why |
|--------|--------|-----|
| APK size | <15 MB | Budget phones have 1-2GB total storage |
| Cold start | <3 seconds | Users abandon after 3s |
| RAM usage | <80 MB | 1GB RAM devices need headroom |
| Offline capability | 100% core features | No connectivity = no problem |
| Battery drain | <3% per hour active | Users don't charge daily |
| Image compression | <100KB per photo upload | Data budget |
| Database size | <5MB | Storage constraint |

### 5.4 Design Tokens

```dart
// Colors (high contrast, accessible)
const primaryColor = Color(0xFF1B5E20);      // Deep green (Kenya flag)
const secondaryColor = Color(0xFFFF6F00);     // Amber (mineral/earth)
const backgroundColor = Color(0xFFFFF8E1);    // Warm cream
const errorColor = Color(0xFFB71C1C);         // Deep red
const surfaceColor = Color(0xFFFFFFFF);        // White

// Typography (large, readable)
const headingLarge = TextStyle(fontSize: 24, fontWeight: FontWeight.bold);
const bodyLarge = TextStyle(fontSize: 18);     // Larger than typical 14-16
const buttonLarge = TextStyle(fontSize: 20, fontWeight: FontWeight.w600);

// Touch targets
const minTouchTarget = 48.0;  // dp, Material Design minimum
const preferredTouchTarget = 56.0;  // dp, our preferred

// Spacing
const paddingSmall = 12.0;
const paddingMedium = 16.0;
const paddingLarge = 24.0;
```

### 5.5 Offline-First Sync Strategy

```
User Action (offline)
    │
    ├── Mineral Lookup → Serve from local DB (always works)
    ├── Photo Analysis → Queue for processing when online
    ├── Rights Info → Serve from local cache (always works)
    └── Report Submit → Queue locally, upload when connected

Sync Engine (background):
    1. Check connectivity every 60s
    2. If connected:
       a. Upload queued reports (batched, compressed)
       b. Download mineral data updates (delta only)
       c. Download news/price updates
    3. Notify user: "Data imesasishwa ✅" (if new data)
```

---

## 6. Big Tech Standards: How Google/Meta Build Products

### 6.1 Google's HEART Framework (Adapted)

| Metric | Definition | Our Target |
|--------|-----------|------------|
| **Happiness** | User satisfaction | >80% positive feedback in Swahili surveys |
| **Engagement** | How often users return | >3 queries per user per week |
| **Adoption** | New users | 1,000 users in first 3 months |
| **Retention** | Users still active after 30 days | >40% (high for low-connectivity areas) |
| **Task Success** | Users complete their goal | >90% mineral lookup success rate |

### 6.2 Meta's "Move Fast" with Guardrails

| Meta Principle | Our Adaptation |
|----------------|----------------|
| Ship early, iterate fast | Launch Telegram bot in Week 3 (MVP), iterate based on real usage |
| A/B test everything | Test Swahili phrasings, emoji usage, response length |
| Data-informed decisions | Track: query types, drop-off points, language switches, error rates |
| Build for the next billion | We ARE building for the next billion. Every Meta "lite" product principle applies. |

### 6.3 Google's Material Design for Emerging Markets

| Principle | Application |
|-----------|-------------|
| **Adaptive layouts** | Works on 4" screens (common budget phone size) |
| **Progressive disclosure** | Show basics first, details on demand |
| **Meaningful motion** | Minimal animations (save battery and data) |
| **Accessibility** | WCAG 2.1 AA minimum, high contrast, large text |
| **Internationalization** | RTL-ready (future Arabic support), proper text wrapping for Swahili |

### 6.4 Product Engineering Process

```
Week 1-2:   Discovery & Prototyping
            → User interviews in Nyatike (3-5 miners, 2-3 landowners)
            → Paper prototypes of bot flows
            → Validate language and terminology

Week 3-4:   MVP Build (Telegram Bot)
            → Core mineral lookup
            → Photo analysis (basic)
            → Swahili NLU
            → Internal testing

Week 5-6:   Pilot Launch
            → 50 beta users in Nyatike
            → Daily feedback collection
            → Iterate on bot responses
            → Measure: completion rate, error rate, satisfaction

Week 7-8:   Flutter App Alpha
            → Offline mineral database
            → Basic UI (4 screens)
            → Performance testing on budget devices

Week 9-10:  Feature Expansion
            → Cooperative dashboard
            → Multi-language (add Luo)
            → Community reporting

Week 11-12: Public Launch
            → Telegram bot: open to all
            → Flutter app: Play Store (Kenya)
            → Launch event with cooperative leaders

Week 13+:   Continuous Improvement
            → Monitor HEART metrics
            → Monthly feature releases
            → Quarterly user research sessions
```

### 6.5 Quality Gates

| Gate | Criteria | Tool |
|------|----------|------|
| **Code** | >80% test coverage, no critical bugs | Flutter test, pytest |
| **Performance** | APK <15MB, cold start <3s, RAM <80MB | Flutter devtools |
| **Accessibility** | WCAG 2.1 AA, Swahili proofread by native speaker | Manual review |
| **Connectivity** | All core features work offline | Network throttling tests |
| **Device** | Tested on Tecno Spark Go (1GB RAM) | Real device lab |
| **Language** | All strings in Swahili reviewed by native speaker | Crowdin + review |

---

## 7. Success Metrics & KPIs

### Product Metrics

| KPI | Target (3 months) | Target (12 months) |
|-----|--------------------|--------------------|
| Total users | 500 | 5,000 |
| Daily active users | 50 | 500 |
| Queries per day | 100 | 1,000 |
| Photo analyses per day | 20 | 200 |
| Reports submitted | 50 | 500 |
| Languages used | Swahili + English | + Luo, Kamba, Luhya |
| User satisfaction (CSAT) | >75% | >85% |
| Bot completion rate | >80% | >90% |
| App crash rate | <2% | <1% |
| Offline usage % | >30% | >20% (connectivity improves) |

### Engagement Funnel

```
Awareness:   10,000 (SMS campaigns, cooperative outreach)
    ↓ 20%
Trial:        2,000 (first query)
    ↓ 50%
Activation:   1,000 (completed first mineral lookup)
    ↓ 40%
Retention:      400 (active after 30 days)
    ↓ 30%
Advocacy:       120 (shared with others / cooperative use)
```

---

## 8. Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Users don't trust the system | High | Critical | Partner with trusted local cooperatives; show data sources clearly |
| Mineral data is inaccurate | Medium | Critical | Always disclaim "tathimini ya awali"; partner with geological survey |
| Users can't type in Swahili | Medium | High | Offer voice input (Phase 3); use button-based interactions |
| Photo analysis gives false positives | High | High | Confidence thresholds; always recommend professional verification |
| Data bundles too expensive | Medium | High | Ultra-compressed responses; SMS fallback; offline mode |
| Government pushback | Low | Critical | Frame as awareness tool, not legal advice; consult with county officials |

---

## Summary

**The product philosophy is simple:**

> **"Mtu yeyote, mahali popote, anaweza kujua ni madini gani yako kwenye ardhi yake."**
> *(Anyone, anywhere, can know what minerals are on their land.)*

We build for Mama Jane's feature phone first, Brian's budget Android second, and Grace's dashboard third. If it works for the most constrained user, it works for everyone.

**Phase 1 delivers a Telegram bot that speaks Swahili, identifies minerals from photos, and tells people their rights — all in under 160 characters per response.**

---

*Document generated: 2026-07-25*
*Council Member 5: Product Lead — Product & UX Engineering*
*Status: COMPLETE ✅*
