"""
DAO Governance — The Sovereign Decision Layer

This module implements the governance logic for the Sovereign Resource DAO.
It connects the AI agents to the on-chain governance system, enabling:
- Proposal creation (any community member can propose)
- Quadratic voting (wealth cannot buy decisions)
- Automatic execution (smart contracts enforce decisions)
- Transparent record-keeping (every vote is on-chain)

The principle: Math is the law. Smart contracts don't lie.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ProposalType(Enum):
    """Types of proposals the community can vote on."""
    ROYALTY_ALLOCATION = "royalty_allocation"      # How to spend development fund
    CONTRACT_APPROVAL = "contract_approval"         # Should we sign this mining deal?
    ENVIRONMENTAL_ACTION = "environmental_action"   # Deploy sensors, trigger audits
    DISPUTE_RESOLUTION = "dispute_resolution"       # Resolve extraction disputes
    PARAMETER_CHANGE = "parameter_change"           # Change DAO parameters
    PARTNERSHIP = "partnership"                     # Partner with other DAOs
    EMERGENCY = "emergency"                         # Urgent action needed


class ProposalStatus(Enum):
    """Lifecycle stages of a proposal."""
    DRAFT = "draft"               # Being written
    ACTIVE = "active"             # Open for voting
    PASSED = "passed"             # Approved by community
    REJECTED = "rejected"         # Rejected by community
    EXECUTED = "executed"         # Action taken on-chain
    EXPIRED = "expired"           # Voting period ended without quorum


@dataclass
class Proposal:
    """A governance proposal."""
    id: str
    title: str
    description: str
    proposal_type: ProposalType
    proposer: str                    # Wallet address
    status: ProposalStatus = ProposalStatus.DRAFT
    created_at: int = 0              # Unix timestamp
    voting_ends_at: int = 0          # Unix timestamp
    for_power: float = 0.0           # Quadratic voting power (for)
    against_power: float = 0.0       # Quadratic voting power (against)
    voter_count: int = 0
    execution_data: Optional[dict] = None  # On-chain execution parameters
    ai_analysis: Optional[dict] = None     # Agent analysis of the proposal


@dataclass
class CommunityMember:
    """A member of the DAO."""
    wallet_address: str
    name: Optional[str] = None
    location: Optional[str] = None
    role: str = "member"             # "member", "elder", "youth", "miner"
    tokens_staked: float = 0.0
    voting_power: float = 0.0
    contributions: int = 0           # Number of data submissions
    joined_at: int = 0


class GovernanceEngine:
    """
    The governance engine manages proposals, voting, and execution.

    It connects:
    - Community members (who propose and vote)
    - AI agents (who analyze proposals and provide recommendations)
    - Smart contracts (who enforce decisions)
    """

    def __init__(self):
        self.proposals: dict[str, Proposal] = {}
        self.members: dict[str, CommunityMember] = {}
        self.next_proposal_id: int = 1

    def create_proposal(
        self,
        title: str,
        description: str,
        proposal_type: ProposalType,
        proposer: str,
        voting_duration_hours: int = 72,
        execution_data: Optional[dict] = None,
    ) -> Proposal:
        """
        Create a new governance proposal.

        Any community member can create a proposal. The proposal enters
        DRAFT status and can be activated for voting.
        """
        import time

        proposal_id = f"PROP-{self.next_proposal_id:04d}"
        self.next_proposal_id += 1

        proposal = Proposal(
            id=proposal_id,
            title=title,
            description=description,
            proposal_type=proposal_type,
            proposer=proposer,
            status=ProposalStatus.DRAFT,
            created_at=int(time.time()),
            voting_ends_at=int(time.time()) + (voting_duration_hours * 3600),
            execution_data=execution_data,
        )

        self.proposals[proposal_id] = proposal
        logger.info("Proposal created: %s by %s", proposal_id, proposer)

        return proposal

    def activate_voting(self, proposal_id: str) -> Proposal:
        """Move a proposal from DRAFT to ACTIVE (open for voting)."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        if proposal.status != ProposalStatus.DRAFT:
            raise ValueError(f"Proposal is {proposal.status}, not DRAFT")

        import time
        proposal.status = ProposalStatus.ACTIVE
        proposal.voting_ends_at = int(time.time()) + (72 * 3600)  # 72 hours

        logger.info("Voting activated for: %s", proposal_id)
        return proposal

    def cast_vote(
        self,
        proposal_id: str,
        voter: str,
        tokens_committed: float,
        support: bool,
    ) -> dict[str, Any]:
        """
        Cast a quadratic vote on a proposal.

        Voting power = sqrt(tokens_committed)
        """
        import math

        proposal = self.proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        if proposal.status != ProposalStatus.ACTIVE:
            raise ValueError(f"Proposal is {proposal.status}, not ACTIVE")

        quadratic_power = math.sqrt(tokens_committed)

        if support:
            proposal.for_power += quadratic_power
        else:
            proposal.against_power += quadratic_power

        proposal.voter_count += 1

        return {
            "proposal_id": proposal_id,
            "voter": voter,
            "tokens_committed": tokens_committed,
            "quadratic_power": quadratic_power,
            "support": support,
            "total_for": proposal.for_power,
            "total_against": proposal.against_power,
        }

    def check_proposal_result(self, proposal_id: str) -> dict[str, Any]:
        """Check if a proposal has passed or failed."""
        import time

        proposal = self.proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        voting_ended = time.time() > proposal.voting_ends_at
        total_power = proposal.for_power + proposal.against_power

        # Minimum participation: quadratic power must exceed threshold
        min_participation = 100  # sqrt(10000) = 100, so at least 10000 tokens committed
        has_quorum = total_power >= min_participation

        passed = (
            proposal.for_power > proposal.against_power
            and has_quorum
            and voting_ended
        )

        if voting_ended:
            proposal.status = ProposalStatus.PASSED if passed else ProposalStatus.REJECTED

        return {
            "proposal_id": proposal_id,
            "status": proposal.status.value,
            "for_power": proposal.for_power,
            "against_power": proposal.against_power,
            "total_power": total_power,
            "has_quorum": has_quorum,
            "voting_ended": voting_ended,
            "passed": passed,
            "voter_count": proposal.voter_count,
        }

    def get_active_proposals(self) -> list[dict[str, Any]]:
        """Get all currently active proposals."""
        import time
        now = time.time()

        active = []
        for proposal in self.proposals.values():
            if proposal.status == ProposalStatus.ACTIVE:
                active.append({
                    "id": proposal.id,
                    "title": proposal.title,
                    "type": proposal.proposal_type.value,
                    "for_power": proposal.for_power,
                    "against_power": proposal.against_power,
                    "voter_count": proposal.voter_count,
                    "voting_ends_in_hours": max(
                        0,
                        (proposal.voting_ends_at - now) / 3600
                    ),
                })

        return active

    def register_member(
        self,
        wallet_address: str,
        name: Optional[str] = None,
        location: Optional[str] = None,
        role: str = "member",
    ) -> CommunityMember:
        """Register a new community member."""
        member = CommunityMember(
            wallet_address=wallet_address,
            name=name,
            location=location,
            role=role,
        )
        self.members[wallet_address] = member
        logger.info("Member registered: %s (%s)", wallet_address, name)
        return member

    def get_community_stats(self) -> dict[str, Any]:
        """Get overall community statistics."""
        total_proposals = len(self.proposals)
        active_proposals = sum(
            1 for p in self.proposals.values()
            if p.status == ProposalStatus.ACTIVE
        )
        passed_proposals = sum(
            1 for p in self.proposals.values()
            if p.status == ProposalStatus.PASSED
        )

        return {
            "total_members": len(self.members),
            "total_proposals": total_proposals,
            "active_proposals": active_proposals,
            "passed_proposals": passed_proposals,
            "total_voting_power": sum(
                m.voting_power for m in self.members.values()
            ),
        }
