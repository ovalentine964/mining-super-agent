"""
Sovereign Resource DAO — Main Entry Point

This is the main application that wires together:
1. The AI Super-Agent (mineral intelligence)
2. The Five Sovereign Agents (Sentinel, Auditor, Advocate, Oracle, Ambassador)
3. The DAO Governance Engine (proposals, quadratic voting)
4. The Oracle Bridge (Python → Polygon blockchain)
5. The Fair Deal Calculator (exploitation detection)

Run:
    python -m src.main
    # or
    uvicorn src.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Import all components
from src.agents import list_agents, get_agent
from src.dao.governance import GovernanceEngine
from src.chain.oracle_bridge import get_oracle_bridge, OracleConfig
from src.tools.fair_deal import evaluate_valentine_offer
from src.api.routes.voice import router as voice_router
from src.channels import get_registry, register_default_channels

# ── Database Engine (SQLAlchemy connection pool, lazy init) ─────────────

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost:5432/sovereign_dao")

# Lazy engine creation — avoids blocking import when DB is unreachable
engine = None
SessionLocal = None


def _ensure_engine():
    """Create the SQLAlchemy engine on first use, not at import time."""
    global engine, SessionLocal
    if engine is None:
        engine = create_engine(
            DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=os.environ.get("SQL_ECHO", "false").lower() == "true",
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine


logger = logging.getLogger(__name__)


# ── In-Memory Sliding Window Rate Limiter (fail-closed) ─────────────

class InMemoryRateLimiter:
    """Sliding window rate limiter using in-memory counters.
    Used as fail-closed fallback when Redis is unreachable."""

    def __init__(self, default_limit: int = 100, window_secs: int = 60):
        self.default_limit = default_limit
        self.window_secs = window_secs
        self._counters: dict[str, list[float]] = {}

    def is_allowed(self, key: str, limit: int | None = None) -> tuple[bool, int]:
        """Check if request is allowed under rate limit.
        Returns (allowed, current_count)."""
        import time
        limit = limit or self.default_limit
        now = time.monotonic()
        window = float(self.window_secs)
        timestamps = self._counters.setdefault(key, [])
        # Remove expired entries
        timestamps[:] = [t for t in timestamps if now - t < window]
        count = len(timestamps)
        if count >= limit:
            return False, count
        timestamps.append(now)
        return True, count + 1


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with Redis primary + in-memory fallback.
    NEVER fails open — blocks requests if Redis is down."""

    def __init__(self, app, redis_client=None, default_limit: int = 100, window_secs: int = 60):
        super().__init__(app)
        self.redis = redis_client
        self.memory_limiter = InMemoryRateLimiter(default_limit, window_secs)
        self.default_limit = default_limit
        self.window_secs = window_secs

    async def dispatch(self, request: Request, call_next):
        # Build rate key from client IP + path prefix
        client_ip = request.client.host if request.client else "unknown"
        path_prefix = request.url.path.split("/")[1] if request.url.path else "root"
        rate_key = f"rl:{client_ip}:{path_prefix}"

        redis_available = False
        if self.redis is not None:
            try:
                count = await self.redis.incr(rate_key)
                if count == 1:
                    await self.redis.expire(rate_key, self.window_secs)
                redis_available = True
                if count > self.default_limit:
                    logger.warning("Rate limit exceeded (Redis): key=%s count=%d", rate_key, count)
                    return JSONResponse(
                        status_code=429,
                        content={"error": "rate_limit_exceeded", "retry_after_secs": self.window_secs},
                    )
            except Exception as e:
                logger.warning("Redis rate limiting failed (%s), using in-memory fallback", e)

        # Fallback: in-memory sliding window (fail-closed)
        if not redis_available:
            allowed, count = self.memory_limiter.is_allowed(rate_key, self.default_limit)
            if not allowed:
                logger.warning("Rate limit exceeded (in-memory): key=%s count=%d", rate_key, count)
                return JSONResponse(
                    status_code=429,
                    content={"error": "rate_limit_exceeded", "retry_after_secs": self.window_secs},
                )

        return await call_next(request)


# Singleton agent — created once at startup, reused for all requests
_agent_instance = None


def get_agent_instance():
    """Get or create the singleton SovereignResourceDAO agent."""
    global _agent_instance
    if _agent_instance is None:
        from src.superagent import SovereignResourceDAO
        _agent_instance = SovereignResourceDAO()
    return _agent_instance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    global _agent_instance
    logger.info("Sovereign Resource DAO starting...")
    logger.info("Agents loaded: %d", len(list_agents()))

    # Pre-create the agent singleton (saves 5-15ms per request)
    _agent_instance = get_agent_instance()
    logger.info("Super-agent initialized (singleton)")

    # Register and start messaging channels (Telegram, etc.)
    await register_default_channels()
    registry = get_registry()
    await registry.start_all()

    yield

    # Shutdown channels then exit
    await registry.shutdown_all()
    logger.info("Sovereign Resource DAO shutting down.")


app = FastAPI(
    title="Sovereign Resource DAO",
    description="AI-powered mineral intelligence and community-owned resource governance",
    version="1.0.0",
    lifespan=lifespan,
)

# ── API Key Auth (optional, enabled via API_KEY env var) ───────────────────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_REQUIRED_API_KEY = os.environ.get("API_KEY", "")


async def verify_api_key(api_key: str | None = Depends(_api_key_header)):
    """Require API key if API_KEY env var is set. Otherwise allow all."""
    if _REQUIRED_API_KEY and api_key != _REQUIRED_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True

# ── Routers ────────────────────────────────────────────────────────────────

app.include_router(voice_router)


# ── Channel Routing (called by Telegram bot) ────────────────────────────────

@app.post("/api/v1/channels/route")
async def route_channel_message(payload: dict):
    """
    Route an inbound message from any channel (Telegram, WhatsApp, etc.)
    to the AI agent pipeline.

    Called by BackendClient.route_message() in the Telegram bot.
    """
    message_type = payload.get("message_type", "text")
    text = payload.get("text", "")
    sender = payload.get("sender_id", "unknown")
    source = payload.get("source_channel", "unknown")

    logger.info("Routing %s message from %s via %s", message_type, sender, source)

    # Try to get a response from the super-agent (singleton, not per-request)
    try:
        agent = get_agent_instance()
        result = await agent.chat(
            user_id=sender,
            message=text or f"[{message_type} message received]",
        )
        return {
            "text": result.get("response", "Message received."),
            "message_id": str(uuid.uuid4()),
            "parse_mode": "Markdown",
        }
    except Exception:
        logger.exception("Agent routing failed, returning acknowledgment")
        return {
            "text": f"✅ Received your {message_type} message. Processing…",
            "message_id": str(uuid.uuid4()),
        }


@app.post("/api/v1/media/upload")
async def upload_media():
    """Stub: media upload for channel routing."""
    return {"url": "placeholder", "status": "uploaded"}


@app.post("/api/v1/channels/telegram/verify-link")
async def verify_telegram_link(payload: dict):
    """Stub: verify a Telegram link code."""
    return {"account_id": "demo-account", "community_name": "Sovereign Resource DAO"}


@app.get("/api/v1/channels/telegram/user/{telegram_user_id}")
async def get_telegram_user(telegram_user_id: int):
    """Stub: get Telegram user context."""
    return {
        "account_id": f"user-{telegram_user_id}",
        "community_name": "Sovereign Resource DAO",
        "role": "member",
        "linked_channels": [{"type": "telegram", "status": "connected"}],
    }


@app.post("/api/v1/channels/receipt")
async def delivery_receipt(payload: dict):
    """Stub: delivery receipt from channels."""
    return {"status": "ok"}


@app.get("/api/v1/governance/proposals/active")
async def active_proposals():
    """Stub: list active proposals for the Telegram bot's /vote command."""
    return {"proposals": governance.get_active_proposals()}


# ── Rate Limiting Middleware (Redis + in-memory fallback, fail-closed) ──
_redis_client = None
try:
    import redis.asyncio as aioredis
    _redis_url = os.environ.get("REDIS_URL", "")
    if _redis_url:
        _redis_client = aioredis.from_url(_redis_url, decode_responses=True)
        logger.info("Rate limiter: Redis connected")
except Exception as e:
    logger.warning("Rate limiter: Redis unavailable (%s), using in-memory only", e)

app.add_middleware(
    RateLimitMiddleware,
    redis_client=_redis_client,
    default_limit=int(os.environ.get("RATE_LIMIT", "100")),
    window_secs=int(os.environ.get("RATE_WINDOW_SECS", "60")),
)

# CORS — restrict in production
_cors_origins = os.environ.get("CORS_ORIGINS", "").strip()
if not _cors_origins or _cors_origins == "*":
    if os.environ.get("ENV", "development") == "production":
        raise ValueError("CORS_ORIGINS must be set in production (no wildcards)")
    _cors_origins_list = ["http://localhost:3000", "http://localhost:5173"]  # dev defaults
else:
    _cors_origins_list = [o.strip() for o in _cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health & Status ──────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    # Don't leak application name in production
    is_prod = os.environ.get("ENV", "development") == "production"
    return {"status": "healthy"} if is_prod else {"status": "healthy", "service": "sovereign-resource-dao"}


@app.get("/status")
async def status():
    agents = list_agents()
    oracle = get_oracle_bridge()
    connection = await oracle.check_connection()
    return {
        "agents": len(agents),
        "agent_names": [a["name"] for a in agents],
        "blockchain": connection,
    }


# ── Agent Endpoints ──────────────────────────────────────────────────────────

@app.get("/agents")
async def get_agents():
    """List all five sovereign agents."""
    return {"agents": list_agents()}


@app.post("/agents/{agent_name}/chat")
async def chat_with_agent(agent_name: str, message: dict):
    """Chat with a specific sovereign agent."""
    try:
        agent = get_agent(agent_name)
        return {
            "agent": agent.config.name,
            "mission": agent.config.mission,
            "tools": agent.config.tools,
            "note": "Connect to LLM for full functionality",
        }
    except ValueError as e:
        return {"error": str(e)}


# ── Fair Deal Calculator ─────────────────────────────────────────────────────

@app.get("/fair-deal/valentine")
async def valentine_fair_deal():
    """Analyze Valentine's specific situation (Nyatike, Migori County)."""
    result = evaluate_valentine_offer()
    return {
        "offer_amount_kes": result.offer_amount_kes,
        "estimated_value_kes": result.estimated_total_value_kes,
        "fair_share_kes": result.fair_share_kes,
        "exploitation_ratio": result.exploitation_ratio,
        "verdict": result.verdict,
        "explanation_sw": result.explanation_sw,
        "explanation_en": result.explanation_en,
        "recommended_actions": result.recommended_actions,
    }


@app.post("/fair-deal/evaluate")
async def evaluate_offer(offer: dict):
    """Evaluate any mining offer for fairness."""
    from src.tools.fair_deal import evaluate_offer as eval_offer
    result = eval_offer(
        offer_amount_kes=offer.get("offer_amount_kes", 0),
        minerals=offer.get("minerals", []),
        location=offer.get("location", "Unknown"),
    )
    return {
        "verdict": result.verdict,
        "exploitation_ratio": result.exploitation_ratio,
        "explanation_sw": result.explanation_sw,
        "explanation_en": result.explanation_en,
        "recommended_actions": result.recommended_actions,
    }


# ── DAO Governance ───────────────────────────────────────────────────────────

governance = GovernanceEngine()


@app.get("/dao/proposals")
async def list_proposals():
    """List all active governance proposals."""
    return {"proposals": governance.get_active_proposals()}


@app.post("/dao/proposals")
async def create_proposal(proposal: dict):
    """Create a new governance proposal."""
    from src.dao.governance import ProposalType
    p = governance.create_proposal(
        title=proposal.get("title", ""),
        description=proposal.get("description", ""),
        proposal_type=ProposalType(proposal.get("type", "royalty_allocation")),
        proposer=proposal.get("proposer", "unknown"),
    )
    return {"proposal_id": p.id, "status": p.status.value}


@app.post("/dao/proposals/{proposal_id}/vote")
async def cast_vote(proposal_id: str, vote: dict):
    """Cast a quadratic vote on a proposal."""
    result = governance.cast_vote(
        proposal_id=proposal_id,
        voter=vote.get("voter", "unknown"),
        tokens_committed=vote.get("tokens", 0),
        support=vote.get("support", True),
    )
    return result


@app.get("/dao/stats")
async def dao_stats():
    """Get community statistics."""
    return governance.get_community_stats()


# ── Blockchain ───────────────────────────────────────────────────────────────

@app.get("/chain/status")
async def chain_status():
    """Check blockchain connection status."""
    oracle = get_oracle_bridge()
    return await oracle.check_connection()


@app.post("/chain/submit")
async def submit_to_chain(observation: dict):
    """Submit an observation to the blockchain oracle."""
    from src.chain.oracle_bridge import submit_to_chain
    return await submit_to_chain(observation)


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
