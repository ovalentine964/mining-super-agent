"""
Sovereign Resource DAO — ONE agent, many tools.

Jensen Huang's vision: "We create super sub-agents connected to specialized
tools. That super agent is not trying to book me travel. It's just trying
to optimize our supply chain."

This is NOT a multi-agent system. There is no orchestrator routing between
10 specialist agents. There is ONE intelligent entity that uses OpenAI
function calling to select and invoke tools directly.

Architecture:
    User → SovereignResourceDAO (single LLM + function calling) → Tools → Response

NOT:
    User → Orchestrator → [GeologicalAgent, MarketAgent, ...] → Synthesizer → Response
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from .tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conversation memory (per-user)
# ---------------------------------------------------------------------------

class ConversationMemory:
    """
    Per-user conversation history.
    
    Keeps the last N messages for context so the agent can handle
    follow-up questions like "what about copper?" after a gold query.
    """

    def __init__(self, max_messages: int = 20, ttl_hours: float = 24.0):
        self.max_messages = max_messages
        self.ttl_hours = ttl_hours
        self._sessions: dict[str, dict[str, Any]] = {}

    def get_history(self, user_id: str) -> list[dict[str, str]]:
        """Get conversation history for a user. Returns [] if expired."""
        session = self._sessions.get(user_id)
        if not session:
            return []
        
        # Check TTL
        age_hours = (time.time() - session["created"]) / 3600
        if age_hours > self.ttl_hours:
            del self._sessions[user_id]
            return []
        
        return session["messages"]

    def add_message(self, user_id: str, role: str, content: str) -> None:
        """Add a message to the user's conversation history."""
        if user_id not in self._sessions:
            self._sessions[user_id] = {
                "created": time.time(),
                "messages": [],
            }
        
        session = self._sessions[user_id]
        session["messages"].append({
            "role": role,
            "content": content,
        })
        
        # Trim to max_messages (keep system message + recent)
        if len(session["messages"]) > self.max_messages:
            # Keep first (system) and last N-1
            session["messages"] = (
                session["messages"][:1] + session["messages"][-(self.max_messages - 1):]
            )

    def clear(self, user_id: str) -> None:
        """Clear a user's conversation history."""
        self._sessions.pop(user_id, None)

    def clear_all(self) -> None:
        """Clear all conversation histories."""
        self._sessions.clear()

    @property
    def active_sessions(self) -> int:
        """Number of active user sessions."""
        return len(self._sessions)


# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function calling format)
# ---------------------------------------------------------------------------

# These map tool names to their OpenAI function schemas.
# The superagent uses these to tell the LLM what tools are available.
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    # ── Geological ──────────────────────────────────────────────────
    "geological_database_query": {
        "type": "function",
        "function": {
            "name": "geological_database_query",
            "description": "Query geological data for Kenya — rock types, formations, mineral deposits, structural features. Use this for any question about what's underground.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number", "description": "Latitude of the location"},
                    "longitude": {"type": "number", "description": "Longitude of the location"},
                    "radius_km": {"type": "number", "description": "Search radius in km", "default": 10},
                    "query_type": {"type": "string", "enum": ["all", "rocks", "minerals", "structures"], "default": "all"},
                },
                "required": ["latitude", "longitude"],
            },
        },
    },
    "gempy_3d_model": {
        "type": "function",
        "function": {
            "name": "gempy_3d_model",
            "description": "Create a 3D geological model using GemPy. Use when the user wants to visualize subsurface geology or model geological formations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "extent": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "[xmin, xmax, ymin, ymax, zmin, zmax] in meters",
                    },
                    "resolution": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "[nx, ny, nz] grid resolution, default [50,50,50]",
                    },
                    "surface_points": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number"},
                                "y": {"type": "number"},
                                "z": {"type": "number"},
                                "formation": {"type": "string"},
                            },
                        },
                        "description": "Known surface point locations",
                    },
                },
                "required": ["extent"],
            },
        },
    },
    "simpeg_inversion": {
        "type": "function",
        "function": {
            "name": "simpeg_inversion",
            "description": "Run geophysical inversion (magnetic, resistivity, gravity) using SimPEG. Use when the user has geophysical survey data to process.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_type": {"type": "string", "enum": ["magnetic", "resistivity", "gravity"], "description": "Type of geophysical data"},
                    "data_path": {"type": "string", "description": "Path to geophysical data file"},
                    "mesh_size": {"type": "integer", "description": "Number of mesh cells per axis", "default": 64},
                    "inversion_type": {"type": "string", "description": "Physical property to invert for", "default": "susceptibility"},
                },
                "required": ["data_type"],
            },
        },
    },
    "mindat_query": {
        "type": "function",
        "function": {
            "name": "mindat_query",
            "description": "Query Mindat.org for mineral occurrence data near a location. Use to find known mineral occurrences in an area.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                    "radius_km": {"type": "number", "default": 25},
                    "mineral": {"type": "string", "description": "Specific mineral to search for"},
                },
                "required": ["latitude", "longitude"],
            },
        },
    },
    "usgs_mrdata_query": {
        "type": "function",
        "function": {
            "name": "usgs_mrdata_query",
            "description": "Query USGS Mineral Resources Data System for mineral deposits near a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                    "radius_km": {"type": "number", "default": 50},
                    "commodity": {"type": "string", "description": "Specific commodity to search for"},
                },
                "required": ["latitude", "longitude"],
            },
        },
    },
    # ── Satellite ───────────────────────────────────────────────────
    "sentinel2_download": {
        "type": "function",
        "function": {
            "name": "sentinel2_download",
            "description": "Download Sentinel-2 satellite imagery for a location. Use for remote sensing analysis of land.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                    "date_range": {"type": "string", "description": "Date range, e.g. '2024-01-01/2024-06-01'"},
                    "cloud_cover_max": {"type": "number", "description": "Max cloud cover percentage", "default": 20},
                },
                "required": ["latitude", "longitude"],
            },
        },
    },
    "calculate_ndvi": {
        "type": "function",
        "function": {
            "name": "calculate_ndvi",
            "description": "Calculate NDVI (vegetation index) from satellite data. Useful for detecting vegetation patterns related to mineralization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "Path to Sentinel-2 image"},
                    "output_path": {"type": "string", "description": "Path for output raster"},
                },
                "required": ["image_path"],
            },
        },
    },
    "calculate_clay_ratio": {
        "type": "function",
        "function": {
            "name": "calculate_clay_ratio",
            "description": "Calculate clay mineral ratio from satellite data. Clay alteration zones often indicate hydrothermal mineral deposits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string"},
                    "output_path": {"type": "string"},
                },
                "required": ["image_path"],
            },
        },
    },
    "calculate_iron_oxide_ratio": {
        "type": "function",
        "function": {
            "name": "calculate_iron_oxide_ratio",
            "description": "Calculate iron oxide ratio from satellite data. Iron oxides can indicate gold and copper mineralization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string"},
                    "output_path": {"type": "string"},
                },
                "required": ["image_path"],
            },
        },
    },
    "cloud_cover_check": {
        "type": "function",
        "function": {
            "name": "cloud_cover_check",
            "description": "Check cloud cover percentage for satellite imagery at a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                    "date": {"type": "string", "description": "Date to check (YYYY-MM-DD)"},
                },
                "required": ["latitude", "longitude"],
            },
        },
    },
    # ── Market ──────────────────────────────────────────────────────
    "get_commodity_price": {
        "type": "function",
        "function": {
            "name": "get_commodity_price",
            "description": "Get current commodity price (gold, silver, copper, platinum, palladium). Uses multi-provider fallback chain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "commodity": {"type": "string", "enum": ["gold", "silver", "copper", "platinum", "palladium"], "description": "Commodity name"},
                    "currency": {"type": "string", "default": "USD", "description": "Currency for price"},
                },
                "required": ["commodity"],
            },
        },
    },
    "get_price_history": {
        "type": "function",
        "function": {
            "name": "get_price_history",
            "description": "Get historical price data for a commodity. Use for trend analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "commodity": {"type": "string", "enum": ["gold", "silver", "copper", "platinum", "palladium"]},
                    "period": {"type": "string", "description": "Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)", "default": "1y"},
                    "interval": {"type": "string", "description": "Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)", "default": "1mo"},
                },
                "required": ["commodity"],
            },
        },
    },
    # ── Quantum ─────────────────────────────────────────────────────
    "quantum_mineral_classify": {
        "type": "function",
        "function": {
            "name": "quantum_mineral_classify",
            "description": "Classify minerals using quantum kernel methods. Advanced ML for mineral identification from spectral data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "features": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Feature vector (e.g. XRF spectral intensities)",
                    },
                    "mineral_classes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Candidate mineral classes",
                        "default": ["gold", "pyrite", "chalcopyrite", "galena", "magnetite"],
                    },
                },
                "required": ["features"],
            },
        },
    },
    "quantum_drill_optimize": {
        "type": "function",
        "function": {
            "name": "quantum_drill_optimize",
            "description": "Optimize drill target locations using quantum optimization (QAOA). Use for exploration planning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "targets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number"},
                                "y": {"type": "number"},
                                "priority": {"type": "number"},
                            },
                        },
                        "description": "Candidate drill targets with coordinates and priority",
                    },
                    "budget": {"type": "number", "description": "Number of drill holes allowed"},
                    "min_distance": {"type": "number", "description": "Minimum distance between drill holes (meters)", "default": 100},
                },
                "required": ["targets", "budget"],
            },
        },
    },
}


# ---------------------------------------------------------------------------
# The Superagent
# ---------------------------------------------------------------------------

class SovereignResourceDAO:
    """
    ONE agent. Many tools. No orchestrator.

    The model decides which tool to use via OpenAI function calling.
    There are no specialist agents routing through an orchestrator.
    There is one intelligent entity that has access to geological,
    satellite, market, legal, financial, and quantum tools.

    Jensen Huang: "That super agent is not trying to book me travel.
    It's just trying to optimize our supply chain."
    """

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = config_dir or str(Path(__file__).parent / "config")

        # Load configuration
        self.config = self._load_config()

        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        self._register_all_tools()

        # Conversation memory (per-user)
        memory_config = self.config.get("memory", {}).get("session_memory", {})
        self.memory = ConversationMemory(
            max_messages=memory_config.get("max_messages", 20),
            ttl_hours=memory_config.get("ttl_hours", 24),
        )

        # Model configuration
        agent_config = self.config.get("agent", {})
        self.model = agent_config.get("model", "nvidia/nemotron-3-ultra")
        self.fallback_model = agent_config.get("fallback_model", "meta/llama-3.1-405b-instruct")
        self.fast_model = agent_config.get("fast_model", "meta/llama-3.1-8b-instruct")
        self.system_prompt = agent_config.get("system_prompt", self._default_system_prompt())
        self.max_tool_calls = agent_config.get("max_tool_calls", 10)

        logger.info(
            "Sovereign Resource DAO initialized: model=%s, tools=%d",
            self.model,
            len(self._available_tools()),
        )

        # Shared HTTP client (avoids creating new connections per request)
        self._http_client: Optional[httpx.AsyncClient] = None

    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create the shared async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client

    async def close(self):
        """Clean up resources."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    # -- Configuration -------------------------------------------------------

    def _load_config(self) -> dict[str, Any]:
        """Load agent.yaml configuration."""
        config_path = Path(self.config_dir) / "agent.yaml"
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        logger.warning("No agent.yaml found at %s — using defaults", config_path)
        return {}

    def _default_system_prompt(self) -> str:
        return (
            "You are a Sovereign Resource DAO — an AI-powered digital geologist "
            "built for Kenyan miners. You help miners understand what minerals "
            "are on their land, what they're worth, and how to negotiate fair deals.\n\n"
            "You speak Swahili first, English second. You are honest about "
            "uncertainty — you never claim certainty about mineral identification "
            "from photos alone. You always recommend physical verification for "
            "economic decisions.\n\n"
            "You have access to specialized tools for geological analysis, "
            "satellite imagery, mineral identification, market data, and quantum "
            "computing. You use these tools to help miners — you don't guess, "
            "you analyze.\n\n"
            "Your goal: End mineral exploitation in Kenya by giving miners "
            "the same data that foreign companies use to exploit them.\n\n"
            "IMPORTANT RULES:\n"
            "1. Use the provided tools via function calling — never fabricate tool outputs.\n"
            "2. Always report calibrated confidence — never claim certainty.\n"
            "3. If evidence is insufficient, say so explicitly.\n"
            "4. For economic minerals, ALWAYS recommend physical verification.\n"
            "5. Pyrite (FeS2) must NEVER be identified as gold (Au).\n"
            "6. Photo-only mineral ID cannot exceed 65% confidence.\n"
            "7. Include Swahili disclaimers where appropriate.\n"
        )

    # -- Tool registration ---------------------------------------------------

    def _register_all_tools(self) -> None:
        """Register all tool handlers with the registry."""
        from .tools.geological import register_geological_tools
        from .tools.satellite import register_satellite_tools
        from .tools.market import register_market_tools
        from .tools.quantum import register_quantum_tools

        register_geological_tools(self.tool_registry)
        register_satellite_tools(self.tool_registry)
        register_market_tools(self.tool_registry)
        register_quantum_tools(self.tool_registry)

        registered = sum(
            1 for name in self.tool_registry._tools
            if name in self.tool_registry._handlers
        )
        logger.info("Registered %d tool handlers", registered)

    def _available_tools(self) -> list[dict[str, Any]]:
        """Get OpenAI function calling schemas for all registered tools."""
        tools = []
        for tool_name in self.tool_registry._handlers:
            schema = TOOL_SCHEMAS.get(tool_name)
            if schema:
                tools.append(schema)
            else:
                # Auto-generate a basic schema for tools not in TOOL_SCHEMAS
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": f"Execute {tool_name}",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                        },
                    },
                })
        return tools

    # -- LLM calling --------------------------------------------------------

    async def _call_llm(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Call the LLM with messages and tools.
        Uses NVIDIA NIM via OpenAI-compatible API.
        """
        import httpx

        model = model or self.model
        api_key = os.environ.get("NVIDIA_API_KEY", "")
        base_url = os.environ.get("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")

        if not api_key:
            logger.warning("No NVIDIA_API_KEY — using mock LLM")
            return self._mock_llm_response(messages)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4096,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        client = self._get_http_client()
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]["message"]
        return dict(choice)

    def _mock_llm_response(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Mock LLM response for testing without API keys."""
        last_msg = messages[-1]["content"] if messages else ""
        return {
            "role": "assistant",
            "content": (
                f"Analysis of: {last_msg[:200]}\n\n"
                "⚠️ This is a mock response. Configure NVIDIA_API_KEY for real analysis.\n"
                "Confidence: 30% (mock mode — not calibrated)\n\n"
                "Hii si uthibitisho wa maabara. Tafadhali thibitisha na mtihani wa kimwili."
            ),
            "tool_calls": [],
        }

    # -- Tool execution ------------------------------------------------------

    async def _execute_tool(self, tool_call: dict[str, Any]) -> str:
        """Execute a single tool call and return the result as JSON string."""
        func = tool_call.get("function", {})
        tool_name = func.get("name", "")
        raw_args = func.get("arguments", "{}")

        # Parse arguments (LLMs sometimes send JSON strings)
        if isinstance(raw_args, str):
            try:
                arguments = json.loads(raw_args)
            except json.JSONDecodeError:
                return json.dumps({"error": f"Invalid JSON arguments: {raw_args}"})
        else:
            arguments = raw_args

        logger.info("Executing tool: %s(%s)", tool_name, json.dumps(arguments)[:200])

        try:
            result = await self.tool_registry.execute(tool_name, arguments)
            return json.dumps(result, default=str)
        except Exception as e:
            logger.exception("Tool %s failed", tool_name)
            return json.dumps({"error": f"{type(e).__name__}: {e}"})

    # -- Main chat loop ------------------------------------------------------

    async def chat(
        self,
        user_message: str,
        user_id: str = "default",
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Main entry point. Send a message, get a response.

        The superagent:
        1. Builds conversation with system prompt + history + new message
        2. Calls the LLM with available tools
        3. If LLM wants to call a tool → execute it → feed result back
        4. Repeat until LLM produces a final text response
        5. Store the exchange in memory

        Args:
            user_message: The user's message
            user_id: Unique user identifier (for conversation memory)
            context: Optional context (location, photos, etc.)

        Returns:
            The agent's text response
        """
        # Build messages
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
        ]

        # Add conversation history
        history = self.memory.get_history(user_id)
        messages.extend(history)

        # Add context if provided
        if context:
            context_str = json.dumps(context, indent=2, default=str)
            messages.append({
                "role": "system",
                "content": f"Additional context:\n{context_str}",
            })

        # Add user message
        messages.append({"role": "user", "content": user_message})

        # Get available tools
        tools = self._available_tools()

        # Execution loop: LLM decides when to stop calling tools
        for iteration in range(self.max_tool_calls):
            try:
                response = await self._call_llm(messages, tools)
            except Exception as e:
                logger.exception("LLM call failed on iteration %d", iteration)
                # Try fallback model
                if iteration == 0:
                    try:
                        response = await self._call_llm(messages, tools, model=self.fallback_model)
                    except Exception:
                        return f"Sorry, I'm having trouble connecting to my AI brain. Error: {e}"
                else:
                    return f"Sorry, I encountered an error during analysis: {e}"

            # Check for tool calls
            tool_calls = response.get("tool_calls", [])

            if not tool_calls:
                # No more tools to call — this is the final response
                final_content = response.get("content", "")

                # Store in memory
                self.memory.add_message(user_id, "user", user_message)
                self.memory.add_message(user_id, "assistant", final_content)

                return final_content

            # LLM wants to call tools — execute them
            messages.append(response)  # Add assistant message with tool_calls

            for tc in tool_calls:
                result_str = await self._execute_tool(tc)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": result_str,
                })

        # Max iterations reached — ask LLM for a final summary
        messages.append({
            "role": "user",
            "content": "Please provide your final analysis based on all the tool results above.",
        })
        try:
            response = await self._call_llm(messages, [])  # No tools — force final answer
            final_content = response.get("content", "Analysis incomplete — too many tool calls.")
        except Exception:
            final_content = "Analysis incomplete — reached maximum tool call iterations."

        # Store in memory
        self.memory.add_message(user_id, "user", user_message)
        self.memory.add_message(user_id, "assistant", final_content)

        return final_content

    async def analyze(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
        user_id: str = "default",
    ) -> dict[str, Any]:
        """
        Run an analysis and return a structured result.
        Convenience wrapper around chat() for API use.
        """
        start_time = time.monotonic()
        response = await self.chat(query, user_id=user_id, context=context)
        elapsed = (time.monotonic() - start_time) * 1000

        return {
            "success": True,
            "response": response,
            "model": self.model,
            "user_id": user_id,
            "elapsed_ms": round(elapsed, 1),
            "active_sessions": self.memory.active_sessions,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # -- Convenience methods -------------------------------------------------

    async def identify_mineral(
        self,
        image_description: str,
        location: Optional[dict[str, float]] = None,
        user_id: str = "default",
    ) -> str:
        """Convenience method for mineral identification queries."""
        query = f"Identify this mineral: {image_description}"
        if location:
            query += f" (Location: {location.get('lat')}, {location.get('lon')})"
        return await self.chat(query, user_id=user_id, context=location)

    async def get_price_report(
        self,
        commodities: Optional[list[str]] = None,
        language: str = "english",
        user_id: str = "default",
    ) -> str:
        """Convenience method for commodity price reports."""
        if commodities is None:
            commodities = ["gold", "copper", "silver"]
        query = f"Get current prices for: {', '.join(commodities)}"
        if language == "swahili":
            query += " — Report in Swahili"
        return await self.chat(query, user_id=user_id)

    async def check_compliance(
        self,
        project_type: str,
        mineral: str,
        user_id: str = "default",
    ) -> str:
        """Convenience method for compliance checking."""
        query = (
            f"What are the legal requirements for {project_type} mining "
            f"of {mineral} in Migori County, Kenya?"
        )
        return await self.chat(query, user_id=user_id)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools."""
        return self.tool_registry.list_tools()

    def get_config(self) -> dict[str, Any]:
        """Get the agent configuration (safe to expose)."""
        return {
            "name": self.config.get("agent", {}).get("name", "Sovereign Resource DAO"),
            "model": self.model,
            "fallback_model": self.fallback_model,
            "fast_model": self.fast_model,
            "tools_count": len(self._available_tools()),
            "active_sessions": self.memory.active_sessions,
        }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

async def main():
    """CLI entry point for testing."""
    logging.basicConfig(level=logging.INFO)

    agent = SovereignResourceDAO()

    print("=" * 60)
    print("SOVEREIGN RESOURCE DAO")
    print("ONE agent. MANY tools. NO orchestrator.")
    print("=" * 60)
    print(f"Model: {agent.model}")
    print(f"Tools: {len(agent._available_tools())}")
    print(f"Config: {agent.get_config()}")
    print()

    # Test query
    response = await agent.chat(
        "Is there gold on my land in Nyatike, Migori County? "
        "I found some shiny yellow rocks.",
        user_id="test_user",
    )

    print("RESPONSE:")
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
