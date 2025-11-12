"""Tests for numpy transport and serialization."""

import asyncio
import threading
import time

import numpy as np
import pytest

from simplerpyc.client.connection import connect
from simplerpyc.client.proxy import materialize
from simplerpyc.common.serialization import deserialize, serialize
from simplerpyc.server.server import RPCServer


class TestNumpySerialization:
    """Test numpy serialization/deserialization."""

    def test_serialize_1d_array(self):
        """Test serializing 1D numpy array."""
        arr = np.array([1, 2, 3, 4, 5])
        data = serialize(arr)
        result = deserialize(data)
        np.testing.assert_array_equal(result, arr)
        assert result.dtype == arr.dtype

    def test_serialize_2d_array(self):
        """Test serializing 2D numpy array."""
        arr = np.array([[1, 2, 3], [4, 5, 6]])
        data = serialize(arr)
        result = deserialize(data)
        np.testing.assert_array_equal(result, arr)
        assert result.shape == arr.shape

    def test_serialize_3d_array(self):
        """Test serializing 3D numpy array."""
        arr = np.random.rand(3, 4, 5)
        data = serialize(arr)
        result = deserialize(data)
        np.testing.assert_array_almost_equal(result, arr)
        assert result.shape == arr.shape

    def test_serialize_float_array(self):
        """Test serializing float array."""
        arr = np.array([1.1, 2.2, 3.3, 4.4], dtype=np.float32)
        data = serialize(arr)
        result = deserialize(data)
        np.testing.assert_array_almost_equal(result, arr)
        assert result.dtype == arr.dtype

    def test_serialize_int_array(self):
        """Test serializing int array."""
        arr = np.array([1, 2, 3, 4], dtype=np.int64)
        data = serialize(arr)
        result = deserialize(data)
        np.testing.assert_array_equal(result, arr)
        assert result.dtype == arr.dtype

    def test_serialize_complex_array(self):
        """Test serializing complex array."""
        arr = np.array([1 + 2j, 3 + 4j, 5 + 6j])
        data = serialize(arr)
        result = deserialize(data)
        np.testing.assert_array_equal(result, arr)
        assert result.dtype == arr.dtype

    def test_serialize_bool_array(self):
        """Test serializing boolean array."""
        arr = np.array([True, False, True, False])
        data = serialize(arr)
        result = deserialize(data)
        np.testing.assert_array_equal(result, arr)
        assert result.dtype == arr.dtype

    def test_serialize_empty_array(self):
        """Test serializing empty array."""
        arr = np.array([])
        data = serialize(arr)
        result = deserialize(data)
        np.testing.assert_array_equal(result, arr)

    def test_serialize_large_array(self):
        """Test serializing large array."""
        arr = np.random.rand(1000, 1000)
        data = serialize(arr)
        result = deserialize(data)
        np.testing.assert_array_almost_equal(result, arr)
        assert result.shape == arr.shape

    def test_serialize_dict_with_numpy(self):
        """Test serializing dict containing numpy arrays."""
        data_dict = {
            "array1": np.array([1, 2, 3]),
            "array2": np.array([[4, 5], [6, 7]]),
            "scalar": 42,
        }
        data = serialize(data_dict)
        result = deserialize(data)
        np.testing.assert_array_equal(result["array1"], data_dict["array1"])
        np.testing.assert_array_equal(result["array2"], data_dict["array2"])
        assert result["scalar"] == data_dict["scalar"]

    def test_serialize_list_with_numpy(self):
        """Test serializing list containing numpy arrays."""
        data_list = [
            np.array([1, 2, 3]),
            np.array([4.5, 5.5]),
            "string",
            42,
        ]
        data = serialize(data_list)
        result = deserialize(data)
        np.testing.assert_array_equal(result[0], data_list[0])
        np.testing.assert_array_equal(result[1], data_list[1])
        assert result[2] == data_list[2]
        assert result[3] == data_list[3]


@pytest.fixture
def numpy_server():
    """Start server for numpy integration tests."""
    server = RPCServer(host="localhost", port=-1)

    def run_server():
        asyncio.run(server.serve())

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(0.5)

    yield server


class TestNumpyIntegration:
    """Integration tests for numpy operations over RPC."""

    def test_numpy_array_creation(self, numpy_server):
        """Test creating numpy arrays remotely."""
        import numpy as np_local

        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy

        arr = materialize(np_remote.array([1, 2, 3, 4, 5]))

        assert isinstance(arr, np_local.ndarray)
        assert np_local.array_equal(arr, np_local.array([1, 2, 3, 4, 5]))

    def test_numpy_zeros(self, numpy_server):
        """Test numpy.zeros over RPC."""
        import numpy as np_local

        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        arr = materialize(np_remote.zeros(10))
        assert isinstance(arr, np_local.ndarray)
        assert arr.shape == (10,)
        assert np_local.array_equal(arr, np_local.zeros(10))

    def test_numpy_ones(self, numpy_server):
        """Test numpy.ones over RPC."""
        import numpy as np_local

        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        arr = materialize(np_remote.ones((3, 4)))
        assert isinstance(arr, np_local.ndarray)
        assert arr.shape == (3, 4)
        assert np_local.array_equal(arr, np_local.ones((3, 4)))

    def test_numpy_arange(self, numpy_server):
        """Test numpy.arange over RPC."""
        import numpy as np_local

        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        arr = materialize(np_remote.arange(0, 10, 2))
        assert isinstance(arr, np_local.ndarray)
        assert np_local.array_equal(arr, np_local.arange(0, 10, 2))

    def test_numpy_linspace(self, numpy_server):
        """Test numpy.linspace over RPC."""
        import numpy as np_local

        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        arr = materialize(np_remote.linspace(0, 1, 11))
        assert isinstance(arr, np_local.ndarray)
        assert np_local.allclose(arr, np_local.linspace(0, 1, 11))

    def test_numpy_reshape(self, numpy_server):
        """Test numpy array reshaping over RPC."""
        import numpy as np_local

        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        arr = materialize(np_remote.arange(12).reshape(3, 4))
        assert isinstance(arr, np_local.ndarray)
        assert arr.shape == (3, 4)
        assert np_local.array_equal(arr, np_local.arange(12).reshape(3, 4))

    def test_numpy_sum(self, numpy_server):
        """Test numpy.sum over RPC."""
        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        result = materialize(np_remote.array([1, 2, 3, 4, 5]).sum())
        assert result == 15

    def test_numpy_mean(self, numpy_server):
        """Test numpy.mean over RPC."""
        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        result = materialize(np_remote.array([1, 2, 3, 4, 5]).mean())
        assert result == 3.0

    def test_numpy_transpose(self, numpy_server):
        """Test numpy array transpose over RPC."""
        import numpy as np_local

        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        result = materialize(np_remote.array([[1, 2, 3], [4, 5, 6]]).T)
        expected = np_local.array([[1, 4], [2, 5], [3, 6]])
        assert np_local.array_equal(result, expected)

    def test_numpy_indexing(self, numpy_server):
        """Test numpy array indexing over RPC."""
        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        arr = np_remote.array([10, 20, 30, 40, 50])
        result = materialize(arr[2])
        assert result == 30

    def test_numpy_dtype_preservation(self, numpy_server):
        """Test that numpy dtypes are preserved over RPC."""
        import numpy as np_local

        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        int32_arr = materialize(np_remote.zeros(5, dtype="int32"))
        float64_arr = materialize(np_remote.ones(5, dtype="float64"))
        assert int32_arr.dtype == np_local.int32
        assert float64_arr.dtype == np_local.float64

    def test_numpy_complex_operations(self, numpy_server):
        """Test complex numpy operations over RPC."""
        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        mean_val = materialize(np_remote.arange(20).reshape(4, 5).mean())
        assert mean_val == 9.5

    def test_numpy_large_array_transport(self, numpy_server):
        """Test transporting large numpy arrays over RPC."""
        import numpy as np_local

        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        arr = materialize(np_remote.zeros((100, 100)))
        assert isinstance(arr, np_local.ndarray)
        assert arr.shape == (100, 100)

    def test_numpy_proxy_as_argument(self, numpy_server):
        """Test passing RPCProxy as argument to numpy functions."""
        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        arr = np_remote.array([1, 2, 3, 4, 5])
        result = materialize(np_remote.sum(arr))
        assert result == 15

    def test_numpy_multiple_proxy_arguments(self, numpy_server):
        """Test passing multiple RPCProxy objects as arguments."""
        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        a = np_remote.array([1, 2, 3])
        b = np_remote.array([4, 5, 6])
        result = materialize(np_remote.dot(a, b))
        assert result == 32

    def test_numpy_matrix_multiply_with_proxies(self, numpy_server):
        """Test matrix multiplication with proxy arguments."""
        import numpy as np_local

        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        a = np_remote.array([[1, 2], [3, 4]])
        b = np_remote.array([[5, 6], [7, 8]])
        result = materialize(np_remote.matmul(a, b))
        expected = np_local.array([[19, 22], [43, 50]])
        assert np_local.array_equal(result, expected)

    def test_numpy_slicing_with_slice_object(self, numpy_server):
        """Test numpy array slicing with slice objects."""
        import numpy as np_local

        conn = connect("localhost", numpy_server.port, token=numpy_server.token)
        np_remote = conn.modules.numpy
        arr = np_remote.arange(12).reshape(3, 4)
        result = materialize(arr[0:2])
        expected = np_local.arange(12).reshape(3, 4)[0:2]
        assert np_local.array_equal(result, expected)
