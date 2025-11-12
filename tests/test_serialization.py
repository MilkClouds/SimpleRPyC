"""Tests for simplerpyc.common.serialization module."""

from unittest.mock import patch

import numpy as np
import pytest

from simplerpyc.common.serialization import deserialize, deserialize_exception, serialize, serialize_exception


class TestSerialization:
    """Test serialization functions."""

    def test_string(self):
        """Test string."""
        original = "test string"
        serialized = serialize(original)
        deserialized = deserialize(serialized)

        assert deserialized == original
        assert isinstance(serialized, bytes)

    def test_int(self):
        """Test int."""
        assert deserialize(serialize(42)) == 42

    def test_float(self):
        """Test float."""
        assert deserialize(serialize(3.14159)) == 3.14159

    def test_list(self):
        """Test list."""
        original = [1, 2, 3, "four", 5.0]
        assert deserialize(serialize(original)) == original

    def test_dict(self):
        """Test dict."""
        original = {"string": "value", "number": 42, "float": 3.14, "list": [1, 2, 3], "nested": {"key": "value"}}
        assert deserialize(serialize(original)) == original

    def test_none(self):
        """Test None."""
        assert deserialize(serialize(None)) is None

    @pytest.mark.parametrize("value", [True, False])
    def test_bool(self, value):
        """Test bool."""
        assert deserialize(serialize(value)) == value

    def test_tuple(self):
        """Test tuple (converts to list)."""
        original = (1, 2, 3, "four")
        assert deserialize(serialize(original)) == list(original)

    def test_numpy_array(self):
        """Test numpy array."""
        original = np.array([1, 2, 3, 4, 5])
        assert np.array_equal(deserialize(serialize(original)), original)

    def test_numpy_2d_array(self):
        """Test numpy 2D array."""
        original = np.array([[1, 2, 3], [4, 5, 6]])
        assert np.array_equal(deserialize(serialize(original)), original)

    def test_numpy_float_array(self):
        """Test numpy float array."""
        original = np.array([1.1, 2.2, 3.3, 4.4])
        assert np.allclose(deserialize(serialize(original)), original)

    def test_complex_structure(self):
        """Test complex nested structure."""
        original = {
            "data": [1, 2, 3],
            "metadata": {"name": "test", "version": 1, "array": np.array([10, 20, 30])},
            "flags": [True, False, True],
        }
        deserialized = deserialize(serialize(original))

        assert deserialized["data"] == original["data"]
        assert deserialized["metadata"]["name"] == original["metadata"]["name"]
        assert np.array_equal(deserialized["metadata"]["array"], original["metadata"]["array"])

    def test_returns_bytes(self):
        """Test serialize returns bytes."""
        assert isinstance(serialize("test"), bytes)

    @pytest.mark.parametrize("original", [42, 3.14, "string", [1, 2, 3], {"key": "value"}, True, False, None])
    def test_type_preservation(self, original):
        """Test type preservation."""
        deserialized = deserialize(serialize(original))
        assert deserialized == original
        assert type(deserialized) is type(original)


class TestExceptionSerialization:
    """Test exception serialization."""

    def test_builtin_exception_round_trip(self):
        """Test builtin exceptions preserve type."""
        from simplerpyc.client.proxy import RemoteException

        for exc_type in [ValueError, TypeError, KeyError, IndexError]:
            exc = exc_type("test")
            data = serialize_exception(exc)
            remote_exc, original_exc = deserialize_exception(data)

            assert isinstance(remote_exc, RemoteException)
            assert hasattr(remote_exc, "remote_traceback")
            assert isinstance(original_exc, exc_type)

    def test_exception_with_attributes(self):
        """Test exception attributes preserved."""
        from simplerpyc.client.proxy import RemoteException

        exc = ValueError("test")
        exc.custom = "value"  # type: ignore
        data = serialize_exception(exc)
        remote_exc, original_exc = deserialize_exception(data)

        assert isinstance(remote_exc, RemoteException)
        assert isinstance(original_exc, ValueError)
        assert original_exc.custom == "value"  # type: ignore

    def test_exception_serialization_failure(self):
        """Test exception serialization failure fallback."""

        class UnserializableException(Exception):
            def __reduce__(self):
                raise TypeError("Cannot serialize")

        exc = UnserializableException("test")

        with patch("dill.dumps", side_effect=TypeError("Cannot serialize")):
            data = serialize_exception(exc)
            assert data["exception_pickle"] is None
            assert "UnserializableException" in data["exception_type"]

    def test_exception_deserialization_failure(self):
        """Test exception deserialization failure fallback."""
        from simplerpyc.client.proxy import RemoteException

        exc = ValueError("test")
        data = serialize_exception(exc)

        # Corrupt the pickle data
        data["exception_pickle"] = b"corrupted"

        with patch("dill.loads", side_effect=Exception("Cannot deserialize")):
            remote_exc, original_exc = deserialize_exception(data)
            assert isinstance(remote_exc, RemoteException)
            assert original_exc is None
