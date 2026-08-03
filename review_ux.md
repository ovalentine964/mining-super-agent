# UX & Accessibility Review — Sovereign Resource DAO

**Reviewed by:** UX & Accessibility Review Council
**Date:** 2026-08-04
**Scope:** Flutter mobile app, React dashboard, Telegram bot, localization, accessibility, onboarding

---

## Executive Summary

The Sovereign Resource DAO has a solid foundation with bilingual support (Swahili/English), consistent branding, and thoughtful feature design targeting Kenyan artisanal miners. However, the project has **significant accessibility gaps** (zero `Semantics` widgets in Flutter, zero ARIA attributes in the dashboard), **incomplete error handling UX** in several screens, **hardcoded strings** that bypass the i18n system, and **no onboarding experience** for first-time users. The Telegram bot is the strongest UX surface — well-structured with good command discovery and error recovery.

**Overall UX Grade: C+** (functional but needs substantial a11y and polish work)

---

## 1. Flutter Mobile UX

### 1.1 Navigation Flow

| Aspect | Status | Notes |
|--------|--------|-------|
| Home screen grid layout | ✅ Good | 9 menu cards in a 2-column grid, clear icons + bilingual labels |
| Navigation pattern | ⚠️ Fair | All screens use `Navigator.push` with `MaterialPageRoute` — no named routes, no deep linking |
| Back navigation | ✅ Good | Standard AppBar back buttons |
| Bottom navigation | ❌ Missing | No bottom nav bar; users must return to home for every screen switch |
| Screen transitions | ⚠️ Fair | Default MaterialPageRoute transitions only — no custom animations |

**Issues:**
- **No bottom navigation bar.** With 9 screens, a bottom nav (3-5 top destinations) + drawer for the rest would reduce navigation friction significantly. Miners in the field need quick access to Camera, Prices, and Chat.
- **No named routes or deep linking.** Makes it impossible to share links to specific screens or handle push notification navigation.
- **No navigation breadcrumbs or history.** The 9-card grid is the only entry point — no "recently used" or "favorites" section.

### 1.2 Error Handling UX

| Screen | Error Handling | Quality |
|--------|---------------|---------|
| `AgentChatScreen` | Shows raw `Exception.toString()` in chat bubbles | ❌ Poor |
| `BlockchainScreen` | Silently swallows errors, shows stale/empty state | ❌ Poor |
| `DaoScreen` | Shows raw `Error: $e` in SnackBar | ❌ Poor |
| `FairDealScreen` | Shows raw `Error: $e` in SnackBar | ❌ Poor |
| `PhotoScreen` | No error handling for API failures | ❌ Poor |
| `PriceScreen` | No error handling (hardcoded data) | N/A |
| `VoiceChatScreen` | `debugPrint` only, no user-facing errors | ❌ Poor |

**Critical Issues:**

1. **Raw exception leaking to users** — `AgentChatScreen._sendTextMessage()` shows `Hitilafu: $e\nError: $e` directly in chat bubbles. Exception objects contain stack traces, internal URLs, and potentially sensitive info.

2. **`DaoScreen._vote()`** — `SnackBar(content: Text('Error: $e'))` exposes raw API errors. A miner seeing `HttpException: Connection refused` is not helpful.

3. **No retry mechanisms** — When API calls fail, users have no way to retry except manually re-triggering the action. No "Tap to retry" patterns anywhere.

4. **`BlockchainScreen._loadStatus()`** — catches errors but just sets `_loading = false` with no error state shown. Users see a blank screen with no explanation.

**Recommendations:**
- Create a centralized error handler that maps `ApiException` types to user-friendly bilingual messages
- Add retry buttons on all error states
- Never show raw exception text to users
- Use `SnackBar` with action buttons ("Retry", "Dismiss") instead of raw error strings

### 1.3 Loading States

| Screen | Loading Indicator | Quality |
|--------|------------------|---------|
| `BlockchainScreen` | `CircularProgressIndicator` (full screen) | ✅ Good |
| `DaoScreen` | `CircularProgressIndicator` (full screen) | ✅ Good |
| `PriceScreen` | `CircularProgressIndicator` (full screen) | ✅ Good |
| `FairDealScreen` | Button spinner + text "Inachambua..." | ✅ Good |
| `AgentChatScreen` | Button spinner (sends) + no message-level loading | ⚠️ Fair |
| `PhotoScreen` | `CircularProgressIndicator` + "Analyzing mineral..." | ✅ Good |
| `VoiceChatScreen` | Pulse animation + status text | ✅ Good |
| `ReportScreen` | No loading (static) | N/A |

**Issues:**
- **No skeleton/shimmer loading** — All screens use a single centered spinner. For list-based screens (DAO proposals, prices), skeleton placeholders would feel faster.
- **`AgentChatScreen`** — No per-message loading indicator. When a message is sent, the user sees nothing until the response arrives. A "typing..." indicator or message-level spinner would improve perceived responsiveness.
- **No pull-to-refresh on `AgentChatScreen` or `PhotoScreen`**.

### 1.4 Empty States

| Screen | Empty State | Quality |
|--------|------------|---------|
| `AgentChatScreen` | Icon + bilingual text + quick action chips | ✅ Excellent |
| `BlockchainScreen` | Icon + bilingual "Hakuna rekodi bado" | ✅ Good |
| `DaoScreen` | Icon + bilingual "Hakuna mapendekezo bado" | ✅ Good |
| `PriceScreen` | No empty state (hardcoded data) | N/A |
| `ReportScreen` | Icon + "No reports yet" + CTA | ✅ Good |
| `PhotoScreen` | Camera icon + instruction text | ✅ Good |

**Strengths:** Empty states are consistently designed with icons, bilingual text, and helpful guidance. The `AgentChatScreen` empty state with quick action chips is particularly well done.

**Issue:** `ReportScreen` empty state is English-only ("No reports yet", "Take a photo to generate your first report").

### 1.5 Form Validation

| Screen | Validation | Quality |
|--------|-----------|---------|
| `FairDealScreen` | `int.tryParse` with fallback to 0 | ⚠️ Fair |
| `DaoScreen` (vote) | None — hardcoded voter/tokens | ❌ Poor |
| `AgentChatScreen` | Empty text check | ⚠️ Fair |

**Issues:**
- **`FairDealScreen`** — No inline validation. If a user enters "abc", `int.tryParse` returns 0 and the API call proceeds with `offer_amount_kes: 0`. No error message, no field highlighting.
- **No input formatting** — The offer amount field accepts raw numbers with no thousand separators. A miner entering "1,000,000" gets parsed as 1 (strips comma, then `int.tryParse` fails on remaining text).
- **No form validation library** — All validation is ad-hoc. Consider `flutter_form_builder` or at minimum `TextFormField` with `validator` callbacks.

### 1.6 Touch Targets

| Element | Size | Meets 48dp? |
|---------|------|-------------|
| Home screen menu cards | ~160dp × ~160dp | ✅ Yes |
| Voice button (AgentChatScreen) | 48dp circle | ✅ Yes (barely) |
| Send button (AgentChatScreen) | 40dp CircleAvatar | ❌ No |
| Text input camera icon | ~24dp IconButton | ❌ No |
| Quick action chips | ~32dp height | ❌ No |
| Voice control buttons (VoiceChatScreen) | 32dp icon + text | ❌ No |
| Vote buttons (DaoScreen) | ElevatedButton (≥48dp) | ✅ Yes |
| Price refresh button | IconButton (~24dp) | ❌ No |
| Language toggle buttons (SettingsScreen) | ListTile (~56dp) | ✅ Yes |

**Critical Issues:**
- **AgentChatScreen send button** — `CircleAvatar` with `IconButton` inside is only ~40dp. Needs to be at least 48dp.
- **VoiceChatScreen control buttons** — The stop/start and clear buttons are 32dp icons with small text labels. The main talk button (80dp) is fine, but the flanking controls are too small for field use with gloves.
- **Quick action chips** — `ActionChip` defaults to ~32dp height. Should be at least 40dp for mining field conditions.

### 1.7 Screen Reader Support (Semantics)

**❌ CRITICAL: Zero `Semantics` widgets found across the entire Flutter codebase.**

No `semanticsLabel`, no `Semantics` widget, no `ExcludeSemantics`, no `MergeSemantics`. The app is completely invisible to screen readers (TalkBack/VoiceOver).

**Impact:** Any visually impaired user — including miners with eye injuries or age-related vision loss — cannot use the app at all.

### 1.8 Color Contrast

| Element | Foreground | Background | Ratio | WCAG AA? |
|---------|-----------|------------|-------|----------|
| Home card labels | `Colors.black87` (#333) | White card | 11.4:1 | ✅ |
| AgentChatScreen user message | White (#FFF) | Gold (#8B6914) | 4.1:1 | ⚠️ Barely passes |
| AgentChatScreen assistant text | `Colors.black87` | `grey.shade100` | 10.7:1 | ✅ |
| VoiceChatScreen status text | Colors.green (#4CAF50) | Dark (#1A1A2E) | 5.9:1 | ✅ |
| VoiceChatScreen transcript | White | Dark (#1A1A2E) | 13.5:1 | ✅ |
| BlockchainScreen error text | Colors.red (#F44336) | White card | 3.9:1 | ❌ Fails AA |
| Price change colors | Green/Red | Various backgrounds | Variable | ⚠️ Check needed |

**Issues:**
- **Gold (#8B6914) on white** for AppBar text — contrast ratio ~3.2:1, **fails WCAG AA** (needs 4.5:1 for normal text).
- **Red text on white** in several places (BlockchainScreen error states) fails AA.
- **No dark mode support** — `Brightness.light` only. Field miners working in bright sunlight need high contrast; miners checking at night need dark mode.

---

## 2. Dashboard UX (React)

### 2.1 Responsive Design

**CSS Breakpoints:**
```css
@media (max-width: 768px) {
  .dashboard-grid { grid-template-columns: 1fr; }
  .price-grid { grid-template-columns: 1fr; }
  .royalty-stats { grid-template-columns: 1fr; }
}
```

| Breakpoint | Status | Notes |
|-----------|--------|-------|
| Desktop (>1200px) | ✅ Good | 2-column grid, max-width 1400px |
| Tablet (768-1200px) | ⚠️ Fair | 2-column grid may be cramped on small tablets |
| Mobile (<768px) | ✅ Good | Single column, responsive adjustments |

**Issues:**
- **Only one breakpoint** (768px). No intermediate tablet breakpoint.
- **No `viewport` meta tag** — not visible in the HTML, but crucial for mobile rendering.
- **`card-full` spans both columns** — On desktop, PriceWidget, ExtractionTable, and ProposalList all span full width. This wastes horizontal space.
- **No touch-specific styles** — Buttons and interactive elements don't have touch-optimized sizing on mobile.

### 2.2 Loading/Error/Empty States

**✅ Excellent pattern** — Every component consistently implements all three states:

```tsx
{isLoading && <div className="state-msg"><div className="spinner" />...</div>}
{error && <div className="state-msg error-msg">...<span className="retry-link">...</span></div>}
{data && data.length === 0 && <div className="state-msg">...</div>}
```

| Component | Loading | Error | Empty | Retry |
|-----------|---------|-------|-------|-------|
| PriceWidget | ✅ | ✅ | N/A (always has data) | ✅ |
| ExtractionTable | ✅ | ✅ | ✅ | ✅ |
| RoyaltyCard | ✅ | ✅ | N/A | ✅ |
| ProposalList | ✅ | ✅ | ✅ | ✅ |
| FairnessIndex | ✅ | ✅ | N/A | ✅ |
| SatelliteAlerts | ✅ | ✅ | ✅ | ✅ |

**Strengths:** This is the best-structured UX code in the project. Consistent patterns, bilingual error messages, clickable retry links.

**Issues:**
- **No skeleton loading** — Spinner-only. For data-heavy cards, skeleton placeholders would feel faster.
- **Error messages are generic** — `t('general.error')` = "Something went wrong" / "Kuna hitilafu". No distinction between network errors, server errors, or timeout.
- **No offline indicator** — WebSocket status dot exists but there's no banner when the backend is unreachable.

### 2.3 Data Visualization Clarity

**PriceWidget (Recharts LineChart):**
- ✅ Uses `ResponsiveContainer` for responsive sizing
- ✅ Color-coded lines (gold=amber, copper=orange, silver=silver)
- ✅ Clean tooltip styling matching dark theme
- ⚠️ No chart legend — users must infer which line is which mineral
- ⚠️ No data point labels on hover beyond tooltip
- ❌ No accessible alternative for screen readers (chart is purely visual)

**FairnessIndex (SVG Gauge):**
- ✅ Custom SVG gauge with color-coded score
- ✅ Clear numeric display (score/100)
- ✅ Descriptive label (Excellent/Good/Fair/Poor)
- ⚠️ No `aria-label` on SVG element
- ❌ Gauge arc is decorative — screen readers get nothing

**ProposalList (Vote Bars):**
- ✅ Dual progress bars (for/against) with distinct colors
- ✅ Numeric vote counts displayed
- ⚠️ No `aria-valuenow` or `role="progressbar"` on vote bars

### 2.4 Keyboard Navigation

**❌ CRITICAL: No keyboard navigation support.**

- No `tabIndex` attributes found
- No `onKeyDown`/`onKeyUp` handlers
- No focus styles defined in CSS
- No skip-to-content link
- No focus trapping in any modal/overlay

**Impact:** Keyboard-only users cannot navigate the dashboard at all. Tab order is undefined.

### 2.5 Color Contrast (WCAG 2.1 AA)

| Element | Colors | Ratio | AA? |
|---------|--------|-------|-----|
| Body text | `#e4e6eb` on `#0f1117` | 13.8:1 | ✅ |
| Muted text | `#8b8fa3` on `#0f1117` | 5.3:1 | ✅ |
| Accent (green) | `#00d4aa` on `#0f1117` | 8.2:1 | ✅ |
| Red (error/down) | `#ff4d6a` on `#0f1117` | 4.8:1 | ✅ |
| Yellow (warning) | `#ffc107` on `#0f1117` | 10.1:1 | ✅ |
| Header logo | `var(--accent)` on `var(--bg-card)` | 7.1:1 | ✅ |
| Badge text | `var(--accent)` on `var(--accent-dim)` | 7.1:1 | ✅ |
| **Muted text on cards** | `#8b8fa3` on `#1a1d28` | 4.2:1 | ⚠️ Borderline |

**Overall:** Dashboard color contrast is **good** due to the dark theme. The muted text on card backgrounds is borderline but passes AA for large text.

### 2.6 ARIA Attributes

**❌ Zero ARIA attributes found across all dashboard components.**

- No `role` attributes
- No `aria-label` or `aria-labelledby`
- No `aria-live` regions for dynamic content updates
- No `aria-describedby` for form inputs
- Screen readers will interpret the entire dashboard as a wall of `<div>` elements

---

## 3. Telegram Bot UX

### 3.1 Conversation Flow

**✅ Well-designed.** The bot has a clear, natural conversation flow:

1. `/start` → Welcome message with clear linking instructions
2. Unlinked users get guided to the mobile app for account linking
3. Linked users see available capabilities (photos, location, chat)
4. Smart detection: text that looks like a link code is auto-routed to `/link`

**Strengths:**
- **Progressive disclosure** — New users see linking instructions; returning users see capabilities
- **Context-aware** — `_looks_like_link_code()` auto-detects codes without requiring the `/link` command
- **Mode-based handling** — `current_mode` tracks if the user is in "awaiting_photo" state after `/analyze`

### 3.2 Command Discovery

**✅ Excellent.** The bot registers commands with Telegram's menu system:

```python
BotCommand("start", "Welcome & link your DAO account"),
BotCommand("link", "Link Telegram to your DAO identity"),
BotCommand("status", "Show your DAO status & channels"),
BotCommand("resources", "Browse community resources"),
BotCommand("analyze", "Send a photo for AI analysis"),
BotCommand("propose", "Submit a governance proposal"),
BotCommand("vote", "Vote on active proposals"),
BotCommand("help", "Show all commands"),
```

The `/help` command provides a comprehensive, categorized command reference.

**Minor Issue:** Command descriptions are English-only in the bot menu. Should be bilingual for Swahili-speaking miners.

### 3.3 Error Messages

| Scenario | Error Message | Quality |
|----------|--------------|---------|
| Invalid link code | "❌ Invalid or expired code." | ✅ Good |
| Already-used code | "⚠️ This code has already been used." | ✅ Good |
| Photo analysis fails | "❌ Analysis failed. Please try again or contact support." | ✅ Good |
| Document processing fails | "❌ Failed to process document." | ✅ Good |
| Video processing fails | "❌ Failed to process video." | ✅ Good |
| Audio transcription fails | "🎤 Couldn't transcribe audio. Try again?" | ✅ Good |
| Text routing fails | "❌ Something went wrong. Please try again." | ✅ Good |
| Status fetch fails | "❌ Failed to fetch status." | ✅ Good |
| Vote fails | "❌ Vote failed. You may have already voted." | ✅ Good |
| Access denied | "⛔ Access denied." | ✅ Good |

**Strengths:** Error messages are human-readable, use emoji for visual scanning, and don't expose internal details. The voice transcription failure message is particularly good — empathetic and actionable.

**Weakness:** All error messages are English-only. Should be bilingual.

### 3.4 Inline Keyboard Usability

**✅ Good patterns:**
- Resource browsing uses a 2×3 grid of categorized buttons
- Voting uses 👍/👎/🤷 emoji buttons — universally understood
- Proposal confirmation uses ✅/❌ clear choices
- Callback data uses structured `action:subaction:id` format

**Issues:**
- **No pagination** — `/vote` shows up to 5 proposals at once. For communities with many proposals, this could be overwhelming.
- **No confirmation for votes** — Voting is instant with no "Are you sure?" step. In a governance context, accidental votes could be problematic.
- **Callback data length** — `propose:confirm:{title[:50]}` truncates titles. If two proposals share the first 50 characters, they'd collide.

### 3.5 Voice Message Handling

**✅ Well-implemented flow:**
1. User sends voice message
2. Bot shows "🎤 Transcribing audio..." (processing indicator)
3. Transcribes via NVIDIA NIM Whisper
4. Shows transcript + routes to AI agent
5. Returns AI response

**Issues:**
- **No language detection** — The bot assumes the voice message is in a language Whisper can handle, but doesn't detect or report what language was detected.
- **No voice response** — The bot transcribes and responds with text only. For illiterate miners, a voice response (TTS) would be more accessible.
- **Long timeout (120s)** — While generous, a 2-minute wait with no progress update could feel broken. Consider streaming progress.

---

## 4. Localization Quality

### 4.1 Translation Coverage

**Flutter App (`app_localizations.dart`):**

| Language | Keys Translated | Coverage |
|----------|----------------|----------|
| English (en) | 7/7 | 100% |
| Swahili (sw) | 7/7 | 100% |
| Luo (luo) | 7/7 | 100% |
| Luyia (luy) | 7/7 | 100% |
| Kamba (kam) | 7/7 | 100% |

**BUT** — Only 7 keys are defined! The vast majority of UI strings are hardcoded directly in widget files. The localization system is essentially unused.

**Dashboard (`i18n.ts`):**

| Language | Keys | Coverage |
|----------|------|----------|
| English (en) | ~45 keys | ~95% |
| Swahili (sw) | ~45 keys | ~90% |

**Dashboard is much better** — most visible strings go through `createTranslator()`. However, some strings are still hardcoded (see below).

### 4.2 Hardcoded English Strings

**Flutter (Critical):**

| File | Hardcoded String | Should Be |
|------|-----------------|-----------|
| `home_screen.dart` | `'Sovereign Resource DAO'` (AppBar title) | Localized |
| `home_screen.dart` | `'Tambua Madini\nIdentify Mineral'` etc. | Partially localized (Swahili in code, not in i18n) |
| `agent_chat_screen.dart` | `'Andika ujumbe au ongea'` | In i18n system |
| `agent_chat_screen.dart` | `'Type or speak your message'` | In i18n system |
| `agent_chat_screen.dart` | All quick action labels | In i18n system |
| `blockchain_screen.dart` | `'Blockchain Status'` | Localized |
| `blockchain_screen.dart` | `'Smart Contracts'`, `'Extraction Records'` | Localized |
| `blockchain_screen.dart` | Contract names (`'RoyaltyDistributor'` etc.) | Acceptable (technical) |
| `dao_screen.dart` | `'DAO Governance'` | Localized |
| `fair_deal_screen.dart` | `'Fair Deal Calculator'` | Localized |
| `fair_deal_screen.dart` | All form labels and descriptions | Partially bilingual in code |
| `photo_screen.dart` | `'Identify Mineral'`, `'Take Photo'` etc. | Localized |
| `price_screen.dart` | `'Market Prices'`, mineral names | Localized |
| `report_screen.dart` | `'Reports'`, `'No reports yet'` | Localized |
| `settings_screen.dart` | `'Settings'`, `'Language'`, `'Server'` | Localized |
| `voice_chat_screen.dart` | Status messages, UI labels | Partially bilingual in code |

**Pattern observed:** Developers are adding bilingual text directly in widget code (e.g., `'Hakuna rekodi bado\nNo extraction records yet'`) instead of using the i18n system. This is fragile and doesn't scale.

**Dashboard:**

| File | Hardcoded String |
|------|-----------------|
| `Header.tsx` | `'⛏️ Sovereign Resource DAO'` |
| `ProposalList.tsx` | `'🔗'` prefix (acceptable — emoji) |

Dashboard is mostly clean — the i18n system is well-used.

### 4.3 Cultural Appropriateness

**Swahili translations reviewed:**

| Key | Translation | Assessment |
|-----|-------------|------------|
| `Dashibodi` (Dashboard) | Direct transliteration | ✅ Acceptable — common in East African tech |
| `Unganisha Mkoba` (Connect Wallet) | "Connect Wallet" | ✅ Good — "mkoba" is colloquial for wallet |
| `Bei ya Madini` (Mineral Prices) | Accurate | ✅ Good |
| `Rekodi za Uchimbaji` (Extraction Records) | Accurate | ✅ Good |
| `Mgawo wa Royaliti` (Royalty Distributions) | "Royaliti" is transliteration | ⚠️ Fair — consider "Faida ya Madini" |
| `Mapendekezo ya Utawala` (Governance Proposals) | Accurate | ✅ Good |
| `Fahirisi ya Usawa wa Uchimbaji` (Extraction Fairness Index) | Accurate but long | ⚠️ May overflow UI |
| `Tahadhari za Ufuatiliaji wa Satelaiti` (Satellite Monitoring Alerts) | Very long | ❌ Will overflow in most UI contexts |
| `Bora Sana` (Excellent) | Natural Swahili | ✅ Good |
| `Dhaifu` (Poor) | Acceptable | ✅ Good |

**Issues:**
- Several Swahili translations are very long and will overflow UI containers (especially "Fahirisi ya Usawa wa Uchimbaji" and "Tahadhari za Ufuatiliaji wa Satelaiti").
- The i18n key `'fairness.fair'` has a syntax error: `{ en: 'Fair', wastani }` — missing `sw:` prefix. This will cause a TypeScript compilation error.
- Luo/Luyia/Kamba translations appear to be machine-generated or placeholder quality. Several use Swahili words (`'Ripoti'`, `'Mipangilio'`) instead of the target language.

### 4.4 Number/Currency Formatting

| Location | Format | Issue |
|----------|--------|-------|
| FairDealScreen | `KES 1,000,000` (prefix text) | ⚠️ No locale-aware formatting |
| ExtractionTable | `toLocaleString()` | ✅ Good |
| RoyaltyCard | `$X,XXX` via `toLocaleString()` | ✅ Good |
| PriceWidget | `$X,XXX.XX` via `toLocaleString()` | ✅ Good |
| DaoScreen stats | Raw numbers `${stats['total_members'] ?? 0}` | ❌ No formatting |
| PriceScreen (Flutter) | Hardcoded `'2,650.00'` strings | ❌ No locale formatting |

**Dashboard uses `toLocaleString()`** which is good — it adapts to the user's browser locale. Flutter app does not.

### 4.5 Date/Time Formatting

| Location | Format | Issue |
|----------|--------|-------|
| ExtractionTable | `new Date().toLocaleDateString()` | ✅ Locale-aware |
| RoyaltyCard | `new Date().toLocaleDateString()` | ✅ Locale-aware |
| SatelliteAlerts | `new Date().toLocaleString()` | ✅ Locale-aware |
| AgentChatScreen | Manual `HH:MM` format | ⚠️ No locale awareness |
| VoiceChatScreen | Manual `HH:MM` format | ⚠️ No locale awareness |

### 4.6 RTL Considerations

**No RTL support exists.** No `dir` attributes, no `text-direction` CSS, no Flutter `Directionality` widget. If expanding to Arabic-speaking markets (Sudan, Egypt, Somalia), this would require significant rework.

---

## 5. Accessibility (a11y)

### 5.1 Flutter Semantics

**❌ CRITICAL: Zero Semantics widgets in the entire Flutter codebase.**

```
grep -r "Semantics\|semanticsLabel" → No results
```

**Missing:**
- No `Semantics` widgets on any interactive element
- No `semanticsLabel` on icons (camera, microphone, vote buttons)
- No `semanticsHint` on form fields
- No `ExcludeSemantics` for decorative elements
- No `MergeSemantics` for grouped elements (menu cards)
- No `SemanticsService.announce()` for dynamic state changes

**Impact:** The app is completely inaccessible to screen reader users. TalkBack (Android) and VoiceOver (iOS) will read nothing meaningful.

### 5.2 Dashboard ARIA

**❌ Zero ARIA attributes found.**

```
grep -r "aria-\|role=" → No results
```

**Missing:**
- No `role="navigation"`, `role="main"`, `role="banner"`
- No `aria-label` on any interactive element
- No `aria-live="polite"` for dynamic content (prices, alerts)
- No `role="table"` on the extraction table
- No `role="progressbar"` on vote bars
- No `aria-valuemin`/`aria-valuemax`/`aria-valuenow` on the fairness gauge
- No `alt` text considerations for emoji icons

### 5.3 Keyboard Navigation

**Flutter:**
- No custom focus management
- Default Material widgets have some keyboard support (buttons are focusable)
- No `FocusTraversalGroup` or custom tab order
- VoiceChatScreen's `GestureDetector` (hold-to-talk) is not keyboard-accessible

**Dashboard:**
- No `tabIndex` attributes
- No focus styles in CSS
- No `:focus` or `:focus-visible` pseudo-class styles
- No skip-to-content link
- Retry links (`<span className="retry-link">`) are not `<button>` elements — keyboard users can't reach them
- Language toggle buttons are `<button>` elements ✅
- Vote buttons are `<button>` elements ✅

### 5.4 Font Sizes and Scaling

**Flutter:**
- Home screen card labels: 13px (small for field conditions)
- Agent chat messages: 15px (acceptable)
- Various labels: 12px (too small for outdoor use)
- No `MediaQuery.textScaleFactor` consideration
- No minimum font size enforcement

**Dashboard:**
- Base font: System font stack (good)
- Card titles: 1rem (16px) ✅
- Muted text: 0.8rem (12.8px) — borderline for accessibility
- Small badges: 0.7rem (11.2px) — too small
- No `rem`-based responsive font scaling

### 5.5 Motion/Animation Accessibility

**❌ No `prefers-reduced-motion` support anywhere.**

| Animation | Location | Reduced Motion? |
|-----------|----------|----------------|
| `@keyframes pulse` | Dashboard WS dot | ❌ No |
| `@keyframes spin` | Dashboard spinner | ❌ No |
| `AnimationController` pulse | Flutter VoiceChatScreen | ❌ No |
| Card hover transitions | Dashboard | ❌ No |
| Button transitions | Dashboard | ❌ No |

Users with vestibular disorders or motion sensitivity have no way to disable animations.

---

## 6. Onboarding & Help

### 6.1 First-Run Experience

**❌ No first-run experience exists.**

When a miner first opens the Flutter app:
1. They see the 9-card home screen with no explanation
2. No welcome dialog or tour
3. No explanation of what the DAO is or how it helps them
4. No setup wizard (API server configuration, language selection)
5. No account creation or linking flow in the app

The Telegram bot has better onboarding (`/start` with linking instructions), but the mobile app — which is the primary interface — has none.

### 6.2 Help Text and Tooltips

**Flutter:**
- `PopupMenuButton` on AgentChatScreen has `tooltip: 'Badilisha Agent (Switch Agent)'` ✅
- `IconButton` for voice settings has tooltip ✅
- `IconButton` for camera has tooltip ✅
- No help text on form fields (FairDealScreen offer input)
- No explanation of what the Fair Deal Calculator actually does (just "Enter the amount being offered")
- No help text explaining what the DAO Governance screen is for

**Dashboard:**
- No tooltips on any element
- No help text or info icons
- No explanation of the Fairness Index (what does 65/100 mean?)
- WebSocket status dot has a `title` attribute ✅ (but no visible help)
- Validator addresses are truncated with no way to see the full address (no tooltip on hover)

### 6.3 Tutorial or Guide

**❌ No tutorial, guide, or contextual help exists anywhere in the project.**

### 6.4 First-Time Miner Experience (Scenario)

**Imagine Valentine, a gold miner in Nyatike, Migori County, opening the app for the first time:**

1. Opens app → Sees 9 cards with icons. Some labels are bilingual, some are English-only.
2. Taps "Tambua Madini / Identify Mineral" → Camera opens. No explanation of what to photograph or how to get good results.
3. Takes a photo → Sees "Mineral identification will appear here." (TODO placeholder). No actual analysis.
4. Goes back, taps "Bei za Soko / Market Prices" → Sees hardcoded prices (Gold $2,650, Copper $9,450). These are static, not live.
5. Taps "Hakiki Ofa / Fair Deal" → Sees a form with "KES 1,000,000" pre-filled. No explanation of what this does or why it matters.
6. Taps "Mazungumzo / Agent Chat" → Sees empty chat with quick actions. Taps "📸 Tuma Picha" → "Picha — Coming soon!"
7. Taps "Mipangilio / Settings" → Can change language. Server URL is hardcoded `http://localhost:8000` with no way to configure.
8. **Closes app. Never returns.**

**The onboarding gap is the single biggest UX risk for adoption.**

---

## 7. Priority Recommendations

### P0 — Critical (Fix Before Launch)

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| 1 | **Add Flutter Semantics widgets** to all interactive elements | Screen reader users can't use the app | Medium |
| 2 | **Add ARIA attributes** to all dashboard components | Screen reader users can't use the dashboard | Medium |
| 3 | **Fix raw exception display** in Flutter error handlers | Users see stack traces, potential security leak | Low |
| 4 | **Add keyboard navigation** to dashboard (tabIndex, focus styles) | Keyboard users locked out | Medium |
| 5 | **Create onboarding flow** for first-time users | 0% conversion without it | High |
| 6 | **Fix i18n syntax error** (`fairness.fair` missing `sw:` key) | TypeScript compilation error | Trivial |
| 7 | **Increase touch targets** to 48dp minimum | Field use with gloves is impossible | Low |

### P1 — High (Fix Within Sprint)

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| 8 | **Move hardcoded strings to i18n system** | Can't add new languages, inconsistent translations | Medium |
| 9 | **Add `prefers-reduced-motion` support** | Accessibility compliance | Low |
| 10 | **Add form validation** to FairDealScreen | Users can submit invalid data | Low |
| 11 | **Add bottom navigation bar** to Flutter app | 9 screens with no quick navigation | Medium |
| 12 | **Add dark mode** to Flutter app | Eye strain for night use, sunlight readability | Medium |
| 13 | **Improve error messages** — bilingual, actionable | Users don't know what to do when things fail | Medium |
| 14 | **Add help text/tooltips** to key features | Users don't understand Fair Deal, Fairness Index | Low |

### P2 — Medium (Backlog)

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| 15 | Add skeleton loading states | Better perceived performance | Medium |
| 16 | Add chart legends and accessible alternatives | Data viz comprehension | Low |
| 17 | Improve Swahili translation quality (long strings) | UI overflow | Low |
| 18 | Add RTL support infrastructure | Future Arabic expansion | High |
| 19 | Add retry mechanisms to all error states | Better error recovery | Medium |
| 20 | Add offline indicator banner to dashboard | Users don't know they're offline | Low |
| 21 | Add Telegram bot command descriptions in Swahili | Swahili-speaking users discover commands slower | Low |
| 22 | Add tutorial/contextual help system | User education | High |

---

## Appendix: Detailed File-by-File Findings

### Flutter Files

| File | Lines | Issues Found |
|------|-------|-------------|
| `home_screen.dart` | 109 | No Semantics, hardcoded AppBar title, small touch targets on cards (OK), no bottom nav |
| `agent_chat_screen.dart` | 365 | Raw exceptions in chat, no Semantics, small send button, hardcoded strings, no per-message loading |
| `blockchain_screen.dart` | 147 | Silent error swallowing, no Semantics, hardcoded strings |
| `dao_screen.dart` | 175 | Raw error SnackBars, hardcoded voter, no Semantics, unformatted numbers |
| `fair_deal_screen.dart` | 175 | No form validation, no Semantics, partially hardcoded |
| `photo_screen.dart` | 80 | TODO placeholder, English-only, no Semantics |
| `price_screen.dart` | 78 | Hardcoded data, English-only, no Semantics |
| `report_screen.dart` | 25 | English-only empty state, no Semantics |
| `settings_screen.dart` | 102 | No Semantics, hardcoded server URL, good language picker |
| `voice_chat_screen.dart` | 388 | Complex animations without reduced-motion, no Semantics, `await` in `initState` (bug) |

### Dashboard Files

| File | Lines | Issues Found |
|------|-------|-------------|
| `App.tsx` | 20 | Clean, no ARIA |
| `Header.tsx` | 55 | No ARIA, hardcoded logo text |
| `PriceWidget.tsx` | 82 | No ARIA, no chart legend, no accessible chart alternative |
| `ExtractionTable.tsx` | 62 | No ARIA table roles, good states pattern |
| `RoyaltyCard.tsx` | 52 | No ARIA, good states pattern |
| `ProposalList.tsx` | 85 | No ARIA, vote bars not accessible, good states pattern |
| `FairnessIndex.tsx` | 85 | No ARIA on SVG gauge, good states pattern |
| `SatelliteAlerts.tsx` | 55 | No ARIA, alert dots not accessible, good states pattern |
| `index.css` | 285 | No focus styles, no reduced-motion, one breakpoint, good dark theme contrast |

### Telegram Bot

| File | Lines | Issues Found |
|------|-------|-------------|
| `telegram_bot.py` | 620 | English-only messages, no Swahili bot commands, good error handling, good flow |

### Bug: `voice_chat_screen.dart` — `await` in `initState`

```dart
@override
void initState() {
  super.initState();
  _cloudVoiceService = VoiceService(nvidiaApiKey: 'YOUR_NVIDIA_API_KEY');
  _onDeviceAvailable = await _onDeviceVoice.initialize(); // ❌ BUG
  // ...
}
```

`initState` is synchronous — `await` will not work here. This will cause a compilation error. Should use `WidgetsBinding.instance.addPostFrameCallback` or move to a separate `initAsync()` method called from `initState`.

---

*End of UX & Accessibility Review*
