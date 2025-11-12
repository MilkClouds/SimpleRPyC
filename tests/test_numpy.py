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
    """Test numpy serialization."""

    def test_1d_array(self):
        """Test 1D array."""
        arr = np.array([1, 2, 3, 4, 5])
        result = deserialize(serialize(arr))
        np.testing.assert_array_equal(result, arr)
        assert result.dtype == arr.dtype

    def test_2d_array(self):
        """Test 2D array."""
        arr = np.array([[1, 2, 3], [4, 5, 6]])
        result = deserialize(serialize(arr))
        np.testing.assert_array_equal(result, arr)
        assert result.shape == arr.shape

    def test_3d_array(self):
        """Test 3D array."""
        arr = np.random.rand(3, 4, 5)
        result = deserialize(serialize(arr))
        np.testing.assert_array_almost_equal(result, arr)
        assert result.shape == arr.shape

    def test_float_array(self):
        """Test float array."""
        arr = np.array([1.1, 2.2, 3.3, 4.4], dtype=np.float32)
        result = deserialize(serialize(arr))
        np.testing.assert_array_almost_equal(result, arr)
        assert result.dtype == arr.dtype

    def test_int_array(self):
        """Test int array."""
        arr = np.array([1, 2, 3, 4], dtype=np.int64)
        result = deserialize(serialize(arr))
        np.testing.assert_array_equal(result, arr)
        assert result.dtype == arr.dtype

    def test_complex_array(self):
        """Test complex array."""
        arr = np.array([1 + 2j, 3 + 4j, 5 + 6j])
        result = deserialize(serialize(arr))
        np.testing.assert_array_equal(result, arr)
        assert result.dtype == arr.dtype

    def test_bool_array(self):
        """Test bool array."""
        arr = np.array([True, False, True, False])
        result = deserialize(serialize(arr))
        np.testing.assert_array_equal(result, arr)
        assert result.dtype == arr.dtype

    def test_empty_array(self):
        """Test empty array."""
        arr = np.array([])
        result = deserialize(serialize(arr))
        np.testing.assert_array_equal(result, arr)

    def test_large_array(self):
        """Test large array."""
        arr = np.random.rand(1000, 1000)
        result = deserialize(serialize(arr))
        np.testing.assert_array_almost_equal(result, arr)
        assert result.shape == arr.shape

    def test_dict_with_numpy(self):
        """Test dict with numpy."""
        data_dict = {
            "array1": np.array([1, 2, 3]),
            "array2": np.array([[4, 5], [6, 7]]),
            "scalar": 42,
        }
        result = deserialize(serialize(data_dict))
        np.testing.assert_array_equal(result["array1"], data_dict["array1"])
        np.testing.assert_array_equal(result["array2"], data_dict["array2"])
        assert result["scalar"] == data_dict["scalar"]

    def test_list_with_numpy(self):
        """Test list with numpy."""
        data_list = [np.array([1, 2, 3]), np.array([4.5, 5.5]), "string", 42]
        result = deserialize(serialize(data_list))
        np.testing.assert_array_equal(result[0], data_list[0])
        np.testing.assert_array_equal(result[1], data_list[1])
        assert result[2] == data_list[2]
        assert result[3] == data_list[3]


@pytest.fixture
def numpy_server():
    """Start server."""
    server = RPCServer(host="localhost", port=0)

    def run_server():
        asyncio.run(server.serve())

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(0.5)

    yield server


@pytest.fixture
def numpy_conn(numpy_server):
    """Create connection to numpy server."""
    conn = connect("localhost", numpy_server.port, token=numpy_server.token)
    yield conn
    conn.unpatch_all()
    conn.disconnect()


class TestNumpyIntegration:
    """Numpy integration tests."""

    def test_array_creation(self, numpy_conn):
        """Test array creation."""
        import numpy as np_local

        arr = materialize(numpy_conn.modules.numpy.array([1, 2, 3, 4, 5]))

        assert isinstance(arr, np_local.ndarray)
        assert np_local.array_equal(arr, np_local.array([1, 2, 3, 4, 5]))

    def test_zeros(self, numpy_conn):
        """Test zeros."""
        import numpy as np_local

        arr = materialize(numpy_conn.modules.numpy.zeros(10))

        assert isinstance(arr, np_local.ndarray)
        assert arr.shape == (10,)
        assert np_local.array_equal(arr, np_local.zeros(10))

    def test_ones(self, numpy_conn):
        """Test ones."""
        import numpy as np_local

        arr = materialize(numpy_conn.modules.numpy.ones((3, 4)))

        assert isinstance(arr, np_local.ndarray)
        assert arr.shape == (3, 4)
        assert np_local.array_equal(arr, np_local.ones((3, 4)))

    def test_arange(self, numpy_conn):
        """Test arange."""
        import numpy as np_local

        arr = materialize(numpy_conn.modules.numpy.arange(0, 10, 2))

        assert isinstance(arr, np_local.ndarray)
        assert np_local.array_equal(arr, np_local.arange(0, 10, 2))

    def test_linspace(self, numpy_conn):
        """Test linspace."""
        import numpy as np_local

        arr = materialize(numpy_conn.modules.numpy.linspace(0, 1, 11))

        assert isinstance(arr, np_local.ndarray)
        assert np_local.allclose(arr, np_local.linspace(0, 1, 11))

    def test_reshape(self, numpy_conn):
        """Test reshape."""
        import numpy as np_local

        arr = materialize(numpy_conn.modules.numpy.arange(12).reshape(3, 4))

        assert isinstance(arr, np_local.ndarray)
        assert arr.shape == (3, 4)
        assert np_local.array_equal(arr, np_local.arange(12).reshape(3, 4))

    def test_sum(self, numpy_conn):
        """Test sum."""
        result = materialize(numpy_conn.modules.numpy.array([1, 2, 3, 4, 5]).sum())
        assert result == 15

    def test_mean(self, numpy_conn):
        """Test mean."""
        result = materialize(numpy_conn.modules.numpy.array([1, 2, 3, 4, 5]).mean())
        assert result == 3.0

    def test_transpose(self, numpy_conn):
        """Test transpose."""
        import numpy as np_local

        result = materialize(numpy_conn.modules.numpy.array([[1, 2, 3], [4, 5, 6]]).T)
        expected = np_local.array([[1, 4], [2, 5], [3, 6]])
        assert np_local.array_equal(result, expected)

    def test_indexing(self, numpy_conn):
        """Test indexing."""
        arr = numpy_conn.modules.numpy.array([10, 20, 30, 40, 50])
        assert materialize(arr[2]) == 30

    def test_dtype_preservation(self, numpy_conn):
        """Test dtype preservation."""
        import numpy as np_local

        np_remote = numpy_conn.modules.numpy
        int32_arr = materialize(np_remote.zeros(5, dtype="int32"))
        float64_arr = materialize(np_remote.ones(5, dtype="float64"))

        assert int32_arr.dtype == np_local.int32
        assert float64_arr.dtype == np_local.float64

    def test_complex_operations(self, numpy_conn):
        """Test complex operations."""
        mean_val = materialize(numpy_conn.modules.numpy.arange(20).reshape(4, 5).mean())
        assert mean_val == 9.5

    def test_large_array_transport(self, numpy_conn):
        """Test large array transport."""
        import numpy as np_local

        arr = materialize(numpy_conn.modules.numpy.zeros((100, 100)))

        assert isinstance(arr, np_local.ndarray)
        assert arr.shape == (100, 100)

    def test_proxy_as_argument(self, numpy_conn):
        """Test proxy as argument."""
        np_remote = numpy_conn.modules.numpy
        arr = np_remote.array([1, 2, 3, 4, 5])
        assert materialize(np_remote.sum(arr)) == 15

    def test_multiple_proxy_arguments(self, numpy_conn):
        """Test multiple proxy arguments."""
        np_remote = numpy_conn.modules.numpy
        a = np_remote.array([1, 2, 3])
        b = np_remote.array([4, 5, 6])
        assert materialize(np_remote.dot(a, b)) == 32

    def test_matrix_multiply(self, numpy_conn):
        """Test matrix multiply."""
        import numpy as np_local

        np_remote = numpy_conn.modules.numpy
        a = np_remote.array([[1, 2], [3, 4]])
        b = np_remote.array([[5, 6], [7, 8]])
        result = materialize(np_remote.matmul(a, b))
        expected = np_local.array([[19, 22], [43, 50]])
        assert np_local.array_equal(result, expected)

    def test_slicing(self, numpy_conn):
        """Test slicing."""
        import numpy as np_local

        arr = numpy_conn.modules.numpy.arange(12).reshape(3, 4)
        result = materialize(arr[0:2])
        expected = np_local.arange(12).reshape(3, 4)[0:2]
        assert np_local.array_equal(result, expected)
