"""Tests for simplerpc.client.patcher module."""

import sys
import pytest
from unittest.mock import Mock, patch

from simplerpc.client.patcher import patch_module, unpatch_all, _original_modules
from simplerpc.client.proxy import RPCProxy, RemoteException


class TestPatchModule:
    """Test patch_module function."""

    def setup_method(self):
        """Clean up before each test."""
        _original_modules.clear()

    def teardown_method(self):
        """Clean up after each test."""
        unpatch_all()

    def test_patch_new_module(self, mock_connection):
        """Test patching a module that doesn't exist in sys.modules."""
        mock_connection.send.return_value = {"type": "success", "obj_id": 1}

        # Ensure module doesn't exist
        if "fake_module" in sys.modules:
            del sys.modules["fake_module"]

        with patch("simplerpc.client.patcher.get_connection", return_value=mock_connection):
            result = patch_module("fake_module")

            assert isinstance(result, RPCProxy)
            assert result._rpc_path == "fake_module"
            assert result._rpc_obj_id == 1
            assert "fake_module" in sys.modules
            assert sys.modules["fake_module"] is result
            mock_connection.send.assert_called_once_with({"type": "import_module", "module": "fake_module"})

    def test_patch_existing_module(self, mock_connection):
        """Test patching a module that already exists in sys.modules."""
        mock_connection.send.return_value = {"type": "success", "obj_id": 2}

        # Create a fake existing module
        original_module = Mock()
        sys.modules["existing_module"] = original_module

        try:
            with patch("simplerpc.client.patcher.get_connection", return_value=mock_connection):
                result = patch_module("existing_module")

                assert isinstance(result, RPCProxy)
                assert sys.modules["existing_module"] is result
                assert _original_modules["existing_module"] is original_module
        finally:
            # Cleanup
            if "existing_module" in sys.modules:
                del sys.modules["existing_module"]

    def test_patch_already_patched_module(self, mock_connection):
        """Test patching a module that's already been patched."""
        mock_connection.send.return_value = {"type": "success", "obj_id": 3}

        with patch("simplerpc.client.patcher.get_connection", return_value=mock_connection):
            # First patch
            first_result = patch_module("test_module")

            # Second patch should return existing proxy without calling server
            mock_connection.send.reset_mock()
            second_result = patch_module("test_module")

            assert second_result is first_result
            mock_connection.send.assert_not_called()

    def test_patch_module_error(self, mock_connection):
        """Test patching module with server error."""
        mock_connection.send.return_value = {
            "type": "error",
            "error": "ModuleNotFoundError: No module named 'nonexistent'",
            "traceback": "Traceback...",
        }

        with patch("simplerpc.client.patcher.get_connection", return_value=mock_connection):
            with pytest.raises(RemoteException) as exc_info:
                patch_module("nonexistent")

            assert "ModuleNotFoundError" in str(exc_info.value)

    def test_patch_multiple_modules(self, mock_connection):
        """Test patching multiple modules."""
        mock_connection.send.side_effect = [
            {"type": "success", "obj_id": 1},
            {"type": "success", "obj_id": 2},
            {"type": "success", "obj_id": 3},
        ]

        with patch("simplerpc.client.patcher.get_connection", return_value=mock_connection):
            proxy1 = patch_module("module1")
            proxy2 = patch_module("module2")
            proxy3 = patch_module("module3")

            assert len(_original_modules) == 3
            assert sys.modules["module1"] is proxy1
            assert sys.modules["module2"] is proxy2
            assert sys.modules["module3"] is proxy3


class TestUnpatchAll:
    """Test unpatch_all function."""

    def setup_method(self):
        """Clean up before each test."""
        _original_modules.clear()

    def teardown_method(self):
        """Clean up after each test."""
        unpatch_all()

    def test_unpatch_new_modules(self, mock_connection):
        """Test unpatching modules that didn't exist before."""
        mock_connection.send.return_value = {"type": "success", "obj_id": 1}

        with patch("simplerpc.client.patcher.get_connection", return_value=mock_connection):
            patch_module("new_module")
            assert "new_module" in sys.modules

            unpatch_all()

            assert "new_module" not in sys.modules
            assert len(_original_modules) == 0

    def test_unpatch_existing_modules(self, mock_connection):
        """Test unpatching modules that existed before."""
        mock_connection.send.return_value = {"type": "success", "obj_id": 2}

        # Create original module
        original_module = Mock()
        sys.modules["existing"] = original_module

        try:
            with patch("simplerpc.client.patcher.get_connection", return_value=mock_connection):
                patch_module("existing")
                assert isinstance(sys.modules["existing"], RPCProxy)

                unpatch_all()

                assert sys.modules["existing"] is original_module
                assert len(_original_modules) == 0
        finally:
            if "existing" in sys.modules:
                del sys.modules["existing"]

    def test_unpatch_mixed_modules(self, mock_connection):
        """Test unpatching mix of new and existing modules."""
        mock_connection.send.side_effect = [
            {"type": "success", "obj_id": 1},
            {"type": "success", "obj_id": 2},
        ]

        # Create one existing module
        original = Mock()
        sys.modules["existing"] = original

        try:
            with patch("simplerpc.client.patcher.get_connection", return_value=mock_connection):
                patch_module("new_module")
                patch_module("existing")

                unpatch_all()

                assert "new_module" not in sys.modules
                assert sys.modules["existing"] is original
        finally:
            if "existing" in sys.modules:
                del sys.modules["existing"]

    def test_unpatch_empty(self):
        """Test unpatching when nothing is patched."""
        unpatch_all()  # Should not raise any errors
        assert len(_original_modules) == 0

    def test_unpatch_idempotent(self, mock_connection):
        """Test that unpatch_all can be called multiple times."""
        mock_connection.send.return_value = {"type": "success", "obj_id": 1}

        with patch("simplerpc.client.patcher.get_connection", return_value=mock_connection):
            patch_module("test_module")

            unpatch_all()
            unpatch_all()  # Should not raise

            assert len(_original_modules) == 0


class TestPatcherIntegration:
    """Integration tests for patcher module."""

    def setup_method(self):
        """Clean up before each test."""
        _original_modules.clear()

    def teardown_method(self):
        """Clean up after each test."""
        unpatch_all()

    def test_patch_and_import(self, mock_connection):
        """Test patching and then importing the module."""
        mock_connection.send.return_value = {"type": "success", "obj_id": 1}

        with patch("simplerpc.client.patcher.get_connection", return_value=mock_connection):
            patch_module("remote_module")

            # Now import should get the proxy
            import remote_module  # noqa: F401

            assert isinstance(remote_module, RPCProxy)

    def test_patch_preserves_original_state(self, mock_connection):
        """Test that unpatching restores original sys.modules state."""
        mock_connection.send.return_value = {"type": "success", "obj_id": 1}

        # Save original state
        original_keys = set(sys.modules.keys())

        with patch("simplerpc.client.patcher.get_connection", return_value=mock_connection):
            patch_module("temp_module")
            assert "temp_module" in sys.modules

            unpatch_all()

            # Should be back to original state
            assert set(sys.modules.keys()) == original_keys
