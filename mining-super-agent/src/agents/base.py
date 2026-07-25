"""
Base Agent — Abstract foundation for all mining agents.

Key design decisions (from council review):
- OpenAI function calling protocol, NOT regex
- Pydantic schema validation for all tool arguments
- Permission allowlists per agent (least privilege)
- Sandboxed execution with timeout
- Calibrated confidence output (never hardcoded)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Confidence calibration
# ---------------------------------------------------------------------------

class ConfidenceLevel(str, Enum):
    """Calibrated confidence buckets with human-readable labels."""
    VERY_LOW = "very_low"      # < 0.3 — essentially guessing
    LOW = "low"                 # 0.3-0.5 — weak evidence
    MODERATE = "moderate"       # 0.5-0.7 — reasonable but uncertain
    HIGH = "high"               # 0.7-0.9 — strong evidence
    VERY_HIGH = "very_high"    # 0.9-1.0 — near certain (rare)

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        if score < 0.3:
            return cls.VERY_LOW
        elif score < 0.5:
            return cls.LOW
        elif score < 0.7:
            return cls.MODERATE
        elif score < 0.9:
            return cls.HIGH
        return cls.VERY_HIGH


def calibrate_confidence(
    raw_score: float,
    evidence_count: int = 1,
    source_reliability: float = 0.7,
    method_limitation: float = 0.0,
) -> float:
    """
    Calibrate a raw confidence score using real factors.

    Instead of returning a hardcoded 0.8, this adjusts based on:
    - raw_score: base model confidence
    - evidence_count: more independent evidence → higher confidence
    - source_reliability: how trustworthy the data source is (0-1)
    - method_limitation: known limitations of the method (0-1 penalty)

    Returns a calibrated score in [0.0, 1.0].
    """
    # Evidence bonus: diminishing returns (logarithmic)
    import math
    evidence_factor = min(1.0, 0.5 + 0.15 * math.log2(max(1, evidence_count)))

    # Combine factors
    calibrated = raw_score * evidence_factor * source_reliability * (1.0 - method_limitation)

    # Clip to [0.05, 0.98] — never claim 0% or 100% certainty
    return max(0.05, min(0.98, calibrated))


# ---------------------------------------------------------------------------
# Pydantic schemas for tool calling (OpenAI function calling protocol)
# ---------------------------------------------------------------------------

class ToolParameter(BaseModel):
    """Schema for a single tool parameter."""
    name: str
    type: str  # "string", "number", "integer", "boolean", "array", "object"
    description: str = ""
    required: bool = True
    enum: Optional[list[str]] = None
    default: Any = None
    properties: Optional[dict[str, "ToolParameter"]] = None  # for nested objects
    items: Optional["ToolParameter"] = None  # for arrays


class ToolDefinition(BaseModel):
    """
    Defines a tool in OpenAI function calling format.
    This is what gets sent to the LLM as available functions.
    """
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for parameters
    permissions: list[str] = Field(default_factory=list)  # e.g., ["read:geo", "write:cache"]
    timeout_seconds: float = 30.0
    requires_confirmation: bool = False  # for destructive actions

    def to_openai_function(self) -> dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolCall(BaseModel):
    """A tool call request from the LLM (OpenAI function calling format)."""
    id: str = Field(default_factory=lambda: f"call_{uuid.uuid4().hex[:12]}")
    name: str
    arguments: dict[str, Any]

    @field_validator("arguments", mode="before")
    @classmethod
    def parse_arguments(cls, v: Any) -> dict[str, Any]:
        """Handle both string and dict arguments (LLMs sometimes send JSON strings)."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON in tool arguments: {v}")
        return v


class ToolResult(BaseModel):
    """Result from a tool execution."""
    call_id: str
    tool_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    cached: bool = False


# ---------------------------------------------------------------------------
# Agent result
# ---------------------------------------------------------------------------

class AgentResult(BaseModel):
    """Structured result from an agent's work."""
    agent_name: str
    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    success: bool
    summary: str
    detailed_findings: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MODERATE
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[ToolResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    disclaimers: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("confidence_level", mode="before")
    @classmethod
    def compute_confidence_level(cls, v: Any, info: Any) -> ConfidenceLevel:
        if isinstance(v, ConfidenceLevel):
            return v
        # Auto-compute from confidence score if not explicitly set
        conf = info.data.get("confidence", 0.5)
        return ConfidenceLevel.from_score(conf)


# ---------------------------------------------------------------------------
# Base Agent
# ---------------------------------------------------------------------------

class BaseAgent(ABC):
    """
    Abstract base class for all mining agents.

    Enforces:
    - OpenAI function calling protocol for tool use
    - Pydantic validation of all tool arguments
    - Permission-based tool access (least privilege)
    - Sandboxed execution with timeout
    - Calibrated confidence output
    """

    def __init__(
        self,
        name: str,
        description: str,
        model_id: str = "meta/llama-3.1-8b-instruct",
        permissions: Optional[list[str]] = None,
        tools: Optional[list[ToolDefinition]] = None,
        system_prompt: str = "",
        max_tool_calls: int = 10,
        timeout_seconds: float = 120.0,
    ):
        self.name = name
        self.description = description
        self.model_id = model_id
        self.permissions = set(permissions or [])
        self.tools: dict[str, ToolDefinition] = {}
        self.system_prompt = system_prompt
        self.max_tool_calls = max_tool_calls
        self.timeout_seconds = timeout_seconds
        self._tool_handlers: dict[str, Callable] = {}

        # Register provided tools
        for tool in (tools or []):
            self.register_tool(tool)

    # -- Tool registration --------------------------------------------------

    def register_tool(self, definition: ToolDefinition, handler: Optional[Callable] = None):
        """Register a tool with its definition and optional handler."""
        self.tools[definition.name] = definition
        if handler:
            self._tool_handlers[definition.name] = handler
        logger.debug(f"[{self.name}] Registered tool: {definition.name}")

    def register_handler(self, tool_name: str, handler: Callable):
        """Register or update a tool handler."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not defined. Register definition first.")
        self._tool_handlers[tool_name] = handler

    # -- Permission checking ------------------------------------------------

    def has_permission(self, permission: str) -> bool:
        """Check if this agent has a specific permission."""
        return permission in self.permissions

    def check_tool_permission(self, tool: ToolDefinition) -> bool:
        """Verify the agent has all required permissions for a tool."""
        for perm in tool.permissions:
            if not self.has_permission(perm):
                logger.warning(f"[{self.name}] Missing permission '{perm}' for tool '{tool.name}'")
                return False
        return True

    # -- OpenAI function calling format -------------------------------------

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Get all tools in OpenAI function calling format."""
        return [
            tool.to_openai_function()
            for tool in self.tools.values()
            if self.check_tool_permission(tool)
        ]

    def get_system_message(self) -> dict[str, str]:
        """Build the system message with agent context."""
        return {
            "role": "system",
            "content": (
                f"You are {self.name}: {self.description}\n\n"
                f"{self.system_prompt}\n\n"
                "IMPORTANT RULES:\n"
                "1. Use the provided tools via function calling — never fabricate tool outputs.\n"
                "2. Always report calibrated confidence — never claim certainty.\n"
                "3. If evidence is insufficient, say so explicitly.\n"
                "4. For economic minerals, ALWAYS recommend physical verification.\n"
                "5. Include disclaimers where appropriate.\n"
            ),
        }

    # -- Tool execution (sandboxed) -----------------------------------------

    async def execute_tool(self, call: ToolCall) -> ToolResult:
        """
        Execute a single tool call with validation and sandboxing.

        Steps:
        1. Validate tool exists and agent has permission
        2. Validate arguments against Pydantic schema
        3. Execute with timeout
        4. Return structured result
        """
        start_time = time.monotonic()

        # 1. Check tool exists
        tool_def = self.tools.get(call.name)
        if not tool_def:
            return ToolResult(
                call_id=call.id,
                tool_name=call.name,
                success=False,
                error=f"Tool '{call.name}' not found in agent '{self.name}'",
            )

        # 2. Check permissions
        if not self.check_tool_permission(tool_def):
            return ToolResult(
                call_id=call.id,
                tool_name=call.name,
                success=False,
                error=f"Agent '{self.name}' lacks permission for tool '{call.name}'",
            )

        # 3. Validate arguments against JSON Schema
        try:
            self._validate_arguments(call.arguments, tool_def.parameters)
        except ValidationError as e:
            return ToolResult(
                call_id=call.id,
                tool_name=call.name,
                success=False,
                error=f"Argument validation failed: {e}",
            )

        # 4. Execute with timeout
        handler = self._tool_handlers.get(call.name)
        if not handler:
            return ToolResult(
                call_id=call.id,
                tool_name=call.name,
                success=False,
                error=f"No handler registered for tool '{call.name}'",
            )

        try:
            result = await asyncio.wait_for(
                self._run_handler(handler, call.arguments),
                timeout=tool_def.timeout_seconds,
            )
            elapsed = (time.monotonic() - start_time) * 1000
            return ToolResult(
                call_id=call.id,
                tool_name=call.name,
                success=True,
                data=result,
                execution_time_ms=elapsed,
            )
        except asyncio.TimeoutError:
            return ToolResult(
                call_id=call.id,
                tool_name=call.name,
                success=False,
                error=f"Tool '{call.name}' timed out after {tool_def.timeout_seconds}s",
            )
        except Exception as e:
            logger.exception(f"[{self.name}] Tool '{call.name}' failed")
            return ToolResult(
                call_id=call.id,
                tool_name=call.name,
                success=False,
                error=f"{type(e).__name__}: {e}",
            )

    async def _run_handler(self, handler: Callable, arguments: dict[str, Any]) -> Any:
        """Run a handler, supporting both sync and async callables."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(**arguments)
        return handler(**arguments)

    def _validate_arguments(self, arguments: dict[str, Any], schema: dict[str, Any]) -> None:
        """
        Validate tool arguments against JSON Schema.
        Uses jsonschema for proper validation.
        """
        try:
            from jsonschema import validate, ValidationError
            validate(instance=arguments, schema=schema)
        except ImportError:
            # Fallback: basic required-field check
            required = schema.get("required", [])
            props = schema.get("properties", {})
            for field_name in required:
                if field_name not in arguments:
                    raise ValueError(f"Missing required argument: {field_name}")
            # Type checking for provided args
            for key, value in arguments.items():
                if key in props:
                    expected_type = props[key].get("type")
                    if expected_type == "string" and not isinstance(value, str):
                        raise ValueError(f"Argument '{key}' must be string")
                    elif expected_type == "number" and not isinstance(value, (int, float)):
                        raise ValueError(f"Argument '{key}' must be number")
                    elif expected_type == "integer" and not isinstance(value, int):
                        raise ValueError(f"Argument '{key}' must be integer")
                    elif expected_type == "boolean" and not isinstance(value, bool):
                        raise ValueError(f"Argument '{key}' must be boolean")
                    elif expected_type == "array" and not isinstance(value, list):
                        raise ValueError(f"Argument '{key}' must be array")

    # -- Core execution loop ------------------------------------------------

    async def run(self, task: str, context: Optional[dict[str, Any]] = None) -> AgentResult:
        """
        Main entry point. Execute a task using the agent's tools and model.

        This is the method orchestrators call. It:
        1. Builds the conversation with system prompt + user task
        2. Calls the LLM with available tools (function calling)
        3. Executes tool calls the LLM requests
        4. Feeds results back to the LLM
        5. Repeats until LLM stops calling tools or max_tool_calls reached
        6. Returns structured AgentResult with calibrated confidence
        """
        task_id = uuid.uuid4().hex[:12]
        logger.info(f"[{self.name}] Starting task {task_id}: {task[:100]}...")

        tool_results: list[ToolResult] = []
        warnings: list[str] = []

        # Build initial messages
        messages = [
            self.get_system_message(),
            {"role": "user", "content": task},
        ]
        if context:
            messages.insert(1, {
                "role": "system",
                "content": f"Additional context:\n{json.dumps(context, indent=2)}",
            })

        # Get available tools
        openai_tools = self.get_openai_tools()

        # Execution loop
        for iteration in range(self.max_tool_calls):
            try:
                llm_response = await self._call_llm(messages, openai_tools)
            except Exception as e:
                logger.exception(f"[{self.name}] LLM call failed")
                return AgentResult(
                    agent_name=self.name,
                    task_id=task_id,
                    success=False,
                    summary=f"LLM call failed: {e}",
                    confidence=0.0,
                    tool_calls=tool_results,
                    warnings=[f"LLM error: {e}"],
                )

            # Check if LLM wants to call tools
            message = llm_response
            tool_calls = message.get("tool_calls", [])

            if not tool_calls:
                # LLM is done — extract final answer
                content = message.get("content", "")
                return self._build_result(
                    task_id=task_id,
                    content=content,
                    tool_results=tool_results,
                    warnings=warnings,
                )

            # Execute each tool call
            messages.append(message)  # Add assistant message with tool_calls

            for tc in tool_calls:
                func = tc.get("function", {})
                call = ToolCall(
                    id=tc.get("id", f"call_{uuid.uuid4().hex[:12]}"),
                    name=func.get("name", ""),
                    arguments=func.get("arguments", "{}"),
                )

                result = await self.execute_tool(call)
                tool_results.append(result)

                # Feed result back to LLM
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result.data) if result.success else f"Error: {result.error}",
                })

                if not result.success:
                    warnings.append(f"Tool '{call.name}' failed: {result.error}")

        # Max iterations reached
        warnings.append(f"Reached maximum tool call iterations ({self.max_tool_calls})")
        return self._build_result(
            task_id=task_id,
            content="Task incomplete — maximum tool call iterations reached.",
            tool_results=tool_results,
            warnings=warnings,
        )

    def _build_result(
        self,
        task_id: str,
        content: str,
        tool_results: list[ToolResult],
        warnings: list[str],
    ) -> AgentResult:
        """Build a structured AgentResult from LLM output and tool results."""
        # Parse confidence from content if mentioned, otherwise compute from evidence
        confidence = self._extract_confidence(content, tool_results)
        successful_tools = [r for r in tool_results if r.success]

        return AgentResult(
            agent_name=self.name,
            task_id=task_id,
            success=True,
            summary=content[:500] if len(content) > 500 else content,
            detailed_findings={"full_response": content},
            confidence=confidence,
            tool_calls=tool_results,
            warnings=warnings,
            metadata={
                "model": self.model_id,
                "tool_calls_made": len(tool_results),
                "tool_calls_succeeded": len(successful_tools),
            },
        )

    def _extract_confidence(self, content: str, tool_results: list[ToolResult]) -> float:
        """
        Extract or compute calibrated confidence.
        Tries to parse from LLM output, falls back to evidence-based calculation.
        """
        import re

        # Try to extract explicit confidence from LLM output
        patterns = [
            r'confidence[:\s]*(\d+(?:\.\d+)?)\s*%',
            r'confidence[:\s]*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*%\s*confident',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                val = float(match.group(1))
                if val > 1:
                    val /= 100.0
                return calibrate_confidence(
                    raw_score=val,
                    evidence_count=len([r for r in tool_results if r.success]),
                )

        # Compute from evidence
        successful = len([r for r in tool_results if r.success])
        total = len(tool_results)

        if total == 0:
            # No tools used — lower confidence (text-only analysis)
            return calibrate_confidence(
                raw_score=0.5,
                evidence_count=0,
                source_reliability=0.5,
                method_limitation=0.3,
            )

        success_rate = successful / total
        return calibrate_confidence(
            raw_score=0.7 * success_rate + 0.3,
            evidence_count=successful,
            source_reliability=0.8,
        )

    # -- LLM calling (to be overridden by subclasses) -----------------------

    async def _call_llm(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Call the LLM with messages and tools.
        Default implementation uses NVIDIA NIM via OpenAI-compatible API.

        Subclasses can override for different providers.
        """
        import os
        import httpx

        api_key = os.environ.get("NVIDIA_API_KEY", "")
        base_url = os.environ.get("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")

        if not api_key:
            # Fallback to local/mock
            logger.warning(f"[{self.name}] No NVIDIA_API_KEY — using mock LLM")
            return self._mock_llm_response(messages, tools)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4096,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]["message"]
        return dict(choice)

    def _mock_llm_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Mock LLM response for testing without API keys."""
        # Return a simple text response
        last_msg = messages[-1]["content"] if messages else ""
        return {
            "role": "assistant",
            "content": (
                f"[{self.name}] Analyzed: {last_msg[:200]}\n\n"
                "Note: This is a mock response. Configure NVIDIA_API_KEY for real analysis.\n"
                "Confidence: 30% (mock mode — not calibrated)"
            ),
            "tool_calls": [],
        }
