"""
Tests for the SovereignResourceDAO superagent.

Uses mocked LLM — no NVIDIA_API_KEY required.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.superagent import SovereignResourceDAO, ConversationMemory, TOOL_SCHEMAS


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def memory():
    return ConversationMemory(max_messages=10, ttl_hours=24)


@pytest.fixture
def agent():
    """Create a SovereignResourceDAO with no config dir (uses defaults)."""
    with patch("src.superagent.ToolRegistry"):
        a = SovereignResourceDAO(config_dir="/nonexistent")
    return a


# ── ConversationMemory ─────────────────────────────────────────────

class TestConversationMemory:
    def test_stores_and_retrieves_messages(self, memory):
        memory.add_message("user1", "user", "hello")
        memory.add_message("user1", "assistant", "hi there")

        history = memory.get_history("user1")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "hi there"

    def test_returns_empty_for_unknown_user(self, memory):
        assert memory.get_history("nonexistent") == []

    def test_max_messages_limit(self, memory):
        """Should trim to max_messages, keeping first + last N-1."""
        for i in range(15):
            memory.add_message("user1", "user", f"msg-{i}")

        history = memory.get_history("user1")
        # max_messages is 10, so should be trimmed
        assert len(history) <= 10

    def test_max_messages_preserves_first_message(self, memory):
        """First message (system) should be preserved after trimming."""
        memory.add_message("user1", "system", "system prompt")
        for i in range(15):
            memory.add_message("user1", "user", f"msg-{i}")

        history = memory.get_history("user1")
        assert history[0]["role"] == "system"
        assert history[0]["content"] == "system prompt"

    def test_clear_user_history(self, memory):
        memory.add_message("user1", "user", "hello")
        memory.clear("user1")
        assert memory.get_history("user1") == []

    def test_clear_all(self, memory):
        memory.add_message("user1", "user", "hello")
        memory.add_message("user2", "user", "world")
        memory.clear_all()
        assert memory.active_sessions == 0

    def test_active_sessions_count(self, memory):
        memory.add_message("u1", "user", "a")
        memory.add_message("u2", "user", "b")
        memory.add_message("u3", "user", "c")
        assert memory.active_sessions == 3

    def test_separate_users_have_separate_histories(self, memory):
        memory.add_message("u1", "user", "hello u1")
        memory.add_message("u2", "user", "hello u2")

        assert len(memory.get_history("u1")) == 1
        assert len(memory.get_history("u2")) == 1
        assert memory.get_history("u1")[0]["content"] == "hello u1"
        assert memory.get_history("u2")[0]["content"] == "hello u2"


# ── SovereignResourceDAO Initialization ─────────────────────────────

class TestSovereignResourceDAOInit:
    def test_initializes_with_defaults(self, agent):
        assert agent.model is not None
        assert agent.fallback_model is not None
        assert agent.fast_model is not None
        assert agent.max_tool_calls == 10

    def test_has_memory(self, agent):
        assert isinstance(agent.memory, ConversationMemory)

    def test_has_tool_registry(self, agent):
        assert agent.tool_registry is not None

    def test_get_config_returns_dict(self, agent):
        config = agent.get_config()
        assert isinstance(config, dict)
        assert "model" in config
        assert "tools_count" in config


# ── Tool Schemas ────────────────────────────────────────────────────

class TestToolSchemas:
    def test_tool_schemas_is_nonempty(self):
        assert len(TOOL_SCHEMAS) > 0

    def test_all_schemas_have_function_name(self):
        for name, schema in TOOL_SCHEMAS.items():
            assert "function" in schema, f"{name} missing 'function' key"
            assert "name" in schema["function"], f"{name} function missing 'name'"
            assert schema["function"]["name"] == name, (
                f"Schema name mismatch: key='{name}' vs function.name='{schema['function']['name']}'"
            )

    def test_all_schemas_have_parameters(self):
        for name, schema in TOOL_SCHEMAS.items():
            assert "parameters" in schema["function"], f"{name} missing parameters"

    def test_expected_tools_present(self):
        expected = [
            "geological_database_query",
            "gempy_3d_model",
            "simpeg_inversion",
            "mindat_query",
            "usgs_mrdata_query",
            "sentinel2_download",
            "calculate_ndvi",
            "calculate_clay_ratio",
            "calculate_iron_oxide_ratio",
            "cloud_cover_check",
            "get_commodity_price",
            "get_price_history",
            "quantum_mineral_classify",
            "quantum_drill_optimize",
        ]
        for tool_name in expected:
            assert tool_name in TOOL_SCHEMAS, f"Missing tool schema: {tool_name}"

    def test_tool_schema_names_match_handler_names(self):
        """Every TOOL_SCHEMAS key must equal its function.name — no mismatches."""
        mismatches = []
        for key, schema in TOOL_SCHEMAS.items():
            fn_name = schema.get("function", {}).get("name", "")
            if key != fn_name:
                mismatches.append((key, fn_name))
        assert mismatches == [], f"Tool name mismatches: {mismatches}"


# ── System Prompt ───────────────────────────────────────────────────

class TestSystemPrompt:
    def test_contains_safety_rules(self, agent):
        prompt = agent.system_prompt
        assert "IMPORTANT RULES" in prompt or "RULES" in prompt.upper()
        assert "never" in prompt.lower() or "always" in prompt.lower()

    def test_contains_confidence_guidance(self, agent):
        prompt = agent.system_prompt
        assert "confidence" in prompt.lower()

    def test_contains_pyrite_warning(self, agent):
        prompt = agent.system_prompt
        assert "pyrite" in prompt.lower() or "Pyrite" in prompt

    def test_contains_swahili_reference(self, agent):
        prompt = agent.system_prompt
        assert "Swahili" in prompt or "swahili" in prompt.lower()


# ── Mock LLM Response ──────────────────────────────────────────────

class TestMockLLM:
    def test_mock_response_contains_disclaimer(self, agent):
        messages = [{"role": "user", "content": "Is there gold here?"}]
        response = agent._mock_llm_response(messages)
        assert "mock" in response["content"].lower() or "⚠️" in response["content"]
        assert response["role"] == "assistant"

    def test_mock_response_echoes_input(self, agent):
        messages = [{"role": "user", "content": "Is there gold in Nyatike?"}]
        response = agent._mock_llm_response(messages)
        assert "Nyatike" in response["content"] or "gold" in response["content"].lower()

    def test_mock_response_with_empty_messages(self, agent):
        response = agent._mock_llm_response([])
        assert response["role"] == "assistant"
        assert isinstance(response["content"], str)


# ── Tool Listing ────────────────────────────────────────────────────

class TestToolListing:
    def test_list_tools_returns_list(self, agent):
        tools = agent.list_tools()
        assert isinstance(tools, list)
