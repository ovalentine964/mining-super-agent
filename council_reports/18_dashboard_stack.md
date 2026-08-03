# Council Report #18 — Dashboard Technology Stack Decision

**Date:** 2026-08-03  
**Subject:** Technology Stack Recommendation for Sovereign Resource DAO Dashboard  
**Requested by:** Valentine  
**Status:** FINAL RECOMMENDATION DELIVERED

---

## 1. Current State Analysis

### What We Have Today

The dashboard is a **vanilla JavaScript** application consisting of three files:

| File | Size | Purpose |
|------|------|---------|
| `dashboard.html` | ~180 lines | Semantic HTML structure with i18n data attributes |
| `dashboard.js` | ~520 lines | Data fetching, rendering, auto-refresh, i18n |
| `dashboard.css` | ~520 lines | Mobile-first responsive design, dark theme |

### Current Architecture

```
Browser (Vanilla JS)
  └─ Polling (fetch API, 30s interval)
       └─ FastAPI Backend (Python)
            ├─ /api/v1/prices/{commodity}
            ├─ /api/v1/extractions
            ├─ /api/v1/royalties
            ├─ /api/v1/satellite/latest
            ├─ /dao/stats
            ├─ /dao/proposals
            ├─ /fair-deal/valentine
            └─ /chain/status
```

### Current Strengths
- ✅ Zero dependencies (no build step, no npm)
- ✅ ~3 files, easily understood
- ✅ Bilingual (EN/SW) built-in
- ✅ Mobile-responsive CSS
- ✅ Skeleton loaders and error handling
- ✅ Embed mode support (`?embed=1`)

### Current Weaknesses
- ❌ No type safety — runtime bugs from API shape mismatches
- ❌ No charts — just raw numbers and tables
- ❌ Manual DOM manipulation — brittle at scale
- ❌ Polling only — no real-time WebSocket updates
- ❌ No component reuse — copy-paste HTML templates
- ❌ No tests — impossible to unit test inline DOM code
- ❌ No offline support / PWA capabilities

---

## 2. Option Analysis

### Option A: Vanilla JavaScript (Current) ⭐⭐

**What it is:** Continue with the current approach. Plain HTML/CSS/JS, no build tools.

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Real-time (WebSocket) | ⚠️ Manual | Need to hand-code WebSocket reconnection, backoff |
| Chart libraries | ✅ Good | Chart.js, D3, ECharts all work via CDN |
| Mobile responsiveness | ✅ Already done | Current CSS is mobile-first |
| FastAPI connection | ✅ Already works | Fetch API with CORS |
| Polygon blockchain | ⚠️ Limited | ethers.js via CDN works, but complex contract interaction gets messy |
| Community contribution | ⚠️ Medium | Easy to start, hard to maintain — no contracts between components |
| Deployment | ✅ Trivial | Static files, any web server or CDN |

**Verdict:** Works for MVP. Does not scale past ~1000 lines without pain.

---

### Option B: TypeScript + React ⭐⭐⭐⭐

**What it is:** Component-based UI with type safety. Build step required (Vite).

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Real-time (WebSocket) | ✅ Excellent | `react-query` + WebSocket integration, SWR, or custom hooks |
| Chart libraries | ✅ Excellent | Recharts, Victory, Nivo — all React-native |
| Mobile responsiveness | ✅ Good | CSS-in-JS or Tailwind, same responsive patterns |
| FastAPI connection | ✅ Excellent | Typed API clients with `openapi-typescript-codegen` — auto-generate types from FastAPI's OpenAPI spec |
| Polygon blockchain | ✅ Excellent | wagmi + viem — best-in-class React hooks for Ethereum/Polygon |
| Community contribution | ✅ High | Most web devs know React; massive ecosystem |
| Deployment | ✅ Simple | `vite build` → static files → CDN/Vercel/Netlify |

**Key advantages:**
- Auto-generate TypeScript types from FastAPI's OpenAPI schema — zero drift between backend and frontend
- React Query for intelligent caching, deduplication, and background refetch (replaces manual 30s polling)
- Component library: shadcn/ui, Radix, or Chakra for accessible components out of the box
- wagmi + viem for Polygon wallet connection, contract reads/writes
- Huge talent pool for community contributions

**Verdict:** Best balance of power and accessibility.

---

### Option C: TypeScript + Next.js ⭐⭐⭐

**What it is:** React framework with SSR, API routes, file-based routing.

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Real-time (WebSocket) | ✅ Good | Same as React, but SSR complicates client-only WebSockets |
| Chart libraries | ✅ Excellent | Same as React |
| Mobile responsiveness | ✅ Good | Same as React |
| FastAPI connection | ⚠️ Overkill | API routes duplicate FastAPI — creates confusion about "source of truth" |
| Polygon blockchain | ⚠️ Complex | Server-side rendering + wallet connections = hydration headaches |
| Community contribution | ✅ High | Popular framework |
| Deployment | ⚠️ Medium | Needs Node.js server (Vercel easy, self-hosted harder) |

**Key concern:** We already have a FastAPI backend. Next.js API routes would create a second backend layer that adds complexity without benefit. The SSR advantage (SEO, initial load) matters for content sites, not for a real-time dashboard that refreshes every 30 seconds.

**Verdict:** Over-engineered for our use case. Adds server complexity we don't need.

---

### Option D: Rust + WebAssembly ⭐⭐

**What it is:** Compile Rust to WASM for browser execution. Use frameworks like Yew, Leptos, or Dioxus.

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Real-time (WebSocket) | ⚠️ Possible | wasm-bindgen supports WebSockets, but ecosystem immature |
| Chart libraries | ❌ Poor | No mature Rust/WASM chart library; must call JS interop |
| Mobile responsiveness | ⚠️ Manual | No mature responsive component libraries |
| FastAPI connection | ⚠️ Complex | HTTP from WASM requires JS interop or wasm-bindgen fetch |
| Polygon blockchain | ❌ Very Hard | No wagmi/viem equivalent in Rust/WASM |
| Community contribution | ❌ Very Low | Rust+WASM is niche; few DAO community members will know it |
| Deployment | ✅ Good | Static WASM + JS glue, any CDN |

**Verdict:** Maximum performance for the wrong problem. Our bottleneck is network latency (API calls to FastAPI), not rendering. WASM solves a problem we don't have while creating many we didn't have.

---

### Option E: Python + Dash/Streamlit ⭐⭐

**What it is:** Python-native dashboard frameworks. Dash (Plotly) or Streamlit.

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Real-time (WebSocket) | ⚠️ Limited | Dash has `dcc.Interval` polling; Streamlit requires `st.rerun()` |
| Chart libraries | ✅ Excellent | Plotly (Dash) is world-class for data viz |
| Mobile responsiveness | ⚠️ Basic | Dash: manual CSS. Streamlit: limited layout control |
| FastAPI connection | ✅ Direct | Python-to-Python, no API boundary needed |
| Polygon blockchain | ❌ Poor | Web3.py exists but browser wallet integration impossible |
| Community contribution | ✅ High for data scientists | Low for web developers |
| Deployment | ⚠️ Medium | Needs a Python server, not static files |

**Key concern:** Dash/Streamlit dashboards are server-rendered. Every interaction round-trips to the server. For a real-time community dashboard that needs wallet connections and WebSocket updates, this is the wrong paradigm. Also, it cannot be embedded as a static widget in other sites.

**Verdict:** Great for internal analytics. Wrong for a community-facing, embeddable, real-time dashboard.

---

### Option F: TypeScript + Svelte ⭐⭐⭐

**What it is:** Compile-time reactive framework. Less boilerplate than React.

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Real-time (WebSocket) | ✅ Excellent | Svelte stores + native WebSocket, very clean |
| Chart libraries | ✅ Good | LayerChart, Chart.js wrappers; smaller ecosystem than React |
| Mobile responsiveness | ✅ Good | Same CSS approaches as React |
| FastAPI connection | ✅ Good | Typed fetch, but no OpenAPI codegen ecosystem like React |
| Polygon blockchain | ⚠️ Limited | No wagmi equivalent; need manual ethers.js/viem integration |
| Community contribution | ⚠️ Medium | Growing but much smaller than React; fewer contributors will know it |
| Deployment | ✅ Simple | `vite build` → static files |

**Key advantage:** Svelte produces smaller bundles and has simpler mental model. The code would be more concise.

**Key disadvantage:** Smaller ecosystem means less tooling for blockchain integration (no wagmi), fewer component libraries, and harder community onboarding.

**Verdict:** Technically excellent but ecosystem gap for our blockchain needs.

---

## 3. Comparison Matrix

| Criterion | A. Vanilla | B. React | C. Next.js | D. Rust/WASM | E. Python | F. Svelte |
|-----------|:----------:|:--------:|:----------:|:------------:|:---------:|:---------:|
| WebSocket support | ⚠️ | ✅✅ | ✅ | ⚠️ | ⚠️ | ✅✅ |
| Chart libraries | ✅ | ✅✅ | ✅✅ | ❌ | ✅✅ | ✅ |
| Mobile responsive | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ |
| FastAPI integration | ✅ | ✅✅ | ⚠️ | ⚠️ | ✅✅ | ✅ |
| Polygon blockchain | ⚠️ | ✅✅ | ⚠️ | ❌ | ❌ | ⚠️ |
| Community contrib | ⚠️ | ✅✅ | ✅ | ❌ | ✅ | ⚠️ |
| Deployment ease | ✅✅ | ✅ | ⚠️ | ✅ | ⚠️ | ✅ |
| Bundle size | ✅✅ | ✅ | ⚠️ | ✅ | N/A | ✅✅ |
| Type safety | ❌ | ✅✅ | ✅✅ | ✅✅ | ⚠️ | ✅✅ |
| Testing | ❌ | ✅✅ | ✅✅ | ✅ | ⚠️ | ✅✅ |

**Legend:** ✅✅ Excellent | ✅ Good | ⚠️ Adequate/Compromise | ❌ Poor

---

## 4. FINAL RECOMMENDATION: TypeScript + React (Option B)

### The Decision

**We recommend TypeScript + React with Vite as the build tool.**

### Why React Wins

#### 1. Auto-Generated Types from FastAPI

FastAPI natively generates OpenAPI schemas. With `openapi-typescript`, we can auto-generate TypeScript interfaces from our backend:

```bash
npx openapi-typescript http://localhost:8000/openapi.json -o src/api/types.ts
```

This means **zero drift** between backend and frontend. When a backend developer adds a field to `/api/v1/prices/gold`, the frontend gets a type error if it doesn't handle it. This is critical for a project with multiple contributors.

#### 2. Best-in-Class Blockchain Integration

The `wagmi` + `viem` library pair is purpose-built for React:
- Wallet connection (MetaMask, WalletConnect)
- Contract reads (on-chain proposal data, voting power)
- Transaction writing (cast votes, create proposals)
- Real-time event listening (new blocks, contract events)

No other framework has anything close.

#### 3. React Query Replaces Manual Polling

The current 30-second `setInterval` polling gets replaced by React Query:

```typescript
// Before (vanilla JS): manual polling
setInterval(() => fetchPrices(), 30000);

// After (React Query): intelligent refetching
const { data } = useQuery({
  queryKey: ['prices', commodity],
  queryFn: () => api.prices.get(commodity),
  refetchInterval: 30_000,
  staleTime: 15_000,
});
```

React Query handles: caching, deduplication, background refetch, retry on failure, optimistic updates — all out of the box.

#### 4. Component Library Ready

`shadcn/ui` (built on Radix) gives us accessible, themeable components:
- Data tables with sorting/filtering (extraction records, royalties)
- Charts (Recharts for price history, fairness trends)
- Tabs, dialogs, tooltips
- All customizable, all TypeScript-first

#### 5. Massive Community

- 220k+ GitHub stars
- Largest component ecosystem
- Most DAO dashboards use React (Uniswap, Aave, Compound, ENS)
- Community contributors likely already know it

### Recommended Stack

```
Frontend
├── Framework:     React 19 + TypeScript
├── Build:         Vite 6
├── State:         React Query (TanStack Query)
├── Routing:       React Router (if multi-page needed later)
├── Blockchain:    wagmi + viem
├── Charts:        Recharts or Nivo
├── UI Components: shadcn/ui (Radix primitives)
├── Styling:       Tailwind CSS
├── Forms:         React Hook Form + Zod validation
├── Testing:       Vitest + React Testing Library
└── Linting:       ESLint + Prettier

Backend (unchanged)
├── Framework:     FastAPI (Python)
├── API:           REST + WebSocket endpoints
├── Blockchain:    Polygon via web3.py
└── AI:            NVIDIA NIM API
```

### Project Structure

```
sovereign-resource-dao/
├── src/                    # FastAPI backend (existing)
├── website/
│   ├── dashboard.html      # Current (to be archived)
│   ├── dashboard.js        # Current (to be archived)
│   └── dashboard.css       # Current (to be archived)
└── dashboard/              # NEW: React dashboard
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── tailwind.config.ts
    ├── public/
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── api/
    │   │   ├── client.ts        # API client with base URL config
    │   │   ├── types.ts         # Auto-generated from OpenAPI
    │   │   └── hooks/
    │   │       ├── usePrices.ts
    │   │       ├── useStats.ts
    │   │       ├── useExtractions.ts
    │   │       ├── useProposals.ts
    │   │       └── useSatellite.ts
    │   ├── components/
    │   │   ├── layout/
    │   │   │   ├── Header.tsx
    │   │   │   ├── Footer.tsx
    │   │   │   └── ErrorBanner.tsx
    │   │   ├── prices/
    │   │   │   ├── PriceCard.tsx
    │   │   │   └── PriceGrid.tsx
    │   │   ├── stats/
    │   │   │   └── KPICards.tsx
    │   │   ├── fairness/
    │   │   │   └── FairnessGauge.tsx
    │   │   ├── governance/
    │   │   │   ├── ProposalCard.tsx
    │   │   │   └── ProposalList.tsx
    │   │   ├── extractions/
    │   │   │   └── ExtractionTable.tsx
    │   │   ├── royalties/
    │   │   │   └── RoyaltyList.tsx
    │   │   ├── satellite/
    │   │   │   └── SatellitePanel.tsx
    │   │   └── blockchain/
    │   │       └── ChainStatus.tsx
    │   ├── hooks/
    │   │   ├── useWebSocket.ts    # Real-time updates
    │   │   ├── useLanguage.ts     # i18n hook
    │   │   └── useWallet.ts       # Polygon wallet
    │   ├── i18n/
    │   │   ├── en.json
    │   │   └── sw.json
    │   └── lib/
    │       ├── utils.ts
    │       └── constants.ts
    └── tests/
```

---

## 5. Architecture Diagram

### How the Dashboard Connects to Everything

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER'S BROWSER                           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           React Dashboard (TypeScript + Vite)            │  │
│  │                                                          │  │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐ │  │
│  │  │ Prices  │ │Governance│ │ Satellite│ │  Fairness   │ │  │
│  │  │  Cards  │ │ Proposals│ │  Panel   │ │   Gauge     │ │  │
│  │  └────┬────┘ └────┬─────┘ └────┬─────┘ └──────┬──────┘ │  │
│  │       │           │            │              │          │  │
│  │  ┌────┴───────────┴────────────┴──────────────┴──────┐  │  │
│  │  │            React Query (TanStack Query)           │  │  │
│  │  │  · Cache  · Dedup  · Retry  · Background Refresh │  │  │
│  │  └────────────────────┬──────────────────────────────┘  │  │
│  │                       │                                  │  │
│  │  ┌────────────────────┴──────────────────────────────┐  │  │
│  │  │              wagmi + viem (Blockchain)             │  │  │
│  │  │  · Wallet Connect  · Contract Read  · Events      │  │  │
│  │  └────────────────────┬──────────────────────────────┘  │  │
│  │                       │                                  │  │
│  │  ┌────────────────────┴──────────────────────────────┐  │  │
│  │  │              WebSocket Client                      │  │  │
│  │  │  · Auto-reconnect  · Backoff  · Event dispatch    │  │  │
│  │  └───────────┬────────────────────────┬──────────────┘  │  │
│  └──────────────┼────────────────────────┼─────────────────┘  │
│                 │                        │                      │
└─────────────────┼────────────────────────┼──────────────────────┘
                  │                        │
          HTTPS/REST                 WSS (WebSocket)
                  │                        │
┌─────────────────┼────────────────────────┼──────────────────────┐
│                 ▼                        ▼                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              FastAPI Backend (Python)                     │  │
│  │                                                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │  │
│  │  │ Price API    │  │ DAO Engine   │  │ Fair Deal     │  │  │
│  │  │ /api/v1/     │  │ /dao/        │  │ Calculator    │  │  │
│  │  │ prices/*     │  │ stats        │  │ /fair-deal/   │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │  │
│  │         │                 │                   │          │  │
│  │  ┌──────┴───────┐  ┌─────┴────────┐  ┌──────┴───────┐  │  │
│  │  │ Extraction   │  │ Governance   │  │  Satellite   │  │  │
│  │  │ Records      │  │ Proposals    │  │  Monitoring  │  │  │
│  │  │ /api/v1/     │  │ /dao/        │  │  /api/v1/    │  │  │
│  │  │ extractions  │  │ proposals    │  │  satellite/  │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │  │
│  │                                                          │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │         WebSocket Endpoint (/ws/live)             │   │  │
│  │  │  Pushes: price updates, proposal votes, alerts   │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  └──────────┬───────────────────────────────┬──────────────┘  │
│             │                               │                  │
└─────────────┼───────────────────────────────┼──────────────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────┐   ┌──────────────────────────────────┐
│   POLYGON BLOCKCHAIN    │   │         NVIDIA NIM API           │
│                         │   │                                  │
│  ┌───────────────────┐  │   │  ┌────────────────────────────┐ │
│  │  Smart Contracts  │  │   │  │  Mineral Intelligence      │ │
│  │                   │  │   │  │  · Price prediction        │ │
│  │  · DAO Governance │  │   │  │  · Fairness analysis       │ │
│  │  · Voting (Quad)  │  │   │  │  · Satellite image analysis│ │
│  │  · Royalty Split  │  │   │  │  · Extraction validation   │ │
│  │  · Oracle Bridge  │  │   │  └────────────────────────────┘ │
│  └───────────────────┘  │   │                                  │
│                         │   │  ┌────────────────────────────┐ │
│  ┌───────────────────┐  │   │  │  Five Sovereign Agents    │ │
│  │  Oracle Bridge    │  │   │  │  · Sentinel (monitoring)  │ │
│  │  Python ↔ Chain   │  │   │  │  · Auditor (verification) │ │
│  └───────────────────┘  │   │  │  · Advocate (fairness)    │ │
│                         │   │  │  · Oracle (price feeds)   │ │
│  ┌───────────────────┐  │   │  │  · Ambassador (community) │ │
│  │  Token/NFT        │  │   │  └────────────────────────────┘ │
│  │  · ERC-20 DAO     │  │   │                                  │
│  │  · ERC-721 Rights │  │   └──────────────────────────────────┘
│  └───────────────────┘  │
└─────────────────────────┘
```

### Data Flow Summary

| Data Type | Transport | Direction | Frequency |
|-----------|-----------|-----------|-----------|
| Mineral prices | REST + WS push | Backend → Dashboard | Every 30s + on change |
| DAO stats | REST | Backend → Dashboard | Every 30s |
| Proposals/votes | REST + WS push | Backend → Dashboard | Every 30s + on new vote |
| Extraction records | REST | Backend → Dashboard | Every 60s |
| Royalties | REST | Backend → Dashboard | Every 60s |
| Fairness index | REST | Backend → Dashboard | Every 60s |
| Satellite data | REST | Backend → Dashboard | Every 5 min |
| Chain status | REST | Backend → Dashboard | Every 30s |
| Wallet connection | wagmi/viem | Dashboard ↔ Polygon | On user action |
| Contract reads | wagmi/viem | Dashboard → Polygon | On demand |
| Vote transactions | wagmi/viem | Dashboard → Polygon | On user action |

---

## 6. Migration Path

### Phase 1: Scaffold (Week 1)
- Initialize Vite + React + TypeScript project
- Set up Tailwind + shadcn/ui
- Auto-generate API types from FastAPI OpenAPI spec
- Implement React Query data layer

### Phase 2: Port Existing Features (Week 2)
- Migrate all existing sections (prices, stats, extractions, royalties, proposals, fairness, satellite)
- Preserve exact same visual design
- Implement i18n with react-i18next
- Add WebSocket client with auto-reconnect

### Phase 3: Enhance (Week 3)
- Add charts (price history, fairness trends, voting participation)
- Integrate wagmi for Polygon wallet connection
- Add on-chain governance interactions (vote from dashboard)
- PWA support for offline viewing

### Phase 4: Polish (Week 4)
- Testing (Vitest + React Testing Library)
- Accessibility audit (axe-core)
- Performance optimization (code splitting, lazy loading)
- Archive old vanilla JS files

---

## 7. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Bundle size bloat | Vite tree-shaking + code splitting; React is ~40KB gzipped |
| Learning curve for contributors | React is the most-known framework; good docs |
| Over-engineering | Start with just porting existing features; add charts/wallet later |
| Breaking existing embed | Build as static files; same `?embed=1` flag; same CDN deployment |

---

## 8. Why NOT the Others

| Option | Why Not |
|--------|---------|
| **A. Vanilla JS** | No type safety, no component reuse, no tests. Fine for 500 lines; we'll hit 5000+ |
| **C. Next.js** | SSR is wasted on a real-time dashboard. API routes duplicate FastAPI. Adds server complexity |
| **D. Rust/WASM** | No chart libs, no blockchain libs, no community contributors. Solves performance we don't have |
| **E. Python Dash** | Server-rendered, no wallet integration, not embeddable. Wrong paradigm for real-time |
| **F. Svelte** | Great framework, but no wagmi equivalent for Polygon. Smaller ecosystem for our needs |

---

## 9. Conclusion

**TypeScript + React + Vite** is the clear winner because:

1. **Auto-generated types** from FastAPI's OpenAPI schema eliminate backend/frontend drift
2. **wagmi + viem** is the only mature blockchain integration library, and it's React-only
3. **React Query** replaces our manual polling with intelligent caching and background refetch
4. **Largest ecosystem** means community contributors can onboard immediately
5. **Static deployment** keeps our current CDN-based hosting model
6. **The DAO ecosystem uses React** — Uniswap, Aave, Compound, ENS all ship React dashboards

The current vanilla JS served us well for prototyping. It's time to graduate.

---

*Council convened 2026-08-03. Decision: unanimous.*
