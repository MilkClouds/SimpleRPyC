"""Pytest configuration and fixtures."""

import asyncio
from typing import Any, Dict
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
    ws.__aenter__ = AsyncMock(return_value=ws)
    ws.__aexit__ = AsyncMock(return_value=None)
    return ws


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def create_success_response(obj_id: int = 1, **kwargs: Any) -> Dict[str, Any]:
    """Create success response."""
    response = {"type": "success", "obj_id": obj_id}
    response.update(kwargs)
    return response


def create_error_response(
    exception_type: str,
    exception_message: str,
    traceback: str | None = None,
    exception_pickle: Any = None,
) -> Dict[str, Any]:
    """Create error response."""
    return {
        "type": "error",
        "exception_type": exception_type,
        "exception_message": exception_message,
        "traceback": traceback,
        "exception_pickle": exception_pickle,
    }
