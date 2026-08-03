"""Tests for tool registry."""

import pytest
from src.tools.registry import ToolRegistry, ToolConfig, RateLimitConfig, CacheConfig


def test_tool_config_creation():
    config = ToolConfig(name="test_tool", description="A test tool")
    assert config.name == "test_tool"
    assert config.enabled is True
    assert config.timeout_seconds == 30.0


def test_registry_register_config():
    registry = ToolRegistry()
    config = ToolConfig(name="test_tool")
    registry.register_config(config)
    assert "test_tool" in registry._tools
    assert "test_tool" in registry._rate_limiters


def test_registry_list_tools():
    registry = ToolRegistry()
    registry.register_config(ToolConfig(name="tool_a"))
    registry.register_config(ToolConfig(name="tool_b"))
    tools = registry.list_tools()
    assert len(tools) == 2


def test_registry_disabled_tool():
    registry = ToolRegistry()
    config = ToolConfig(name="disabled_tool", enabled=False)
    registry.register_config(config)
    defs = registry.get_all_definitions()
    assert len(defs) == 0  # disabled tools excluded
