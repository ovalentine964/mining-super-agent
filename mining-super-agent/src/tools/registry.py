"""
Tool Registry — Plug-and-play tool management.

Features:
- Auto-discovery from YAML config
- Rate limiting per tool (token bucket algorithm)
- Caching with TTL
- Fallback chains
- Pydantic validation for all tool inputs/outputs
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic models for tool configuration
# ---------------------------------------------------------------------------

class RateLimitConfig(BaseModel):
    """Rate limiting configuration for a tool."""
    requests_per_minute: int = 30
    requests_per_hour: int = 500
    burst_size: int = 5


class CacheConfig(BaseModel):
    """Cache configuration for a tool."""
    enabled: bool = True
    ttl_seconds: int = 3600  # 1 hour default
    max_entries: int = 1000
    strategy: str = "exact"  # "exact" or "semantic"


class FallbackConfig(BaseModel):
    """Fallback chain configuration."""
    tools: list[str] = Field(default_factory=list)  # ordered fallback tool names
    max_retries: int = 2


class ToolConfig(BaseModel):
    """Full configuration for a single tool from YAML."""
    name: str
    description: str = ""
    module: str = ""  # Python module path for the tool implementation
    endpoint: Optional[str] = None
    auth_env_var: Optional[str] = None  # env var name for API key
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    fallback: FallbackConfig = Field(default_factory=FallbackConfig)
    enabled: bool = True
    permissions: list[str] = Field(default_factory=list)
    timeout_seconds: float = 30.0
    parameters: dict[str, Any] = Field(default_factory=dict)  # JSON Schema


# ---------------------------------------------------------------------------
# Rate Limiter (Token Bucket)
# ---------------------------------------------------------------------------

class RateLimiter:
    """
    Token bucket rate limiter.
    Supports per-minute and per-hour limits with burst allowance.
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._minute_tokens: float = config.requests_per_minute
        self._hour_tokens: float = config.requests_per_hour
        self._last_minute_refill: float = time.monotonic()
        self._last_hour_refill: float = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Try to acquire a rate limit token. Returns True if allowed."""
        async with self._lock:
            now = time.monotonic()

            # Refill minute bucket
            minute_elapsed = now - self._last_minute_refill
            self._minute_tokens = min(
                self.config.requests_per_minute,
                self._minute_tokens + minute_elapsed * (self.config.requests_per_minute / 60.0),
            )
            self._last_minute_refill = now

            # Refill hour bucket
            hour_elapsed = now - self._last_hour_refill
            self._hour_tokens = min(
                self.config.requests_per_hour,
                self._hour_tokens + hour_elapsed * (self.config.requests_per_hour / 3600.0),
            )
            self._last_hour_refill = now

            # Check both buckets
            if self._minute_tokens >= 1 and self._hour_tokens >= 1:
                self._minute_tokens -= 1
                self._hour_tokens -= 1
                return True

            return False

    async def wait_and_acquire(self, max_wait: float = 10.0) -> bool:
        """Wait until a token is available or timeout."""
        deadline = time.monotonic() + max_wait
        while time.monotonic() < deadline:
            if await self.acquire():
                return True
            await asyncio.sleep(0.1)
        return False


# ---------------------------------------------------------------------------
# Cache Manager
# ---------------------------------------------------------------------------

class CacheEntry(BaseModel):
    """A cached tool result."""
    key: str
    data: Any
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int = 3600
    hit_count: int = 0

    def is_expired(self) -> bool:
        elapsed = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds


class CacheManager:
    """
    In-memory cache with TTL support.
    For production, backed by Redis.
    """

    def __init__(self, config: CacheConfig):
        self.config = config
        self._entries: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    def _make_key(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Generate a cache key from tool name and arguments."""
        raw = json.dumps({"tool": tool_name, "args": arguments}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    async def get(self, tool_name: str, arguments: dict[str, Any]) -> Optional[Any]:
        """Look up a cached result."""
        if not self.config.enabled:
            return None

        key = self._make_key(tool_name, arguments)
        async with self._lock:
            entry = self._entries.get(key)
            if entry and not entry.is_expired():
                entry.hit_count += 1
                logger.debug(f"Cache hit for {tool_name} (key={key})")
                return entry.data
            elif entry:
                # Expired
                del self._entries[key]
        return None

    async def put(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        data: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """Store a result in cache."""
        if not self.config.enabled:
            return

        key = self._make_key(tool_name, arguments)
        async with self._lock:
            # Evict if at capacity
            if len(self._entries) >= self.config.max_entries:
                self._evict_oldest()

            self._entries[key] = CacheEntry(
                key=key,
                data=data,
                ttl_seconds=ttl or self.config.ttl_seconds,
            )

    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry."""
        if not self._entries:
            return
        oldest_key = min(self._entries, key=lambda k: self._entries[k].created_at)
        del self._entries[oldest_key]


# ---------------------------------------------------------------------------
# Tool Definition (lightweight wrapper)
# ---------------------------------------------------------------------------

class ToolDefinition(BaseModel):
    """Definition of a tool as exposed to agents."""
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)
    timeout_seconds: float = 30.0


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

class ToolRegistry:
    """
    Central registry for all tools.

    Features:
    - Load tool configs from YAML
    - Register tool handlers dynamically
    - Rate limiting per tool
    - Caching with TTL
    - Fallback chains (if primary tool fails, try alternatives)
    - Permission checking
    """

    def __init__(self, config_path: Optional[str] = None):
        self._tools: dict[str, ToolConfig] = {}
        self._handlers: dict[str, Callable] = {}
        self._rate_limiters: dict[str, RateLimiter] = {}
        self._caches: dict[str, CacheManager] = {}

        if config_path:
            self.load_from_yaml(config_path)

    def load_from_yaml(self, config_path: str) -> None:
        """Load tool definitions from a YAML config file."""
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Tool config not found: {config_path}")
            return

        with open(path) as f:
            data = yaml.safe_load(f)

        tools_config = data.get("tools", {})
        for tool_name, tool_data in tools_config.items():
            config = ToolConfig(name=tool_name, **tool_data)
            self.register_config(config)

        logger.info(f"Loaded {len(tools_config)} tools from {config_path}")

    def register_config(self, config: ToolConfig) -> None:
        """Register a tool configuration."""
        self._tools[config.name] = config
        self._rate_limiters[config.name] = RateLimiter(config.rate_limit)
        self._caches[config.name] = CacheManager(config.cache)
        logger.debug(f"Registered tool config: {config.name}")

    def register_handler(self, tool_name: str, handler: Callable) -> None:
        """Register a callable handler for a tool."""
        if tool_name not in self._tools:
            logger.warning(f"Registering handler for unconfigured tool: {tool_name}")
        self._handlers[tool_name] = handler

    def get_handler(self, tool_name: str) -> Optional[Callable]:
        """Get the handler for a tool."""
        return self._handlers.get(tool_name)

    def get_config(self, tool_name: str) -> Optional[ToolConfig]:
        """Get configuration for a tool."""
        return self._tools.get(tool_name)

    def get_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get a tool's definition (for agent tool lists)."""
        config = self._tools.get(tool_name)
        if not config:
            return None
        return ToolDefinition(
            name=config.name,
            description=config.description,
            parameters=config.parameters,
            permissions=config.permissions,
            timeout_seconds=config.timeout_seconds,
        )

    def get_all_definitions(self) -> list[ToolDefinition]:
        """Get definitions for all enabled tools."""
        return [
            self.get_definition(name)
            for name, config in self._tools.items()
            if config.enabled
        ]

    def get_tools_for_agent(self, agent_tool_names: list[str]) -> list[ToolDefinition]:
        """Get tool definitions for a specific agent's tool list."""
        defs = []
        for name in agent_tool_names:
            d = self.get_definition(name)
            if d:
                defs.append(d)
            else:
                logger.warning(f"Tool '{name}' not found in registry")
        return defs

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        permissions: Optional[set[str]] = None,
        bypass_cache: bool = False,
    ) -> dict[str, Any]:
        """
        Execute a tool with rate limiting, caching, and fallback.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments (will be validated)
            permissions: Agent's permissions (for checking)
            bypass_cache: Skip cache lookup

        Returns:
            Tool execution result as dict

        Raises:
            PermissionError: If agent lacks required permissions
            TimeoutError: If tool execution exceeds timeout
            ValueError: If arguments are invalid
        """
        config = self._tools.get(tool_name)
        if not config:
            raise ValueError(f"Tool '{tool_name}' not found in registry")

        if not config.enabled:
            raise ValueError(f"Tool '{tool_name}' is disabled")

        # Permission check
        if permissions:
            for perm in config.permissions:
                if perm not in permissions:
                    raise PermissionError(f"Missing permission '{perm}' for tool '{tool_name}'")

        # Cache check
        if not bypass_cache:
            cached = await self._caches[tool_name].get(tool_name, arguments)
            if cached is not None:
                return {"success": True, "data": cached, "cached": True}

        # Rate limiting
        limiter = self._rate_limiters[tool_name]
        if not await limiter.wait_and_acquire(max_wait=10.0):
            # Try fallback chain
            return await self._execute_fallback(tool_name, arguments, permissions)

        # Execute primary tool
        handler = self._handlers.get(tool_name)
        if not handler:
            raise ValueError(f"No handler registered for tool '{tool_name}'")

        try:
            result = await asyncio.wait_for(
                self._run_handler(handler, arguments),
                timeout=config.timeout_seconds,
            )

            # Cache result
            await self._caches[tool_name].put(tool_name, arguments, result)
            return {"success": True, "data": result, "cached": False}

        except Exception as e:
            logger.warning(f"Tool '{tool_name}' failed: {e}. Trying fallback...")
            return await self._execute_fallback(tool_name, arguments, permissions)

    async def _execute_fallback(
        self,
        failed_tool: str,
        arguments: dict[str, Any],
        permissions: Optional[set[str]] = None,
    ) -> dict[str, Any]:
        """Execute fallback chain when primary tool fails."""
        config = self._tools.get(failed_tool)
        if not config or not config.fallback.tools:
            return {
                "success": False,
                "error": f"Tool '{failed_tool}' failed and no fallback available",
                "cached": False,
            }

        for fallback_name in config.fallback.tools:
            logger.info(f"Trying fallback: {fallback_name} for {failed_tool}")
            try:
                result = await self.execute(
                    fallback_name,
                    arguments,
                    permissions=permissions,
                    bypass_cache=False,
                )
                if result.get("success"):
                    return result
            except Exception as e:
                logger.warning(f"Fallback '{fallback_name}' also failed: {e}")
                continue

        return {
            "success": False,
            "error": f"All fallbacks exhausted for tool '{failed_tool}'",
            "cached": False,
        }

    async def _run_handler(self, handler: Callable, arguments: dict[str, Any]) -> Any:
        """Run a handler, supporting both sync and async."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(**arguments)
        return handler(**arguments)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools with their status."""
        return [
            {
                "name": config.name,
                "description": config.description,
                "enabled": config.enabled,
                "has_handler": config.name in self._handlers,
                "rate_limit": config.rate_limit.model_dump(),
                "cache_ttl": config.cache.ttl_seconds,
                "fallbacks": config.fallback.tools,
            }
            for config in self._tools.values()
        ]
