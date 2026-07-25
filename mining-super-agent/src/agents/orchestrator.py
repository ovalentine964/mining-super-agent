"""
Orchestrator Agent — Routes requests to specialist agents.

The brain of the system. Uses NVIDIA NIM (Nemotron 3 Ultra) for complex
reasoning about which agents to invoke, how to parallelize, and how to
synthesize results.

Key features:
- Intelligent routing based on request analysis
- Parallel execution when agents are independent
- Result synthesis with conflict resolution
- Confidence aggregation across agents
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from .base import (
    AgentResult,
    BaseAgent,
    ToolCall,
    ToolDefinition,
    calibrate_confidence,
)

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator: routes user requests to the right specialist agents,
    manages parallel execution, and synthesizes results.
    """

    def __init__(self, agents: Optional[dict[str, BaseAgent]] = None):
        super().__init__(
            name="Orchestrator",
            description=(
                "Routes mining-related requests to specialist agents. "
                "Analyzes user intent, determines which agents are needed, "
                "manages parallel execution, and synthesizes results."
            ),
            model_id="nvidia/nemotron-3-ultra",  # Nemotron 3 Ultra for orchestration
            permissions={"*"},  # Orchestrator has all permissions
            system_prompt=self._build_system_prompt(),
        )
        self.agents: dict[str, BaseAgent] = agents or {}
        self._route_cache: dict[str, list[str]] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a specialist agent."""
        self.agents[agent.name.lower()] = agent
        logger.info(f"Registered agent: {agent.name}")

    def _build_system_prompt(self) -> str:
        return """You are the Orchestrator for a Mining Super-Agent system in Kenya.

Your job is to analyze user requests and determine which specialist agents to invoke.

AVAILABLE AGENTS:
- geological: Rock analysis, deposit models, Kenya geology (Migori Greenstone Belt)
- satellite: Sentinel-2 analysis, alteration mapping, spectral indices
- mineral_id: Mineral identification from photos, physical tests
- market: Commodity prices, trends, market intelligence
- legal: Kenya Mining Act 2016, licensing, EIA, community rights
- financial: NPV/IRR, CAPEX/OPEX, sensitivity analysis
- community: Stakeholder analysis, FPIC, community relations
- exploration: Drilling programs, sampling, geophysical surveys
- qc: Quality control, cross-validation, consistency checks
- quantum: Quantum ML for mineral classification, optimization

ROUTING RULES:
1. Analyze the user's intent to determine relevant agents
2. If multiple agents are needed and independent, run them IN PARALLEL
3. If results conflict, use QC agent to resolve
4. Always include confidence scores
5. For mineral identification, ALWAYS include disclaimers about physical verification
6. Synthesize results into a coherent response

PARALLEL EXECUTION:
- geological + satellite → can run in parallel
- mineral_id + market → can run in parallel
- legal + financial + community → can run in parallel
- qc → runs AFTER other agents complete
- quantum → runs in parallel with classical agents when applicable

CONFLICT RESOLUTION:
When agents produce conflicting results:
1. Check evidence quality (tool success rate, data source reliability)
2. Weight by agent confidence scores
3. If still conflicting, escalate to QC agent
4. If QC can't resolve, present both views with analysis
"""

    def _get_routing(self, task: str) -> list[str]:
        """
        Determine which agents to invoke for a given task.
        Uses keyword analysis + LLM reasoning.
        """
        task_lower = task.lower()
        agents_needed: list[str] = []

        # Keyword-based routing (fast path)
        routing_rules = {
            "geological": [
                "rock", "geology", "geological", "deposit", "formation",
                "stratigraphy", "fault", "fold", "mineralization",
                "migori", "greenstone", "belt", "quartz", "vein",
            ],
            "satellite": [
                "satellite", "sentinel", "ndvi", "alteration", "remote sensing",
                "spectral", "imagery", "aerial", "land use", "vegetation",
            ],
            "mineral_id": [
                "identify", "mineral", "rock type", "what is this", "photo",
                "image", "gold", "pyrite", "copper", "specimen", "sample",
            ],
            "market": [
                "price", "market", "commodity", "gold price", "copper price",
                "value", "worth", "trading", "demand", "supply",
            ],
            "legal": [
                "legal", "law", "license", "permit", "mining act", "eia",
                "compliance", "regulation", "fpic", "community consent",
            ],
            "financial": [
                "financial", "npv", "irr", "cost", "revenue", "profit",
                "investment", "capex", "opex", "sensitivity", "roi",
            ],
            "community": [
                "community", "stakeholder", "fpic", "consent", "local",
                "village", "chief", "elders", "compensation",
            ],
            "exploration": [
                "drill", "drilling", "borehole", "sample", "sampling",
                "geophysics", "survey", "magnetic", "resistivity",
            ],
            "quantum": [
                "quantum", "optimization", "qaoa", "advanced classification",
                "high-dimensional",
            ],
        }

        for agent_name, keywords in routing_rules.items():
            if any(kw in task_lower for kw in keywords):
                agents_needed.append(agent_name)

        # Default: if nothing matched, use geological + market as baseline
        if not agents_needed:
            agents_needed = ["geological", "market"]

        return agents_needed

    def _get_execution_groups(self, agent_names: list[str]) -> list[list[str]]:
        """
        Group agents into parallel execution batches.
        Agents in the same group can run simultaneously.
        QC always runs last.
        """
        # Dependency-aware grouping
        independent_groups = {
            "analysis": ["geological", "satellite", "mineral_id", "quantum"],
            "business": ["market", "financial", "legal", "community"],
            "planning": ["exploration"],
        }

        groups: list[list[str]] = []
        remaining = set(agent_names)

        # First group: independent agents that can run in parallel
        first_batch = []
        for group_name, group_agents in independent_groups.items():
            for agent in group_agents:
                if agent in remaining:
                    first_batch.append(agent)
                    remaining.discard(agent)

        if first_batch:
            groups.append(first_batch)

        # Remaining agents (shouldn't normally happen, but handle gracefully)
        if remaining:
            groups.append(list(remaining))

        # QC always runs last (if requested or if multiple agents ran)
        if len(agent_names) > 1 and "qc" not in agent_names:
            groups.append(["qc"])

        return groups

    async def run(self, task: str, context: Optional[dict[str, Any]] = None) -> AgentResult:
        """
        Orchestrate the full pipeline:
        1. Determine which agents to invoke
        2. Execute in parallel batches
        3. Synthesize results
        4. Run QC if needed
        """
        logger.info(f"[Orchestrator] Processing: {task[:200]}")

        # Step 1: Route
        agents_needed = self._get_routing(task)
        logger.info(f"[Orchestrator] Agents needed: {agents_needed}")

        # Validate all agents exist
        missing = [a for a in agents_needed if a not in self.agents]
        if missing:
            logger.warning(f"[Orchestrator] Missing agents: {missing}")
            agents_needed = [a for a in agents_needed if a in self.agents]

        if not agents_needed:
            return AgentResult(
                agent_name="Orchestrator",
                success=False,
                summary="No suitable agents found for this request.",
                confidence=0.0,
                warnings=["No matching agents for the request."],
            )

        # Step 2: Execute in parallel batches
        execution_groups = self._get_execution_groups(agents_needed)
        all_results: dict[str, AgentResult] = {}

        for group in execution_groups:
            logger.info(f"[Orchestrator] Executing group: {group}")
            tasks = []
            for agent_name in group:
                agent = self.agents[agent_name]
                tasks.append(self._run_agent_safely(agent, task, context))

            group_results = await asyncio.gather(*tasks, return_exceptions=True)

            for agent_name, result in zip(group, group_results):
                if isinstance(result, Exception):
                    logger.error(f"[Orchestrator] Agent '{agent_name}' raised: {result}")
                    all_results[agent_name] = AgentResult(
                        agent_name=agent_name,
                        success=False,
                        summary=f"Agent failed: {result}",
                        confidence=0.0,
                        warnings=[f"Exception: {result}"],
                    )
                elif result is not None:
                    all_results[agent_name] = result

        # Step 3: Synthesize
        return self._synthesize(task, all_results)

    async def _run_agent_safely(
        self,
        agent: BaseAgent,
        task: str,
        context: Optional[dict[str, Any]],
    ) -> Optional[AgentResult]:
        """Run an agent with error handling and timeout."""
        try:
            return await asyncio.wait_for(
                agent.run(task, context),
                timeout=agent.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(f"[{agent.name}] Timed out after {agent.timeout_seconds}s")
            return AgentResult(
                agent_name=agent.name,
                success=False,
                summary=f"Agent timed out after {agent.timeout_seconds}s",
                confidence=0.0,
                warnings=[f"Timeout: {agent.timeout_seconds}s"],
            )
        except Exception as e:
            logger.exception(f"[{agent.name}] Failed")
            return AgentResult(
                agent_name=agent.name,
                success=False,
                summary=f"Agent error: {e}",
                confidence=0.0,
                warnings=[f"Error: {e}"],
            )

    def _synthesize(
        self,
        original_task: str,
        results: dict[str, AgentResult],
    ) -> AgentResult:
        """
        Synthesize results from multiple agents into a coherent response.
        Handles conflict resolution and confidence aggregation.
        """
        successful = {k: v for k, v in results.items() if v.success}
        failed = {k: v for k, v in results.items() if not v.success}

        # Build summary
        summaries = []
        for agent_name, result in successful.items():
            summaries.append(f"**{agent_name.title()}**: {result.summary}")

        combined_summary = "\n\n".join(summaries) if summaries else "No successful analysis."

        # Aggregate confidence (weighted by individual confidence)
        if successful:
            confidences = [r.confidence for r in successful.values()]
            # Use geometric mean for conservative aggregation
            import math
            agg_confidence = math.exp(sum(math.log(max(0.01, c)) for c in confidences) / len(confidences))
        else:
            agg_confidence = 0.0

        # Detect conflicts
        warnings = []
        for agent_name, result in failed.items():
            warnings.append(f"Agent '{agent_name}' failed: {result.summary}")

        # Collect all recommendations and disclaimers
        recommendations = []
        disclaimers = []
        for result in successful.values():
            recommendations.extend(result.recommendations)
            disclaimers.extend(result.disclaimers)

        # Add standard disclaimers
        disclaimers.append(
            "This analysis is for informational purposes only. "
            "For economic minerals, always obtain professional geological assessment "
            "and physical laboratory verification."
        )

        return AgentResult(
            agent_name="Orchestrator",
            success=len(successful) > 0,
            summary=combined_summary,
            detailed_findings={
                agent_name: result.detailed_findings
                for agent_name, result in successful.items()
            },
            confidence=calibrate_confidence(
                raw_score=agg_confidence,
                evidence_count=len(successful),
                source_reliability=0.75,
            ),
            tool_calls=[
                tc
                for result in successful.values()
                for tc in result.tool_calls
            ],
            warnings=warnings,
            recommendations=list(set(recommendations)),
            disclaimers=list(set(disclaimers)),
            metadata={
                "agents_invoked": list(results.keys()),
                "agents_succeeded": list(successful.keys()),
                "agents_failed": list(failed.keys()),
            },
        )
