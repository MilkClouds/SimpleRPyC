"""Tests for simplerpyc.client.patcher module (deprecated)."""

import sys
from unittest.mock import MagicMock


class TestPatchModule:
    """Test patch_module (deprecated)."""

    def test_patch_module(self, mock_connection):
        """Test patch_module."""
        from simplerpyc.client.patcher import patch_module

        mock_connection.patch_module = MagicMock(return_value="proxy")
        result = patch_module(mock_connection, "test_module")

        mock_connection.patch_module.assert_called_once_with("test_module")
        assert result == "proxy"

    def test_unpatch_module(self):
        """Test unpatch_module."""
        from simplerpyc.client.patcher import unpatch_module

        sys.modules["test_module"] = MagicMock()
        unpatch_module("test_module")
        assert "test_module" not in sys.modules
