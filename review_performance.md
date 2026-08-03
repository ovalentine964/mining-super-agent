# Performance & Scalability Review — Sovereign Resource DAO

**Council:** Performance & Scalability Review  
**Date:** 2026-08-04  
**Scope:** Python backend, Solidity contracts, Flutter mobile app, React dashboard, infrastructure

---

## Executive Summary

The Sovereign Resource DAO is a well-architected multi-layer system spanning Python (FastAPI + AI agents), Solidity (5 contracts on Polygon), Flutter (mobile), and React (dashboard). The codebase demonstrates solid engineering fundamentals — async/await patterns, connection pooling in the HTTP client, caching in the tool registry, and query caching in React. However, several performance bottlenecks and scalability limits exist that will surface under production load. This report identifies **38 findings** across 5 layers, rated by severity.

| Severity | Count |
|----------|-------|
| 🔴 Critical | 6 |
| 🟠 High | 13 |
| 🟡 Medium | 14 |
| 🟢 Low | 5 |

---

## 1. Python Backend Performance

### 🔴 P-1: New `SovereignResourceDAO` Instantiation Per Request

**File:** `src/main.py:53`  
**Impact:** Critical — O(n) tool registration + config loading per API call

```python
# route_channel_message() creates a new agent EVERY request:
from src.superagent import SovereignResourceDAO
agent = SovereignResourceDAO()  # Loads YAML, registers all tools, creates memory
result = await agent.chat(...)
```

The `SovereignResourceDAO.__init__` loads `agent.yaml` from disk, registers all tool handlers (4 modules), creates a `ConversationMemory`, and initializes the tool registry with rate limiters and caches. This is **~5-15ms of pure startup waste per request**.

**Fix:** Make `SovereignResourceDAO` a singleton or initialize once during `lifespan()`:

```python
_agent: SovereignResourceDAO | None = None

async def lifespan(app: FastAPI):
    global _agent
    _agent = SovereignResourceDAO()
    yield
```

### 🔴 P-2: Blocking `wait_for_transaction_receipt` in Async Context

**File:** `src/chain/oracle_bridge.py:105-108`  
**Impact:** Critical — blocks the event loop for up to 120 seconds

```python
receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
```

`web3.py`'s `wait_for_transaction_receipt` is a **synchronous blocking call** wrapped in an `async` method. It will block the entire FastAPI event loop, freezing all concurrent requests for up to 2 minutes.

**Fix:** Use `asyncio.to_thread()` or switch to `web3.py`'s async provider:

```python
import asyncio
receipt = await asyncio.to_thread(
    self._w3.eth.wait_for_transaction_receipt, tx_hash, timeout=120
)
```

### 🔴 P-3: New `httpx.AsyncClient` Per LLM/Tool Call

**File:** `src/superagent.py:190`, `src/api/routes/voice.py:143`, `src/tools/market.py`  
**Impact:** Critical — TCP handshake + TLS negotiation per request

Three separate locations create ephemeral `httpx.AsyncClient` instances:

```python
# superagent.py — LLM calls
async with httpx.AsyncClient(timeout=120.0) as client:
    resp = await client.post(...)

# voice.py — NIM transcription
async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
    resp = await client.post(...)

# market.py — Finnhub/Alpha Vantage
async with httpx.AsyncClient(timeout=15.0) as client:
    resp = await client.get(...)
```

Each creates a new connection pool, performs DNS resolution, TCP handshake, and TLS negotiation. Under load, this wastes **50-200ms per request**.

**Fix:** Create shared clients with connection pooling:

```python
# In superagent.py
class SovereignResourceDAO:
    def __init__(self, ...):
        self._http_client = httpx.AsyncClient(
            timeout=120.0,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
        )

    async def close(self):
        await self._http_client.aclose()
```

### 🟠 P-4: Conversation Memory Unbounded Growth

**File:** `src/superagent.py:41-78`  
**Impact:** High — memory leak under sustained load

`ConversationMemory` stores sessions in a plain `dict` with no eviction:

```python
self._sessions: dict[str, dict[str, Any]] = {}
```

While TTL is checked on `get_history()`, expired sessions are only cleaned when **that specific user** queries again. If 10,000 users send one message each and never return, all 10,000 sessions persist indefinitely.

**Fix:** Add periodic cleanup or use an LRU cache:

```python
from functools import lru_cache
# Or: add a cleanup coroutine that runs every hour
async def _cleanup_expired_sessions(self):
    while True:
        await asyncio.sleep(3600)
        now = time.time()
        expired = [
            uid for uid, s in self._sessions.items()
            if (now - s["created"]) / 3600 > self.ttl_hours
        ]
        for uid in expired:
            del self._sessions[uid]
```

### 🟠 P-5: Synchronous `yfinance` Calls Block Event Loop

**File:** `src/tools/market.py:40-70`  
**Impact:** High — yfinance uses synchronous HTTP internally

```python
async def yfinance_price(commodity, currency):
    ticker = yf.Ticker(symbol)
    info = ticker.info  # BLOCKING — uses requests internally
```

Despite being `async`, this calls `yfinance` which internally uses `requests` (synchronous). This blocks the event loop for 1-5 seconds per price query.

**Fix:** Wrap in `asyncio.to_thread()`:

```python
info = await asyncio.to_thread(lambda: yf.Ticker(symbol).info)
```

### 🟠 P-6: Tool Registry Lock Contention

**File:** `src/tools/registry.py:90-115`  
**Impact:** High — single asyncio.Lock for all cache operations

```python
class CacheManager:
    def __init__(self, config):
        self._lock = asyncio.Lock()
```

Every cache read/write across all tools contends on a single lock. Under concurrent load (e.g., 50 simultaneous agent chats), this serializes all cache access.

**Fix:** Use per-key locking or a lock-free cache (e.g., `cachetools.TTLCache`):

```python
from cachetools import TTLCache
self._entries = TTLCache(maxsize=config.max_entries, ttl=config.ttl_seconds)
```

### 🟡 P-7: No Request Deduplication for LLM Calls

**File:** `src/superagent.py:210-240`  
**Impact:** Medium — identical queries trigger redundant LLM calls

If two users ask "What is gold price?" simultaneously, both trigger full LLM + tool chains independently. No deduplication or request coalescing exists.

**Fix:** Add a simple in-flight request map:

```python
_inflight: dict[str, asyncio.Future] = {}

async def chat(self, user_message, ...):
    key = hashlib.sha256(user_message.encode()).hexdigest()[:16]
    if key in self._inflight:
        return await self._inflight[key]
    future = asyncio.get_event_loop().create_future()
    self._inflight[key] = future
    try:
        result = await self._do_chat(...)
        future.set_result(result)
        return result
    finally:
        self._inflight.pop(key, None)
```

### 🟡 P-8: Governance Engine In-Memory Only

**File:** `src/dao/governance.py`  
**Impact:** Medium — all proposals/votes lost on restart

The `GovernanceEngine` stores everything in Python dicts. A server restart wipes all proposals and votes. Under load, the dict grows without bound.

**Fix:** Add SQLite/Redis backing store and periodic persistence.

### 🟡 P-9: Telegram Bot Session Dict Growth

**File:** `src/channels/telegram_bot.py:126`  
**Impact:** Medium — unbounded session storage

```python
self.sessions: dict[int, UserSession] = {}
```

Sessions are never evicted. Over weeks of operation with thousands of unique chat_ids, this grows indefinitely.

**Fix:** Add TTL-based eviction (e.g., evict sessions older than 24h).

---

## 2. Smart Contract Gas Costs

### 🔴 S-1: Unbounded Array in `ExtractionTracker.recordExtraction`

**File:** `contracts/ExtractionTracker.sol:78`  
**Impact:** Critical — gas cost grows linearly with record count

```solidity
locationRecords[locationHash].push(recordId);
```

`getLocationRecords()` returns a dynamic array that grows without bounds. For popular mining locations with hundreds of records, the array storage cost becomes prohibitive, and the view function may hit gas limits when called off-chain.

**Fix:** Add pagination:

```solidity
function getLocationRecordsPaginated(
    bytes32 locationHash, uint256 offset, uint256 limit
) external view returns (uint256[] memory) {
    uint256[] storage all = locationRecords[locationHash];
    uint256 end = offset + limit > all.length ? all.length : offset + limit;
    uint256[] memory result = new uint256[](end - offset);
    for (uint256 i = offset; i < end; i++) {
        result[i - offset] = all[i];
    }
    return result;
}
```

### 🟠 S-2: `_verifyLocation` Iterates All Submissions

**File:** `contracts/MiningOracle.sol:72-86`  
**Impact:** High — O(n) gas cost per verification

```solidity
function _verifyLocation(bytes32 locationHash) internal {
    OracleSubmission[] storage subs = submissions[locationHash];
    for (uint i = 0; i < subs.length; i++) {
        // ... iterates all submissions
    }
}
```

With `requiredConfirmations = 2`, this loops through all submissions. If many oracles submit before consensus, gas cost scales linearly.

**Fix:** Track running totals incrementally:

```solidity
mapping(bytes32 => uint256) public totalConfidence;

function submitData(...) external {
    // ...
    totalConfidence[locationHash] += confidenceBps;
    if (submissionCount[locationHash] >= requiredConfirmations) {
        uint256 avg = totalConfidence[locationHash] / submissionCount[locationHash];
        locationVerified[locationHash] = true;
        emit LocationVerified(locationHash, submissionCount[locationHash], avg);
    }
}
```

### 🟠 S-3: Soulbound `_beforeTokenTransfer` Overhead

**File:** `contracts/ExtractionTracker.sol:130-138`  
**Impact:** High — adds ~2,000 gas to every mint

```solidity
function _beforeTokenTransfer(...) internal virtual override {
    require(from == address(0) || to == address(0), "Soulbound: non-transferable");
    super._beforeTokenTransfer(from, to, tokenId, batchSize);
}
```

This hook fires on **every** ERC721 transfer (including mint). The `super._beforeTokenTransfer` includes AccessControl checks. For a soulbound token that can never be transferred, consider using a custom `_mint` override that bypasses the transfer hook entirely, or use ERC5484 (soulbound standard).

### 🟡 S-4: `GovernanceToken` Vesting Schedule Gas

**File:** `contracts/GovernanceToken.sol:74-90`  
**Impact:** Medium — `createVesting` mints to `address(this)`, holding tokens in-contract

```solidity
_mint(address(this), amount); // Hold in contract
```

This increases the contract's storage footprint. Each vesting schedule requires persistent storage. With many beneficiaries, the contract's balance grows, and `releaseVested()` does a `_transfer` from contract to user, which is more expensive than a direct mint.

### 🟡 S-5: Quadratic Voting `_sqrt` Implementation

**File:** `contracts/QuadraticVoting.sol:126-134`  
**Impact:** Medium — Babylonian method converges in O(log(log(x))) iterations

The `_sqrt` function uses a while loop. For very large token amounts (e.g., 10^18 * 10^9), this converges in ~6-7 iterations, which is acceptable. However, the `tokens * PRECISION` multiplication before the sqrt could overflow for extremely large values.

**Fix:** Add overflow protection or use OpenZeppelin's `Math.sqrt()`.

### 🟢 S-6: Event Emission Gas Cost

**File:** All contracts  
**Impact:** Low — events are cheap but worth noting

All contracts emit events with string data (e.g., `mineralType`, `notes`). String storage in events costs 375 gas per 32-byte word + 8 gas per byte. For long strings, this adds up. Consider using indexed enums or bytes32 for common values.

---

## 3. Flutter App Performance

### 🔴 F-1: Multiple `setState` Calls in `_stopRecordingAndSend`

**File:** `mobile/flutter/lib/screens/agent_chat_screen.dart:180-220`  
**Impact:** Critical — 4-5 rebuilds per voice message

```dart
setState(() { _messages.add(...); _loading = true; });  // Rebuild 1
// ... transcription ...
setState(() { _messages.last['content'] = ...; });       // Rebuild 2
// ... agent call ...
setState(() { _messages.add(...); });                     // Rebuild 3
setState(() { _loading = false; });                       // Rebuild 4
```

Each `setState` triggers a full widget rebuild. In a voice message flow, the ListView rebuilds 4 times, causing visible jank.

**Fix:** Batch state updates:

```dart
Future<void> _stopRecordingAndSend() async {
    // ... collect all state changes ...
    setState(() {
        _messages.add(userMsg);
        _messages.last['content'] = '🎤 $transcription';
        _messages.add(assistantMsg);
        _loading = false;
    });
}
```

### 🟠 F-2: No Image Caching in PhotoScreen

**File:** `mobile/flutter/lib/screens/photo_screen.dart:30-35`  
**Impact:** High — raw `Image.file` without caching

```dart
Image.file(_image!, height: 300, fit: BoxFit.cover)
```

`Image.file` doesn't cache decoded images. If the user navigates away and back, the image re-decodes from disk. For large mineral photos (4-12MB), this causes a noticeable delay.

**Fix:** Use `cached_network_image` or configure `ImageCache`:

```dart
Image.file(_image!, height: 300, fit: BoxFit.cover,
    cacheWidth: 800, // Decode at display size
)
```

### 🟠 F-3: No ListView.builder Optimization in Chat

**File:** `mobile/flutter/lib/screens/agent_chat_screen.dart:152`  
**Impact:** High — all messages rebuild on every state change

```dart
ListView.builder(
    itemCount: _messages.length,
    itemBuilder: (_, i) => _buildMessage(_messages[i]),
)
```

`_buildMessage` creates new widget subtrees every build. With 50+ messages, this causes frame drops. The `ListView.builder` does lazy-build, but without `addAutomaticKeepAlives: false` and `addRepaintBoundaries: true` (defaults), each item gets a repaint boundary.

**Fix:** Extract messages into a `StatelessWidget` with proper `const` constructors, and add `key` to each item:

```dart
ListView.builder(
    addAutomaticKeepAlives: false,
    itemCount: _messages.length,
    itemBuilder: (_, i) => _MessageBubble(
        key: ValueKey(_messages[i]['time']),
        message: _messages[i],
        isUser: _messages[i]['role'] == 'user',
    ),
)
```

### 🟠 F-4: AudioPlayer Listener Leak

**File:** `mobile/flutter/lib/screens/agent_chat_screen.dart:252`  
**Impact:** High — new listener added per playback, never removed

```dart
_audioPlayer.onPlayerComplete.listen((_) {
    setState(() { _playingAudio = false; });
});
```

Every call to `_playAudio` adds a new stream subscription. After 20 playbacks, 20 listeners fire on completion. The subscriptions are never cancelled.

**Fix:** Store and cancel the subscription:

```dart
StreamSubscription? _playbackSub;

Future<void> _playAudio(String path) async {
    _playbackSub?.cancel();
    // ...
    _playbackSub = _audioPlayer.onPlayerComplete.listen((_) {
        setState(() { _playingAudio = false; });
    });
}

@override
void dispose() {
    _playbackSub?.cancel();
    super.dispose();
}
```

### 🟡 F-5: No Debouncing on DAO Vote Buttons

**File:** `mobile/flutter/lib/screens/dao_screen.dart:130`  
**Impact:** Medium — rapid taps send duplicate votes

```dart
onPressed: () => _vote(proposal['id'], true),
```

No debounce or loading state per proposal. A user tapping rapidly sends multiple POST requests.

**Fix:** Add per-proposal loading state:

```dart
Set<String> _votingProposals = {};

Future<void> _vote(String proposalId, bool support) async {
    if (_votingProposals.contains(proposalId)) return;
    setState(() => _votingProposals.add(proposalId));
    try { /* ... */ }
    finally { setState(() => _votingProposals.remove(proposalId)); }
}
```

### 🟡 F-6: ApiClient Singleton Doesn't Close HTTP Client

**File:** `mobile/flutter/lib/services/api_client.dart:138`  
**Impact:** Medium — connection pool leaks on app lifecycle

`ApiClient` is a singleton with `_httpClient = http.Client()`. The `dispose()` method exists but is never called from any screen. On hot restart or app lifecycle changes, connections may leak.

**Fix:** Register `dispose()` in app lifecycle or use `WidgetsBindingObserver`.

### 🟡 F-7: OfflineSyncService Periodic Timer Never Stops

**File:** `mobile/flutter/lib/services/offline_sync.dart:24`  
**Impact:** Medium — background timer runs indefinitely

```dart
_syncTimer = Timer.periodic(const Duration(minutes: 5), (_) => syncPending());
```

If `stop()` is never called (which it isn't from any screen), the timer runs forever, even when the app is backgrounded. On iOS, this triggers battery warnings.

### 🟢 F-8: PriceScreen Uses Hardcoded Data

**File:** `mobile/flutter/lib/screens/price_screen.dart:21`  
**Impact:** Low — placeholder data, not a real perf issue, but blocks real usage

```dart
_prices = [
    {'name': 'Gold', 'symbol': 'Au', 'price': '2,650.00', ...},
];
```

This is a TODO stub. When real API integration is added, ensure caching and pagination are implemented from the start.

---

## 4. Dashboard (React) Performance

### 🟠 D-1: All 6 Data Hooks Poll at 30s Intervals Simultaneously

**File:** `dashboard/src/hooks/use*.ts`  
**Impact:** High — 6 concurrent API calls every 30 seconds

```typescript
// useExtractions.ts
refetchInterval: 30_000, staleTime: 15_000,

// usePrices.ts
refetchInterval: 30_000, staleTime: 15_000,

// useProposals.ts
refetchInterval: 30_000, staleTime: 15_000,

// SatelliteAlerts (inline query)
refetchInterval: 30_000, staleTime: 15_000,

// RoyaltyCard (inline query)
refetchInterval: 30_000, staleTime: 15_000,

// FairnessIndex (inline query)
refetchInterval: 30_000, staleTime: 15_000,
```

Every 30 seconds, all 6 queries fire simultaneously, creating a "thundering herd" on the backend. With 100 concurrent dashboard users, that's 600 requests in a 2-second window.

**Fix:** Stagger refetch intervals:

```typescript
// Add jitter to prevent synchronized polling
refetchInterval: 30_000 + Math.random() * 5_000,
```

Or better: use the WebSocket for real-time updates and reduce polling to 60-120s as a fallback.

### 🟠 D-2: WebSocket Invalidation Triggers All Queries

**File:** `dashboard/src/hooks/useWebSocket.ts:22`  
**Impact:** High — single WS message invalidates all query caches

```typescript
ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);
    if (msg.type) {
        qc.invalidateQueries({ queryKey: [msg.type] });
    }
};
```

This is actually correct per-type invalidation. However, if the server sends a message with `type: "all"` or an unrecognized type, it could trigger unexpected behavior. More importantly, there's **no message batching** — if 10 WebSocket messages arrive in 100ms, each triggers a separate query invalidation and refetch.

**Fix:** Debounce invalidations:

```typescript
const invalidateDebounced = useDebouncedCallback(
    (type: string) => qc.invalidateQueries({ queryKey: [type] }),
    500
);
```

### 🟡 D-3: No Memoization in PriceWidget Chart Rendering

**File:** `dashboard/src/components/PriceWidget.tsx:40-70`  
**Impact:** Medium — chart re-renders on every parent render

The `LineChart` and its data are re-computed on every render cycle. With `recharts`, this triggers full SVG re-generation.

**Fix:** Memoize chart data:

```typescript
const chartData = useMemo(() => prices?.[0]?.history ?? [], [prices]);
```

### 🟡 D-4: ExtractionTable Renders All Rows Without Virtualization

**File:** `dashboard/src/components/ExtractionTable.tsx`  
**Impact:** Medium — full DOM render for large datasets

```typescript
{extractions.map((e) => (
    <tr key={e.id}>...</tr>
))}
```

If there are 1,000+ extraction records, this creates 1,000+ DOM nodes. Combined with the 30s refetch, this causes visible jank.

**Fix:** Use `react-window` or `@tanstack/react-virtual` for virtualized lists. Or add server-side pagination.

### 🟡 D-5: ProposalList Inline Query Pattern

**File:** `dashboard/src/components/SatelliteAlerts.tsx`, `RoyaltyCard.tsx`, `FairnessIndex.tsx`  
**Impact:** Medium — hooks defined inline in components, not reusable

Three components define their `useQuery` hooks inline rather than in separate hook files like `useExtractions` and `usePrices`. This makes it harder to share cache configuration and deduplicate queries.

### 🟢 D-6: No Error Boundary

**File:** `dashboard/src/App.tsx`  
**Impact:** Low — unhandled errors crash entire dashboard

No React Error Boundary exists. A single component error (e.g., malformed API response in `ExtractionTable`) crashes the entire dashboard.

**Fix:** Wrap with an ErrorBoundary:

```typescript
<ErrorBoundary fallback={<ErrorFallback />}>
    <main className="dashboard-grid">...</main>
</ErrorBoundary>
```

### 🟢 D-7: No Service Worker / Offline Support

**File:** `dashboard/`  
**Impact:** Low — dashboard requires constant connectivity

No PWA capabilities. For a dashboard that monitors blockchain data and satellite alerts, offline support would improve reliability in low-connectivity mining areas.

---

## 5. Infrastructure Scalability Limits

### 🔴 I-1: Single-Process FastAPI with No Worker Pool

**File:** `src/main.py:145`  
**Impact:** Critical — single process handles all requests

```python
uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
```

Running `uvicorn` without `--workers` means a single process handles all requests. Combined with the blocking Web3 calls (P-2), this means **one oracle submission blocks all other users**.

**Fix:** Use Gunicorn with Uvicorn workers:

```bash
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Or: `uvicorn src.main:app --workers 4`

### 🟠 I-2: No Rate Limiting on API Endpoints

**File:** `src/main.py`  
**Impact:** High — no protection against abuse

No rate limiting middleware exists on any endpoint. The `/agents/{name}/chat` endpoint triggers expensive LLM calls. A malicious user could send 100 concurrent requests, exhausting the NVIDIA API quota and blocking legitimate users.

**Fix:** Add `slowapi` middleware:

```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/agents/{agent_name}/chat")
@limiter.limit("10/minute")
async def chat_with_agent(...):
```

### 🟠 I-3: Oracle Bridge Singleton Has No Connection Pooling

**File:** `src/chain/oracle_bridge.py:185`  
**Impact:** High — single Web3 instance, no connection reuse

```python
_bridge: Optional[OracleBridge] = None

def get_oracle_bridge() -> OracleBridge:
    global _bridge
    if _bridge is None:
        _bridge = OracleBridge()
    return _bridge
```

The singleton `OracleBridge` creates one `Web3` instance. Under concurrent oracle submissions, all requests queue on the single HTTP provider. Polygon RPC providers typically limit to 10-30 concurrent requests.

**Fix:** Use an async Web3 provider with connection pooling, or implement request queuing with priority.

### 🟠 I-4: No Database — Everything In-Memory

**File:** `src/dao/governance.py`, `src/superagent.py`  
**Impact:** High — data loss on restart, no persistence

- GovernanceEngine: proposals and votes in Python dicts
- ConversationMemory: chat history in Python dicts
- Tool Registry Cache: cached results in Python dicts

A server restart loses all governance state, conversation history, and cached tool results. For a DAO where votes are legally binding, this is unacceptable.

**Fix:** Add PostgreSQL/Redis for persistence:
- Governance → PostgreSQL (proposals, votes, members)
- Conversation Memory → Redis with TTL
- Tool Cache → Redis with TTL

### 🟡 I-5: WebSocket Not Implemented on Backend

**File:** `dashboard/src/hooks/useWebSocket.ts` → `src/main.py`  
**Impact:** Medium — dashboard WebSocket connects but backend has no handler

The dashboard connects to `ws://host/ws`, but the FastAPI backend has no WebSocket endpoint. The connection will fail silently, and the dashboard falls back to polling only.

**Fix:** Add WebSocket endpoint:

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        # Push updates to connected dashboards
        await websocket.send_json({"type": "prices", "data": ...})
        await asyncio.sleep(30)
```

### 🟡 I-6: Telegram Bot Shares Event Loop with FastAPI

**File:** `src/channels/telegram_bot.py:545-555`  
**Impact:** Medium — long-polling competes with API requests

```python
class TelegramBotChannel:
    async def start(self):
        await self._app.updater.start_polling(drop_pending_updates=True)
```

The Telegram bot's long-polling runs in the same event loop as FastAPI. Under heavy bot traffic, API response times degrade.

**Fix:** Run the Telegram bot in a separate process or use webhooks instead of polling.

### 🟡 I-7: No Health Check Depth

**File:** `src/main.py:110`  
**Impact:** Medium — health check doesn't verify dependencies

```python
@app.get("/health")
async def health():
    return {"status": "healthy"}
```

The health endpoint returns "healthy" even if:
- The database is down (no DB)
- The blockchain RPC is unreachable
- The NVIDIA API key is expired

**Fix:** Add dependency checks:

```python
@app.get("/health")
async def health():
    checks = {
        "api": True,
        "blockchain": (await oracle.check_connection()).get("connected", False),
        "llm": bool(os.environ.get("NVIDIA_API_KEY")),
    }
    status = "healthy" if all(checks.values()) else "degraded"
    return {"status": status, "checks": checks}
```

### 🟢 I-8: No Request Tracing / Observability

**File:** Entire codebase  
**Impact:** Low — no distributed tracing

No OpenTelemetry, Jaeger, or any tracing integration. Debugging performance issues in production requires correlating logs across Python, Solidity, Flutter, and React manually.

**Fix:** Add OpenTelemetry instrumentation:

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
FastAPIInstrumentor.instrument_app(app)
```

### 🟢 I-9: No CDN / Static Asset Optimization for Dashboard

**File:** `dashboard/vite.config.ts`  
**Impact:** Low — no production build optimization visible

No evidence of code splitting, tree shaking configuration, or CDN deployment. The dashboard bundles all 6 widget components eagerly.

---

## Summary of Recommendations (Priority Order)

| # | Finding | Severity | Effort | Impact |
|---|---------|----------|--------|--------|
| P-1 | Singleton agent initialization | 🔴 Critical | Low | Eliminates 5-15ms per request |
| P-2 | Async Web3 blocking calls | 🔴 Critical | Medium | Unblocks event loop |
| P-3 | Shared HTTP clients | 🔴 Critical | Low | Saves 50-200ms per external call |
| I-1 | Multi-worker deployment | 🔴 Critical | Low | 4x throughput |
| S-1 | Paginated location records | 🔴 Critical | Medium | Prevents gas limit issues |
| F-1 | Batched setState calls | 🔴 Critical | Low | Eliminates chat jank |
| P-4 | Memory session cleanup | 🟠 High | Low | Prevents memory leak |
| P-5 | Async yfinance wrapping | 🟠 High | Low | Prevents event loop blocking |
| P-6 | Lock-free cache | 🟠 High | Medium | Improves concurrency |
| S-2 | Incremental oracle totals | 🟠 High | Medium | Reduces verification gas |
| S-3 | Soulbound transfer overhead | 🟠 High | Medium | Saves ~2k gas per mint |
| F-2 | Image caching in PhotoScreen | 🟠 High | Low | Faster photo re-display |
| F-3 | Optimized ListView | 🟠 High | Medium | Eliminates scroll jank |
| F-4 | AudioPlayer listener cleanup | 🟠 High | Low | Prevents memory leak |
| D-1 | Staggered polling intervals | 🟠 High | Low | Reduces thundering herd |
| D-2 | Debounced WS invalidation | 🟠 High | Low | Reduces re-renders |
| I-2 | API rate limiting | 🟠 High | Low | Prevents abuse |
| I-3 | Web3 connection pooling | 🟠 High | Medium | Improves RPC throughput |
| I-4 | Database persistence | 🟠 High | High | Data durability |
| P-7 | Request deduplication | 🟡 Medium | Medium | Reduces LLM costs |
| P-8 | Governance persistence | 🟡 Medium | High | Data durability |
| P-9 | Telegram session eviction | 🟡 Medium | Low | Prevents memory leak |
| S-4 | Vesting gas optimization | 🟡 Medium | Medium | Reduces release gas |
| S-5 | sqrt overflow protection | 🟡 Medium | Low | Prevents edge-case overflow |
| F-5 | Vote button debouncing | 🟡 Medium | Low | Prevents duplicate votes |
| F-6 | ApiClient lifecycle | 🟡 Medium | Low | Prevents connection leaks |
| F-7 | OfflineSync timer leak | 🟡 Medium | Low | Prevents battery drain |
| D-3 | Memoized chart data | 🟡 Medium | Low | Smoother charts |
| D-4 | Virtualized tables | 🟡 Medium | Medium | Handles large datasets |
| D-5 | Consistent hook patterns | 🟡 Medium | Low | Better code organization |
| I-5 | WebSocket backend | 🟡 Medium | Medium | Real-time dashboard |
| I-6 | Separate bot process | 🟡 Medium | Medium | Isolates concerns |
| I-7 | Deep health checks | 🟡 Medium | Low | Better monitoring |
| S-6 | Event string optimization | 🟢 Low | Low | Minor gas savings |
| D-6 | Error boundary | 🟢 Low | Low | Prevents full crash |
| D-7 | PWA/offline support | 🟢 Low | High | Better reliability |
| I-8 | Distributed tracing | 🟢 Low | Medium | Production debugging |
| I-9 | CDN / code splitting | 🟢 Low | Medium | Faster initial load |

---

*Report generated by the Performance & Scalability Review Council.*
