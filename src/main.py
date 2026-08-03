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
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import all components
from src.agents import list_agents, get_agent
from src.dao.governance import GovernanceEngine
from src.chain.oracle_bridge import get_oracle_bridge, OracleConfig
from src.tools.fair_deal import evaluate_valentine_offer

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logger.info("Sovereign Resource DAO starting...")
    logger.info("Agents loaded: %d", len(list_agents()))
    yield
    logger.info("Sovereign Resource DAO shutting down.")


app = FastAPI(
    title="Sovereign Resource DAO",
    description="AI-powered mineral intelligence and community-owned resource governance",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health & Status ──────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "sovereign-resource-dao"}


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
