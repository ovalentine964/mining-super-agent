# COUNCIL 7: Mobile App & Community Interface

**Report Date:** 2026-08-03
**Subject:** Analysis of Flutter Mobile App & DAO Community Governance Interface Design
**Status:** COMPLETE

---

## 1. EXISTING APP INVENTORY

### 1.1 Architecture Overview

The current Flutter app (`mining-super-agent`) is a **mineral identification and market price tool** for Kenyan artisanal miners. It is NOT a DAO governance tool — it's a geology-first mobile utility that needs significant transformation.

**Current Stack:**
| Component | Technology | Purpose |
|-----------|-----------|---------|
| State Management | `provider` | Locale switching only |
| Local DB | `sqflite` (SQLite) | Store observations offline |
| Networking | `http` package | REST API calls |
| Connectivity | `connectivity_plus` | Online/offline detection |
| Camera | `image_picker`, `camera` | Mineral photo capture |
| Location | `geolocator` | GPS coordinates for observations |
| Localization | Manual `_localizedValues` map + ARB files | 4 languages |
| Notifications | `flutter_local_notifications` | Price alerts (declared, not wired) |

**Current Screens (4 total):**
1. **HomeScreen** — 2×2 grid: Identify Mineral, Market Prices, Reports, Settings
2. **PhotoScreen** — Camera capture → API analysis (TODO: not connected)
3. **PriceScreen** — Hardcoded gold/copper/silver prices (TODO: API fetch)
4. **SettingsScreen** — Language picker (English/Swahili/Luo), API server URL
5. **ReportScreen** — Empty placeholder ("No reports yet")

**Current Models (2):**
- `Observation` — mineral observation with photo, GPS, rock type, mineral ID, confidence, sync status
- `CommodityPrice` — name, symbol, price, currency, unit, change%, timestamp

**Current Services (4):**
- `ApiClient` — basic REST client (GET/POST), token auth, multipart upload stub
- `LocalDatabase` — SQLite CRUD for observations, sync flag management
- `OfflineSyncService` — connectivity listener, periodic 5-min sync, pending count stream
- `LocaleProvider` — ChangeNotifier for locale switching (default: Swahili)

### 1.2 Localization Status

**Four language files exist:**

| Language | Code | File | Keys | Quality |
|----------|------|------|------|---------|
| English | `en` | `app_en.arb` | ~65 keys | ✅ Complete, natural |
| Swahili | `sw` | `app_sw.arb` | ~65 keys | ✅ Good, idiomatic |
| Dholuo | `luo` | `app_luo.arb` | ~65 keys | ⚠️ Functional but some entries appear machine-translated |
| Luhya | `luy` | `app_luy.arb` | ~65 keys | ⚠️ Some inconsistencies (e.g., "delete" and "view" both map to "Khola") |
| Kamba | `kam` | `app_kam.arb` | ~65 keys | ⚠️ Reasonable, some entries need native speaker review |

**Critical gap:** The `AppLocalizations` class hardcodes only `en`, `sw`, `luo` — the ARB files for `luy` and `kam` exist but the runtime class doesn't load them. The settings screen only shows English/Swahili/Luo (missing Luhya and Kamba).

**Missing localization keys for DAO transformation:** No keys exist for voting, proposals, treasury, wallet, tokens, royalties, governance, delegation, or any blockchain/DAO concepts.

### 1.3 Offline Capability Assessment

**What works offline:**
- ✅ SQLite local storage for observations
- ✅ Sync flag (`synced` boolean) on each observation
- ✅ `connectivity_plus` listener triggers sync on reconnect
- ✅ 5-minute periodic sync timer
- ✅ Pending count broadcast stream
- ✅ Photos stored locally (`photo_path`)

**What does NOT work offline:**
- ❌ Mineral analysis requires server (no on-device ML)
- ❌ Price data has no local cache (hardcoded fallback only)
- ❌ No offline queue for non-observation actions
- ❌ No conflict resolution for concurrent edits
- ❌ No data compression or delta sync
- ❌ No offline-first UI indicators beyond a single localization key

**Offline architecture grade: C+** — Basic scaffolding exists, but the sync model is simplistic (one-way push, no pull, no conflict resolution, no retry backoff).

---

## 2. DAO TRANSFORMATION REQUIREMENTS

The current app serves **individual miners** identifying rocks. A DAO governance app serves **community members** making collective decisions about shared resources. These are fundamentally different UX paradigms.

### 2.1 What Must Be Added

| Category | New Feature | Priority |
|----------|------------|----------|
| **Identity** | Wallet connection (MetaMask/Trust/WalletConnect) | 🔴 Critical |
| **Identity** | Community membership verification (SBT/token-gate) | 🔴 Critical |
| **Governance** | Proposal creation & browsing | 🔴 Critical |
| **Governance** | Voting interface (yes/no/abstain + delegated) | 🔴 Critical |
| **Governance** | Delegation management | 🟡 High |
| **Treasury** | Balance view (community + personal share) | 🔴 Critical |
| **Treasury** | Royalty payment history | 🟡 High |
| **Treasury** | Disbursement tracking | 🟡 High |
| **Community** | Mineral extraction activity feed | 🟡 High |
| **Community** | Community dashboard (production, revenue, membership) | 🟡 High |
| **Community** | Discussion/comment on proposals | 🟢 Medium |
| **Notifications** | Proposal alerts, voting deadlines, payment receipts | 🟡 High |
| **Education** | "What is a DAO?" onboarding flow | 🟡 High |
| **Education** | Governance tutorial with local language voiceover | 🟢 Medium |

### 2.2 What Must Change

| Current | Problem | Required Change |
|---------|---------|-----------------|
| `HomeScreen` grid (4 tiles) | No governance entry points | Redesign as tabbed navigation: Home, Govern, Treasury, Community |
| `PhotoScreen` single-user flow | Not connected to DAO extraction logging | Integrate with on-chain mineral verification |
| `PriceScreen` hardcoded data | Not connected to actual commodity feeds | Connect to oracle price feeds; show royalty calculations |
| `ReportScreen` empty | No DAO context | Transform into "My Activity" — votes, proposals, contributions |
| `SettingsScreen` 3 languages | Missing Luhya, Kamba | Add all 4 community languages |
| `ApiClient` basic REST | No blockchain interaction | Add Web3 provider, contract calls, transaction signing |
| `LocalDatabase` observations only | No governance data | Add tables for proposals, votes, delegations, treasury events |
| `OfflineSyncService` push-only | No governance state sync | Add bidirectional sync with conflict resolution |

---

## 3. WALLET INTEGRATION DESIGN

### 3.1 Wallet Strategy for Low-Resource Context

**The problem:** MetaMask, Trust Wallet, and WalletConnect are designed for crypto-native users with modern phones. Our users have:
- Cheap Android phones (1-2GB RAM, Android 8-10)
- Limited data (pay-per-MB Safaricom bundles)
- No crypto experience
- Potential distrust of "wallet" apps (scam associations)

**Recommended approach: Abstracted wallet with progressive disclosure**

```
Level 1 (Default): App-managed wallet
  → User creates account with phone number + PIN
  → Wallet is custodial (app holds keys in secure enclave)
  → No user-facing wallet concepts
  → DAO voting is just "tap to vote"

Level 2 (Optional): Link external wallet
  → "Connect Wallet" in settings
  → WalletConnect v2 protocol (most universal)
  → Links existing MetaMask/Trust Wallet
  → For users who want self-custody

Level 3 (Power user): Full wallet management
  → Import/export seed phrase
  → Direct contract interaction
  → Token management
```

### 3.2 Technical Wallet Architecture

```
┌─────────────────────────────────────┐
│           Flutter App               │
├─────────────────────────────────────┤
│  WalletAbstraction Layer            │
│  ├── CustodialWalletService         │
│  │   ├── Phone+PIN auth             │
│  │   ├── Secure key storage         │
│  │   └── Transaction proxy          │
│  ├── WalletConnectBridge            │
│  │   ├── WC v2 session management   │
│  │   ├── QR code scanning           │
│  │   └── Transaction relay          │
│  └── TransactionBuilder             │
│      ├── ABI encoding               │
│      ├── Gas estimation             │
│      └── Nonce management           │
├─────────────────────────────────────┤
│  Blockchain Layer                   │
│  ├── RPC Provider (L2 chain)        │
│  ├── Contract ABIs                  │
│  └── Event listeners                │
└─────────────────────────────────────┘
```

### 3.3 Recommended Packages

| Package | Purpose | Weight |
|---------|---------|--------|
| `walletconnect_flutter_v2` | WalletConnect v2 protocol | ~2MB |
| `web3dart` | Ethereum-compatible contract calls | ~1.5MB |
| `flutter_secure_storage` | Key storage for custodial wallet | ~200KB |
| `ethers` or `dart_ethers` | Transaction signing, ABI encoding | ~3MB |

**Total added APK size: ~7MB** — acceptable for target devices.

### 3.4 Offline Wallet Considerations

- **Custodial wallet:** Sign transactions server-side when online. Queue unsigned transactions offline.
- **External wallet:** Transactions MUST be online (wallet app needs to sign). Queue intent offline, prompt signing when connected.
- **Critical design rule:** Never expose seed phrases or private keys in the UI flow. For Level 1 users, the wallet should be invisible — they vote, the app handles the rest.

---

## 4. DAO GOVERNANCE INTERFACE DESIGN

### 4.1 Information Architecture

```
Bottom Navigation Bar (4 tabs):
├── 🏠 Home
│   ├── Welcome banner (localized)
│   ├── Active proposal card (if any)
│   ├── Quick actions (Vote, View Treasury, Report Activity)
│   └── Recent activity feed
│
├── 🗳️ Govern
│   ├── Active Proposals list
│   │   ├── Proposal card (title, description preview, vote count, deadline)
│   │   ├── Vote buttons (Yes / No / Abstain) — large touch targets
│   │   └── Tap to expand → full details + discussion
│   ├── Past Proposals (completed)
│   ├── Create Proposal (for authorized members)
│   │   ├── Simple form: Title + Description + Type
│   │   ├── Type selector: Budget / Policy / Mineral Rights / Election
│   │   ├── Voice-to-text for description (critical for non-readers)
│   │   └── Submit → queued if offline
│   └── My Delegation status
│
├── 💰 Treasury
│   ├── Community Balance (large, prominent)
│   ├── Your Share (calculated from membership)
│   ├── Revenue Sources breakdown
│   │   ├── Royalty payments (from mineral sales)
│   │   ├── DAO treasury income
│   │   └── Grant funding
│   ├── Recent Disbursements list
│   ├── Pending Payments
│   └── Export/Share statement
│
└── 👥 Community
    ├── Members count + list
    ├── Mineral Extraction Feed
    │   ├── Who extracted what, where, when
    │   ├── Verification status
    │   └── Photo evidence
    ├── Community Stats dashboard
    │   ├── Total minerals extracted (this month)
    │   ├── Total royalties collected
    │   ├── Active proposals
    │   └── Voter participation rate
    └── Discussion forum (lightweight)
```

### 4.2 Voting Interface Design

**Design principles for low-literacy, low-tech users:**

1. **Visual voting** — Use colored buttons with icons, not just text
2. **Large touch targets** — Minimum 64dp height for all interactive elements
3. **Confirmation step** — "You are voting YES on [proposal title]. Confirm?" with large Yes/No
4. **Visual feedback** — Green checkmark animation on successful vote
5. **Offline voting** — Queue vote locally, show "Vote saved — will submit when connected"
6. **Voice option** — Microphone button to read proposal aloud in selected language

**Vote card wireframe:**
```
┌──────────────────────────────────────┐
│ 📋 Proposal #12                      │
│ "Build new water point near Site A"  │
│                                      │
│ Type: Budget · Amount: 50,000 KES    │
│ Submitted by: Mama Wanjiku           │
│ Deadline: Aug 10, 2026               │
│                                      │
│ Current: ✅ 45 Yes · ❌ 12 No       │
│          🟡 3 Abstain                │
│                                      │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│ │  ✅ YES │ │  ❌ NO  │ │ 🟡 SKIP │ │
│ │  (Green) │ │  (Red)  │ │ (Grey)  │ │
│ └─────────┘ └─────────┘ └─────────┘ │
│                                      │
│ [▶ Listen to proposal]               │
│ [💬 8 comments]                      │
└──────────────────────────────────────┘
```

### 4.3 Delegation Interface

Many community members will want to delegate their voting power to trusted leaders (chiefs, elders, mining cooperative heads).

```
┌──────────────────────────────────────┐
│ 🤝 My Delegation                     │
│                                      │
│ Status: Delegated to Chief Omondi    │
│ Since: July 15, 2026                 │
│ Votes cast by delegate: 3            │
│                                      │
│ [Change Delegate]                    │
│ [Reclaim My Vote]                    │
│                                      │
│ ─────────────────────────────────── │
│                                      │
│ Available Delegates:                 │
│ ┌─────────────────────────────────┐ │
│ │ 👤 Chief Omondi                 │ │
│ │    Mining cooperative leader    │ │
│ │    Votes cast: 12 · Trusted by: │ │
│ │    34 members                   │ │
│ │    [Delegate to this person]    │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ 👤 Mama Wanjiku                 │ │
│ │    Women's mining group chair   │ │
│ │    Votes cast: 8 · Trusted by:  │ │
│ │    21 members                   │ │
│ │    [Delegate to this person]    │ │
│ └─────────────────────────────────┘ │
└──────────────────────────────────────┘
```

---

## 5. COMMUNITY DASHBOARD DESIGN

### 5.1 Mineral Extraction Tracking

```
┌──────────────────────────────────────┐
│ ⛏️ Extraction Activity               │
│ ─────────────────────────────────── │
│ This Month: 23 extractions logged    │
│ Minerals: Gold (15), Copper (5),     │
│           Rare Earth (3)             │
│                                      │
│ Recent:                              │
│ ┌─────────────────────────────────┐ │
│ │ 📷 John Otieno                  │ │
│ │ Gold · Site A · 2 Aug 2026      │ │
│ │ Verified: ✅                     │ │
│ │ [View photo] [View location]    │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ 📷 Amina Hassan                 │ │
│ │ Copper · Site B · 1 Aug 2026    │ │
│ │ Verified: ⏳ Pending            │ │
│ │ [View photo] [View location]    │ │
│ └─────────────────────────────────┘ │
└──────────────────────────────────────┘
```

### 5.2 Royalty Payments View

```
┌──────────────────────────────────────┐
│ 💵 Royalty Payments                  │
│ ─────────────────────────────────── │
│                                      │
│ Total Collected (this quarter):      │
│ KES 2,450,000                        │
│                                      │
│ Breakdown:                           │
│ Gold royalties:    KES 1,800,000     │
│ Copper royalties:  KES   450,000     │
│ Other:             KES   200,000     │
│                                      │
│ Your Share: KES 12,500               │
│ (Based on 0.5% community stake)     │
│                                      │
│ ─────────────────────────────────── │
│ Recent Payments:                     │
│ 📅 1 Aug → KES 450,000 (Gold sale)  │
│ 📅 28 Jul → KES 120,000 (Copper)    │
│ 📅 15 Jul → KES 800,000 (Gold)      │
│                                      │
│ [Download Statement PDF]             │
└──────────────────────────────────────┘
```

### 5.3 Home Screen Redesign

```
┌──────────────────────────────────────┐
│ 🏠 Karibu, Mama Wanjiku!             │
│ ─────────────────────────────────── │
│                                      │
│ ┌─────────────────────────────────┐ │
│ │ 🗳️ VOTE NOW                    │ │
│ │ "Build water point near Site A" │ │
│ │ 2 days left · 45 have voted     │ │
│ │ [Vote Now →]                    │ │
│ └─────────────────────────────────┘ │
│                                      │
│ ┌────────────┐ ┌────────────┐       │
│ │ 💰 Your    │ │ ⛏️ Your    │       │
│ │ Share:     │ │ Activity:  │       │
│ │ KES 12,500 │ │ 3 logs     │       │
│ └────────────┘ └────────────┘       │
│                                      │
│ Recent Activity:                     │
│ • New proposal submitted (2h ago)    │
│ • Gold price: KES 8,200/g (+2.1%)   │
│ • 5 new extractions logged today     │
│                                      │
│ ─────────────────────────────────── │
│ [🏠] [🗳️] [💰] [👥]                │
│ Home Govern Treasury Community       │
└──────────────────────────────────────┘
```

---

## 6. CHEAP ANDROID PHONE ASSESSMENT

### 6.1 Target Device Profile

| Spec | Typical Device | Impact |
|------|---------------|--------|
| RAM | 1-2 GB | App must stay under 150MB runtime |
| Storage | 16-32 GB (5-10 GB free) | APK under 30MB, local DB under 50MB |
| CPU | MediaTek Helio A22 / Snapdragon 450 | No heavy computation on-device |
| Screen | 5-6", 720p | Large fonts, high contrast, no tiny elements |
| Android | 8.1 - 10 (API 27-29) | Must test on these versions |
| Data | Safaricom bundles, 1-5GB/month | Every byte counts |
| Battery | 3000-4000 mAh | Minimize background processes |

### 6.2 Current App Assessment

| Factor | Rating | Notes |
|--------|--------|-------|
| APK size | ✅ Good | Current deps are lightweight (~15MB estimated) |
| Memory usage | ⚠️ Moderate | SQLite + camera + image in memory can spike |
| Data efficiency | ❌ Poor | No image compression, no data caching, no request batching |
| Battery impact | ⚠️ Unknown | GPS + camera + periodic sync = potential drain |
| UI performance | ✅ Good | Simple Material Design, no heavy animations |
| Accessibility | ❌ Poor | No large-text mode, no voice guidance, no high-contrast mode |

### 6.3 Required Optimizations

1. **Image compression:** Compress photos to <200KB before upload (currently `maxWidth: 1920` is too large)
2. **Data caching:** Cache price data locally, only fetch on explicit refresh
3. **Request batching:** Bundle pending sync items into single API calls
4. **Background sync:** Use WorkManager instead of Timer.periodic for battery efficiency
5. **Progressive loading:** Load UI skeleton first, fetch data in background
6. **Font scaling:** Respect system font size, default to large
7. **High contrast mode:** Essential for outdoor use in sunlight
8. **Voice guidance:** Audio prompts for each action ("Tap the green button to vote YES")

---

## 7. OFFLINE-FIRST DAO ARCHITECTURE

### 7.1 Sync Model Redesign

The current sync model (push-only, no conflict resolution) is insufficient for DAO governance. Voting requires **exactly-once semantics** — a vote must not be counted twice, and must not be lost.

```
┌─────────────────────────────────────────────┐
│              OFFLINE-FIRST ARCHITECTURE      │
├─────────────────────────────────────────────┤
│                                             │
│  LOCAL STATE (SQLite)                       │
│  ├── Proposals (read cache)                 │
│  │   ├── id, title, description, type       │
│  │   ├── vote_counts (cached from server)   │
│  │   ├── deadline, status                   │
│  │   └── last_updated timestamp             │
│  ├── My Votes (write-ahead log)             │
│  │   ├── proposal_id, choice                │
│  │   ├── timestamp, signature               │
│  │   └── sync_status: pending/confirmed/    │
│  │       rejected                           │
│  ├── Delegations (read + write cache)       │
│  │   ├── delegate_address, active           │
│  │   └── sync_status                        │
│  ├── Treasury Events (read cache)           │
│  │   ├── type, amount, timestamp            │
│  │   └── last_updated                       │
│  └── Sync Queue                             │
│      ├── action_type, payload, signature    │
│      ├── retry_count, last_error            │
│      └── created_at                         │
│                                             │
│  SYNC ENGINE                                │
│  ├── Conflict Resolution: Last-Writer-Wins  │
│  │   with server-side validation            │
│  ├── Vote Dedup: proposal_id + voter_addr   │
│  │   is unique constraint                   │
│  ├── Retry Policy: Exponential backoff      │
│  │   (1min → 5min → 30min → 2hr)           │
│  ├── Batch Sync: Bundle up to 50 items      │
│  │   per request                            │
│  └── Delta Sync: Only fetch changes since   │
│      last_sync timestamp                    │
│                                             │
└─────────────────────────────────────────────┘
```

### 7.2 Vote Integrity

```
VOTE FLOW (Offline → Online):

1. User taps "YES" on proposal
2. App creates vote record locally:
   {proposal_id: 12, choice: "yes", timestamp: now, 
    voter: local_wallet_address, 
    signature: sign(proposal_id + choice + timestamp, private_key)}
3. Vote saved to SQLite with sync_status: "pending"
4. UI shows "✅ Vote saved — will submit when connected"
5. When online, sync engine:
   a. Reads pending votes from queue
   b. Submits to smart contract via API
   c. Receives transaction hash
   d. Updates sync_status to "confirmed"
   e. If duplicate detected (already voted on-chain), marks "rejected"
      and shows "You already voted on this proposal"
```

---

## 8. IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Weeks 1-3)
- [ ] Add all 4+1 languages to `AppLocalizations` runtime
- [ ] Fix settings screen to show all 5 languages
- [ ] Add Luhya and Kamba to settings language picker
- [ ] Review and fix machine-translated localization entries with native speakers
- [ ] Implement image compression (resize to max 800px, quality 70%)
- [ ] Add local caching for price data
- [ ] Replace `Timer.periodic` with `workmanager` for background sync

### Phase 2: Wallet & Identity (Weeks 4-6)
- [ ] Implement custodial wallet (phone+PIN auth, secure key storage)
- [ ] Add WalletConnect v2 bridge for external wallet linking
- [ ] Create membership verification flow (community invite code or token-gate)
- [ ] Design and implement onboarding flow ("What is this app? What is a DAO?")

### Phase 3: Governance Core (Weeks 7-10)
- [ ] Add proposal browsing, detail view, voting UI
- [ ] Implement offline vote queue with deduplication
- [ ] Add delegation management screen
- [ ] Create proposal creation form (with voice-to-text)
- [ ] Wire up smart contract calls for vote submission

### Phase 4: Treasury & Community (Weeks 11-14)
- [ ] Build treasury dashboard (balance, revenue breakdown, disbursements)
- [ ] Add royalty payment tracking and personal share calculation
- [ ] Create extraction activity feed
- [ ] Build community stats dashboard
- [ ] Add discussion/comment system for proposals

### Phase 5: Polish & Accessibility (Weeks 15-16)
- [ ] High-contrast mode for outdoor visibility
- [ ] Voice guidance system (audio prompts in all 5 languages)
- [ ] Large-text mode (minimum 18sp body text)
- [ ] Iconography audit — ensure all actions have clear icons
- [ ] Battery optimization (reduce background processes)
- [ ] Test on actual cheap Android devices (Tecno Spark, Samsung A03)

---

## 9. CRITICAL FINDINGS & RECOMMENDATIONS

### 9.1 What Works

1. **Localization foundation is solid** — 4 language files exist with 65+ keys each. The framework is right; it needs expansion, not replacement.
2. **Offline sync architecture exists** — The pattern (SQLite + connectivity listener + periodic sync) is correct. It needs sophistication, not replacement.
3. **Material Design 3 is appropriate** — Clean, readable, works on cheap screens.
4. **Swahili as default is correct** — Right call for the target audience.
5. **Small dependency footprint** — Current APK will be under 20MB, good for limited storage.

### 9.2 What Must Change

1. **No blockchain/Web3 capability exists.** This is the biggest gap. The app has zero wallet, zero contract interaction, zero transaction signing. This is a greenfield build.
2. **The `AppLocalizations` class hardcodes only 3 languages.** The ARB files for Luhya and Kamba exist but are not loaded at runtime. This is a bug.
3. **No DAO governance concepts exist anywhere.** No models, no screens, no services. The entire governance layer is new.
4. **The sync model is too simple for voting.** One-way push with no deduplication or conflict resolution will cause double-votes or lost votes.
5. **No accessibility features.** No large text, no voice, no high contrast. For outdoor miners with aging eyes, this is a barrier.
6. **No onboarding.** First-time users see "Identify Mineral" — they won't understand DAO governance without education.

### 9.3 Top 5 Recommendations

| # | Recommendation | Impact | Effort |
|---|---------------|--------|--------|
| 1 | **Build custodial wallet first** — let users vote without understanding crypto | Removes #1 barrier to adoption | Medium |
| 2 | **Offline vote queue with deduplication** — governance integrity depends on this | Prevents vote fraud/loss | High |
| 3 | **Voice-first governance** — audio proposals, voice-to-text creation, spoken results | Bridges literacy gap | Medium |
| 4 | **Add all 5 languages to runtime** — fix the Luhya/Kamba loading bug immediately | Prevents 40% of users being excluded | Low |
| 5 | **Test on actual cheap phones** — Tecno Spark Go, Samsung A03, itel A27 | Catches real-world issues | Low |

### 9.4 Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Users confuse DAO voting with scam apps | High | Critical | Onboarding education, trusted chief endorsement |
| Double-voting due to sync bugs | Medium | Critical | On-chain dedup, client-side queue with unique constraints |
| App too slow on 1GB RAM devices | Medium | High | Memory profiling, image caching, lazy loading |
| Users lose custodial wallet access (phone lost/stolen) | Medium | High | Social recovery via community elders |
| Low voter turnout due to poor UX | High | High | One-tap voting, push notifications, delegation |
| Localization quality insufficient for governance concepts | Medium | Medium | Native speaker review for all DAO-related terms |

---

## 10. CONCLUSION

The existing Flutter app is a **solid mineral identification tool** with good localization scaffolding and basic offline capability. However, it is **not a DAO governance app** — it lacks wallet integration, voting mechanisms, treasury views, and community features entirely.

The transformation is feasible but substantial. The critical path is:
1. Fix the localization bug (Luhya/Kamba not loading) — **do this first, it's a 1-hour fix**
2. Build the custodial wallet layer — **this unblocks everything else**
3. Build the offline vote queue — **this ensures governance integrity**
4. Then iterate on governance UI, treasury, and community features

The app's existing strengths (offline-first design, Swahili default, Material Design 3, lightweight dependencies) provide a good foundation. The main challenge is building an entirely new blockchain interaction layer and governance UX on top of a tool designed for a different purpose.

**Estimated total effort: 16 weeks for a 2-person Flutter + Solidity team.**

---

*Council 7 — Mobile App & Community Interface*
*Analysis complete.*
