"""Pytest configuration and fixtures."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest


@pytest.fixture
def mock_connection():
    """Mock connection for testing."""
    conn = Mock()
    conn.send = Mock(return_value={"type": "success", "obj_id": 1})
    return conn


@pytest.fixture
def mock_websocket():
    """Mock WebSocket for testing."""
    ws = MagicMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    ws.close = AsyncMock()

    # Make the mock itself awaitable
    async def _await():
        return ws

    ws.__aenter__ = AsyncMock(return_value=ws)
    ws.__aexit__ = AsyncMock(return_value=None)

    return ws


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
