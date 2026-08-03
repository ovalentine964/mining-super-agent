"""
Pytest configuration and fixtures.
"""

import asyncio
from typing import Generator

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_mineral_data():
    """Sample mineral data for testing."""
    return {
        "mineral": "quartz",
        "grade": 85.0,
        "confidence": 0.75,
        "source": "observation",
        "latitude": -1.0956,
        "longitude": 34.4836,
    }


@pytest.fixture
def sample_gold_pyrite_data():
    """Sample data for gold vs pyrite testing."""
    return {
        "spectral": [0.85, 0.72, 0.91, 0.45],
        "chemical": {"Fe": 45.2, "S": 52.1, "Au": 0.001},
    }
