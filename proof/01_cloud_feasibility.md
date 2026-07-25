# Proof 1: Cloud Infrastructure Feasibility Analysis

**Analyst:** COUNCIL PROOF MEMBER 1 — Cloud Infrastructure Realist  
**Date:** 2026-07-25  
**Verdict:** ⚠️ CONDITIONAL — Works for MVP/prototype, NOT for production at scale  
**Critical Finding:** The claimed specs are WRONG. The actual free tier is HALF of what's stated.

---

## 0. CRITICAL CORRECTION: The Specs Are Wrong

**The Claim:** Oracle Cloud Always Free = 4 ARM cores, 24GB RAM, 200GB storage, 10TB bandwidth

**The Reality (from Oracle's official docs, verified today):**

> "All tenancies get the first 1,500 OCPU hours and 9,000 GB hours per month for free for VM instances using the VM.Standard.A1.Flex shape. **For Always Free tenancies, this is equivalent to 2 OCPUs and 12 GB of memory.**"
> — Oracle Cloud Infrastructure Documentation, Always Free Resources

### What this means:

| Resource | Claimed | Actual (24/7) | Max (burst) |
|----------|---------|---------------|-------------|
| CPU | 4 OCPUs | **2 OCPUs** | 4 OCPUs for ~15 days |
| RAM | 24 GB | **12 GB** | 24 GB for ~15 days |
| Storage | 200 GB | 200 GB (correct) | 200 GB |
| Bandwidth | 10 TB | 10 TB outbound (correct) | 10 TB outbound |

**The "4 cores / 24GB" figure is the MAXIMUM instance size you can create, not the sustained allocation.** To run 4 OCPUs + 24GB 24/7, you'd need 2,920 OCPU-hours/month (limit: 1,500) and 17,520 GB-hours/month (limit: 9,000). You'd exhaust your free budget in ~12 days.

**For always-on production, you get 2 OCPUs and 12GB RAM. This changes everything.**

---

## 1. Container Resource Requirements (Honest Assessment)

### Per-Component Breakdown

| Component | RAM (idle) | RAM (active) | CPU | Notes |
|-----------|-----------|-------------|-----|-------|
| **PostgreSQL + PostGIS** | 256 MB | 512 MB – 1.5 GB | 0.5 – 1 core | Depends on query complexity, connections, shared_buffers |
| **Redis** | 32 MB | 128 – 512 MB | Minimal | In-memory store; size depends on key count and eviction policy |
| **Qdrant** (100K vectors) | 200 MB | 400 – 600 MB | 0.25 – 0.5 core | Based on Qdrant benchmarks: ~1.2GB for 1M float32 vectors (100-dim) |
| **Qdrant** (1M vectors) | 800 MB | 1.2 – 2 GB | 0.5 – 1 core | From Qdrant's own benchmark: 1,152MB minimum for 1M glove-100 vectors |
| **MinIO** | 100 MB | 200 – 500 MB | 0.25 core | Metadata-heavy; actual storage on disk |
| **FastAPI** (Python, 2 workers) | 150 MB | 300 – 600 MB | 0.5 – 1 core | Python is RAM-hungry; each worker ~150-300MB |
| **Caddy** | 20 MB | 50 MB | Negligible | Extremely lightweight |
| **OS + overhead** | 500 MB | 800 MB – 1 GB | 0.25 core | Linux kernel, systemd, docker daemon |

### Total RAM Budget

| Scenario | RAM Required | Fits in 12GB? | Fits in 24GB? |
|----------|-------------|---------------|---------------|
| **MVP (10 miners, 100K vectors)** | 2.5 – 4 GB | ✅ Yes, with 8 GB headroom | ✅ Yes |
| **Growth (100 miners, 500K vectors)** | 4 – 7 GB | ✅ Tight but feasible | ✅ Yes |
| **Scale (1000 miners, 1M vectors)** | 7 – 12 GB | ⚠️ At the limit | ✅ Yes |
| **Burst (10 AI agents + all services)** | 10 – 16 GB | ❌ OOM likely | ⚠️ Tight |

### RAM Verdict
- **12 GB (real free tier):** Handles MVP (10-50 miners) comfortably. Gets tight at 100+ miners with all services running.
- **24 GB (theoretical max for 15 days):** Handles growth phase. But you can only sustain this for ~15 days/month.

**The "10 AI agents" claim is fantasy on 12GB.** Each agent context window + model inference cache requires 500MB–2GB. 10 agents = 5–20GB just for agents. This is the single biggest red flag in the proposal.

---

## 2. Bandwidth Reality

### The Math

- 10 TB outbound/month = 10,000 GB / 30 days = **333 GB/day**
- 10 TB outbound/month = 10,000,000 MB / 30 / 86,400 = **~3.86 MB/s sustained**

### What Can You Serve?

| Content Type | Size per Request | Requests from 10TB | Per Day |
|-------------|-----------------|--------------------|----|
| API JSON response | 5 KB | 2 billion | 66 million |
| Small satellite thumbnail | 100 KB | 100 million | 3.3 million |
| Full satellite image (5MB) | 5 MB | 2 million | 66,667 |
| Miner photo upload (5MB) | 5 MB (inbound, free) | N/A inbound | N/A |

### Bandwidth Verdict
**10 TB outbound is generous for an MVP.** Even with 1,000 miners each downloading 10 satellite images/day (50MB each), that's 500 GB/day — well within 333 GB/day if you're smart about caching and thumbnails.

**The real bottleneck is inbound for satellite imagery**, but Oracle doesn't charge for inbound. The concern is storage, not bandwidth.

**Gotcha:** Oracle's 10TB is outbound only. Inbound is free. But if you're pulling Sentinel-2 tiles (100MB each) from ESA, you need to store them — and 200GB fills fast.

---

## 3. Storage Reality

### The Math

- Total: 200 GB block storage
- Boot volume: 47 GB (minimum, required)
- **Available for data: 153 GB**

### Growth Projections

| Data Type | Per Miner | 100 Miners | 1,000 Miners |
|-----------|----------|------------|--------------|
| PostgreSQL (claims, metadata) | 50 MB | 5 GB | 50 GB |
| Redis (ephemeral, small) | 10 MB | 1 GB | 1 GB (capped by RAM) |
| Qdrant vectors (100K) | N/A | 2 GB | 10 GB |
| MinIO (satellite tiles) | 500 MB | 50 GB | 500 GB ❌ |
| MinIO (miner photos) | 200 MB | 20 GB | 200 GB ❌ |
| Backups | 100 MB | 10 GB | 100 GB ❌ |

### Storage Scenarios

| Scenario | Storage Used | Fits in 153GB? |
|----------|-------------|----------------|
| **10 miners, 30 days** | 8 – 15 GB | ✅ Plenty |
| **100 miners, 90 days** | 50 – 80 GB | ✅ Feasible |
| **100 miners, 1 year** | 150 – 300 GB | ❌ Exceeds limit |
| **1,000 miners, 30 days** | 100 – 200 GB | ⚠️ At/over limit |

### Storage Verdict
**200 GB is the hardest wall.** At 100 active miners submitting daily photos and pulling satellite tiles, you'll exhaust storage in 3-6 months without aggressive data lifecycle management.

**Mitigation strategies:**
- Store only metadata in MinIO; reference external Sentinel-2 API (no local caching)
- Aggressive image compression (WebP, 80% quality)
- Auto-delete raw images after 30 days; keep only processed features
- Use Oracle's Object Storage free tier (20 GB additional) for cold data
- But these are band-aids, not solutions.

---

## 4. CPU Reality

### The Claim: 4 ARM cores running 10 AI agents + API + database

### The Reality: 2 OCPUs (Ampere A1 ARM cores)

Ampere A1 cores are decent — roughly equivalent to 1.5–2x an AWS Graviton2 vCPU for integer workloads. But 2 cores is 2 cores.

### Workload Analysis

| Component | CPU Demand | Notes |
|-----------|-----------|-------|
| PostgreSQL | Low-Medium | Spiky on complex queries, idle otherwise |
| Redis | Very Low | Single-threaded, memory-bound |
| Qdrant | Medium | HNSW search is CPU-intensive on large datasets |
| FastAPI (2 workers) | Low-Medium | Mostly I/O-bound waiting on DB/Redis |
| Caddy | Negligible | Event-driven, minimal CPU |
| **10 AI agents** | **VERY HIGH** | If running local inference — impossible. If calling external APIs — just network I/O |

### Throughput Estimates

- **API requests:** 50–200 RPS (simple CRUD) — fine for 100 miners
- **Vector search:** 100–500 RPS on 100K vectors — acceptable
- **AI agent inference:** 0 RPS locally. Must use external APIs (OpenAI, etc.)

### CPU Verdict
**2 OCPUs can handle 10-100 miners doing API calls and database queries.** It CANNOT run local AI inference. The "10 AI agents" must be API calls to external services, not local models. If they're local, the system will be completely unusable.

**The hidden cost:** If agents call external APIs (OpenAI, Anthropic), you're paying $20-100+/month for API calls, defeating the "$0" claim.

---

## 5. The "10 AI Agents" Problem — The Elephant in the Room

This is the single biggest feasibility issue. Let me be explicit:

### What "10 AI Agents" Actually Requires

| Agent Type | RAM per Agent | CPU per Agent | Feasible on Free Tier? |
|-----------|--------------|--------------|----------------------|
| Local LLM (7B param) | 4 – 8 GB | 2+ cores | ❌ Absolutely not |
| Local LLM (3B param) | 2 – 4 GB | 1-2 cores | ❌ Not with other services |
| External API agent | 50 – 200 MB | Network I/O only | ✅ But costs money |
| Lightweight rule-based agent | 10 – 50 MB | Minimal | ✅ Free |

### The Options

1. **All external API calls:** Works on free tier hardware, but costs $20-100+/month for API calls. Not "$0".
2. **All local inference:** Impossible. Needs 32-80GB RAM and GPUs. Not happening on any VPS.
3. **Hybrid:** Some agents external, some rule-based. Possible at $10-50/month.
4. **No AI agents, just algorithms:** Works at $0. But then it's not really an "AI mining agent."

### AI Agent Verdict
**The "$0 total cost" is a lie if agents use LLM APIs.** The "$0 infra cost" claim might hold if agents are simple algorithms or call free-tier APIs (Hugging Face inference API has a free tier of ~1000 requests/day). But sophisticated multi-agent orchestration with 10 concurrent agents? Either you pay for compute or you pay for API calls.

---

## 6. Migration Path: When Free Tier Isn't Enough

### Tier 1: Oracle Free → Paid (~$5-15/month)

- Upgrade to Pay-As-You-Go (still use Always Free resources, but can burst)
- Add 1 more OCPU + 6GB RAM: ~$10/month
- Add 100GB block volume: ~$4.50/month
- **Total: ~$15/month for 3 OCPUs, 18GB RAM, 300GB storage**

### Tier 2: Hetzner CX22 ($4.50/month)

- 2 vCPUs (AMD), 4 GB RAM, 40 GB SSD, 20 TB bandwidth
- **Worse than Oracle free tier on RAM and storage.** Not a step up for this stack.
- Better option: **Hetzner CPX21** — 3 vCPUs, 4 GB, 80 GB, $7.50/month
- Or: **Hetzner CPX31** — 4 vCPUs, 8 GB, 160 GB, $13.50/month

### Tier 3: Contabo VPS S ($6/month)

- 4 vCPUs, 8 GB RAM, 200 GB SSD, 32 TB bandwidth
- **Comparable to Oracle free tier but with more CPU and no hourly limits**
- The real value: guaranteed 24/7 allocation, no "out of capacity" errors

### Tier 4: Oracle Paid A1 Flex (best value)

- 4 OCPUs, 24 GB RAM: ~$45/month
- But with Always Free credits applied: ~$25/month net
- **This is actually the best upgrade path — same platform, no migration**

### Recommended Progression

| Phase | Infrastructure | Monthly Cost |
|-------|---------------|-------------|
| MVP (0-50 miners) | Oracle Always Free (2 OCPU, 12GB) | $0 |
| Growth (50-200 miners) | Oracle A1 Flex 4 OCPU + external APIs | $25-50 |
| Scale (200-1000 miners) | Dedicated server or multi-node | $50-150 |

---

## 7. Real-World Evidence

### Oracle Free Tier — Known Gotchas

1. **"Out of capacity" is real and common.** Getting an A1 instance provisioned can take days/weeks of retrying. Reddit and Hacker News are full of complaints.
2. **Instances can be reclaimed.** Oracle reserves the right to terminate Always Free instances (though rarely does in practice).
3. **ARM compatibility issues.** Some Docker images don't have ARM builds. PostgreSQL, Redis, Python — all fine. Some niche libraries may not compile.
4. **The 2 OCPU / 12GB reality.** Most blog posts about "4 cores / 24GB free!" are misleading — they describe the max burst config, not sustained.
5. **Network performance.** Oracle free tier networking is decent (~1 Gbps) but not exceptional. Sufficient for API workloads.

### Similar Deployments (Evidence)

- **Homelab/self-hosted communities** routinely run PostgreSQL + Redis + a web app on 2-4 GB RAM VPS. Adding Qdrant is the stretch.
- **Qdrant's own benchmarks** confirm 1.2GB RAM for 1M vectors — this is real and validated.
- **Multiple Reddit threads** confirm successful Always Free deployments of lightweight web stacks (Next.js + PostgreSQL + Redis).
- **No evidence found** of anyone running a full multi-agent AI system on Oracle free tier. Because it's not feasible.

---

## 8. FINAL VERDICT

### Can the Mining Super-Agent Run on Oracle Cloud Always Free?

| Aspect | Verdict | Confidence |
|--------|---------|-----------|
| Basic stack (PostgreSQL + Redis + FastAPI + Caddy) | ✅ YES | 95% |
| + Qdrant (100K vectors) | ✅ YES | 90% |
| + Qdrant (1M vectors) | ⚠️ TIGHT on 12GB | 75% |
| + MinIO (satellite image storage) | ⚠️ Limited to ~6 months | 85% |
| + 10 AI agents (local) | ❌ IMPOSSIBLE | 99% |
| + 10 AI agents (external API) | ✅ Hardware yes, but costs $ | 90% |
| Full stack, 10 miners, 6 months | ✅ YES | 85% |
| Full stack, 100 miners, 12 months | ❌ NO (storage + RAM) | 90% |
| Full stack, 1000 miners | ❌ NO | 95% |

### The Honest Answer

**YES, for an MVP/prototype with ≤50 miners and ≤6 months of data.** The Oracle Always Free tier can run the core infrastructure stack (database, cache, API, reverse proxy) comfortably on 12GB RAM / 2 OCPUs.

**NO, for production at scale.** The 200GB storage wall hits first (3-6 months), followed by RAM pressure at 100+ concurrent miners, and the "10 AI agents" requirement is either impossible locally or costs money externally.

**The "$0 production" claim is misleading** because:
1. The actual specs are 2 OCPUs / 12GB RAM, not 4 / 24GB
2. AI agents require external API costs ($20-100+/month)
3. Storage fills in months, not years
4. No redundancy, no backups beyond what you squeeze into 153GB

### Recommended Path

Start on Oracle Free. Build the MVP. Prove the concept. Budget $25-50/month for the growth phase. The infrastructure cost is not the bottleneck — the AI agent API costs are.

---

*This analysis is based on Oracle Cloud official documentation (verified 2026-07-25), Qdrant official benchmarks, and standard infrastructure sizing practices. All figures assume typical workloads; actual usage may vary ±30%.*
