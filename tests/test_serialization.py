"""Tests for simplerpc.common.serialization module."""

import pytest
import numpy as np

from simplerpc.common.serialization import serialize, deserialize


class TestSerialization:
    """Test serialization functions."""

    def test_serialize_deserialize_string(self):
        """Test serializing and deserializing strings."""
        original = "test string"
        serialized = serialize(original)
        deserialized = deserialize(serialized)
        
        assert deserialized == original
        assert isinstance(serialized, bytes)

    def test_serialize_deserialize_int(self):
        """Test serializing and deserializing integers."""
        original = 42
        serialized = serialize(original)
        deserialized = deserialize(serialized)
        
        assert deserialized == original

    def test_serialize_deserialize_float(self):
        """Test serializing and deserializing floats."""
        original = 3.14159
        serialized = serialize(original)
        deserialized = deserialize(serialized)
        
        assert deserialized == original

    def test_serialize_deserialize_list(self):
        """Test serializing and deserializing lists."""
        original = [1, 2, 3, "four", 5.0]
        serialized = serialize(original)
        deserialized = deserialize(serialized)
        
        assert deserialized == original

    def test_serialize_deserialize_dict(self):
        """Test serializing and deserializing dicts."""
        original = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "list": [1, 2, 3],
            "nested": {"key": "value"}
        }
        serialized = serialize(original)
        deserialized = deserialize(serialized)
        
        assert deserialized == original

    def test_serialize_deserialize_none(self):
        """Test serializing and deserializing None."""
        original = None
        serialized = serialize(original)
        deserialized = deserialize(serialized)
        
        assert deserialized is None

    def test_serialize_deserialize_bool(self):
        """Test serializing and deserializing booleans."""
        for original in [True, False]:
            serialized = serialize(original)
            deserialized = deserialize(serialized)
            assert deserialized == original

    def test_serialize_deserialize_tuple(self):
        """Test serializing and deserializing tuples."""
        original = (1, 2, 3, "four")
        serialized = serialize(original)
        deserialized = deserialize(serialized)
        
        # msgpack converts tuples to lists
        assert deserialized == list(original)

    def test_serialize_deserialize_numpy_array(self):
        """Test serializing and deserializing numpy arrays."""
        original = np.array([1, 2, 3, 4, 5])
        serialized = serialize(original)
        deserialized = deserialize(serialized)
        
        assert np.array_equal(deserialized, original)

    def test_serialize_deserialize_numpy_2d_array(self):
        """Test serializing and deserializing 2D numpy arrays."""
        original = np.array([[1, 2, 3], [4, 5, 6]])
        serialized = serialize(original)
        deserialized = deserialize(serialized)
        
        assert np.array_equal(deserialized, original)

    def test_serialize_deserialize_numpy_float_array(self):
        """Test serializing and deserializing float numpy arrays."""
        original = np.array([1.1, 2.2, 3.3, 4.4])
        serialized = serialize(original)
        deserialized = deserialize(serialized)
        
        assert np.allclose(deserialized, original)

    def test_serialize_deserialize_complex_structure(self):
        """Test serializing complex nested structures."""
        original = {
            "data": [1, 2, 3],
            "metadata": {
                "name": "test",
                "version": 1,
                "array": np.array([10, 20, 30])
            },
            "flags": [True, False, True]
        }
        serialized = serialize(original)
        deserialized = deserialize(serialized)
        
        assert deserialized["data"] == original["data"]
        assert deserialized["metadata"]["name"] == original["metadata"]["name"]
        assert np.array_equal(
            deserialized["metadata"]["array"],
            original["metadata"]["array"]
        )

    def test_serialize_bytes(self):
        """Test that serialize returns bytes."""
        result = serialize("test")
        assert isinstance(result, bytes)

    def test_deserialize_bytes(self):
        """Test that deserialize accepts bytes."""
        serialized = serialize("test")
        result = deserialize(serialized)
        assert result == "test"

    def test_round_trip_preserves_types(self):
        """Test that round-trip preserves basic types."""
        test_cases = [
            42,
            3.14,
            "string",
            [1, 2, 3],
            {"key": "value"},
            True,
            False,
            None,
        ]
        
        for original in test_cases:
            serialized = serialize(original)
            deserialized = deserialize(serialized)
            assert deserialized == original
            assert type(deserialized) == type(original)

