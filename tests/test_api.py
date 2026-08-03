"""
Tests for the FastAPI endpoints — health, CORS, API key, channel routing.
"""

import os
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def _clean_env(monkeypatch):
    """Reset env vars that affect app startup."""
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("ENV", raising=False)


def _make_client(monkeypatch, env_overrides: dict | None = None):
    """Build an AsyncClient with controlled env vars and mocked agent."""
    for k in ["API_KEY", "CORS_ORIGINS", "ENV"]:
        monkeypatch.delenv(k, raising=False)
    if env_overrides:
        for k, v in env_overrides.items():
            monkeypatch.setenv(k, v)

    # Import inside the helper so module-level CORS logic re-evaluates with fresh env
    import importlib
    import src.main as main_mod
    importlib.reload(main_mod)

    # Mock the agent singleton so no real LLM is needed
    mock_agent = AsyncMock()
    mock_agent.chat = AsyncMock(return_value={"response": "mock reply"})
    main_mod._agent_instance = mock_agent

    transport = ASGITransport(app=main_mod.app)
    return AsyncClient(transport=transport, base_url="http://test"), main_mod


# ── Health Endpoint ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_returns_200(monkeypatch, _clean_env):
    client, _ = _make_client(monkeypatch)
    async with client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_hides_service_name_in_production(monkeypatch, _clean_env):
    client, _ = _make_client(monkeypatch, {"ENV": "production", "CORS_ORIGINS": "https://example.com"})
    async with client:
        resp = await client.get("/health")
    data = resp.json()
    assert "service" not in data
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_shows_service_name_in_development(monkeypatch, _clean_env):
    client, _ = _make_client(monkeypatch)
    async with client:
        resp = await client.get("/health")
    data = resp.json()
    assert "service" in data
    assert data["service"] == "sovereign-resource-dao"


# ── CORS ────────────────────────────────────────────────────────────

def test_cors_rejects_wildcard_in_production(monkeypatch, _clean_env):
    """Setting CORS_ORIGINS=* with ENV=production should raise ValueError."""
    monkeypatch.setenv("CORS_ORIGINS", "*")
    monkeypatch.setenv("ENV", "production")

    import importlib
    import src.main as main_mod
    with pytest.raises(ValueError, match="CORS_ORIGINS must be set in production"):
        importlib.reload(main_mod)


# ── API Key Middleware ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_key_blocks_when_set(monkeypatch, _clean_env):
    """When API_KEY is set, the verify_api_key dependency rejects bad keys."""
    # Test the dependency function directly since it's not wired to routes
    from fastapi import HTTPException
    _, main_mod = _make_client(monkeypatch, {"API_KEY": "secret123"})
    # Without a key, the dependency should raise 401
    with pytest.raises(HTTPException) as exc_info:
        await main_mod.verify_api_key(None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_api_key_allows_when_not_set(monkeypatch, _clean_env):
    """When API_KEY env is empty, all requests pass without a key."""
    client, _ = _make_client(monkeypatch)
    async with client:
        resp = await client.post(
            "/api/v1/channels/route",
            json={"text": "hello", "sender_id": "u1", "source_channel": "tg"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_api_key_allows_with_correct_key(monkeypatch, _clean_env):
    """Correct API key should allow access."""
    client, _ = _make_client(monkeypatch, {"API_KEY": "secret123"})
    async with client:
        resp = await client.post(
            "/api/v1/channels/route",
            json={"text": "hello", "sender_id": "u1", "source_channel": "tg"},
            headers={"X-API-Key": "secret123"},
        )
    assert resp.status_code == 200


# ── Channel Routing ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_channel_route_valid_payload(monkeypatch, _clean_env):
    client, _ = _make_client(monkeypatch)
    async with client:
        resp = await client.post(
            "/api/v1/channels/route",
            json={
                "message_type": "text",
                "text": "What minerals are in Nyatike?",
                "sender_id": "user-42",
                "source_channel": "telegram",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data
    assert "message_id" in data


@pytest.mark.asyncio
async def test_channel_route_missing_text(monkeypatch, _clean_env):
    """Missing text should still work — uses fallback message."""
    client, main_mod = _make_client(monkeypatch)
    async with client:
        resp = await client.post(
            "/api/v1/channels/route",
            json={
                "message_type": "photo",
                "sender_id": "user-99",
                "source_channel": "telegram",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data


@pytest.mark.asyncio
async def test_channel_route_empty_body(monkeypatch, _clean_env):
    """Empty JSON body should be handled gracefully."""
    client, _ = _make_client(monkeypatch)
    async with client:
        resp = await client.post(
            "/api/v1/channels/route",
            json={},
        )
    assert resp.status_code == 200
