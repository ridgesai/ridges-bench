"""Small CPU-backed CuPy shim for verifier-only GPU path tests."""

from __future__ import annotations

import numpy as _np


class _NumbaDevice:
    MAX_THREADS_PER_BLOCK = 1024


class _NumbaLocal:
    @staticmethod
    def array(shape, dtype=float):
        return _np.empty(shape, dtype=dtype)


class _NumbaAtomic:
    @staticmethod
    def add(arr, idx, value):
        arr[idx] += value
        return arr[idx]

    @staticmethod
    def max(arr, idx, value):
        if value > arr[idx]:
            arr[idx] = value
        return arr[idx]

    @staticmethod
    def min(arr, idx, value):
        if value < arr[idx]:
            arr[idx] = value
        return arr[idx]


def _patch_numba_cuda_simulator():
    try:
        from numba import cuda as _numba_cuda
    except Exception:
        return

    if not hasattr(_numba_cuda, "get_current_device"):
        _numba_cuda.get_current_device = lambda: _NumbaDevice()
    if not hasattr(_numba_cuda, "local"):
        _numba_cuda.local = _NumbaLocal()
    if not hasattr(_numba_cuda, "atomic"):
        _numba_cuda.atomic = _NumbaAtomic()
    if not hasattr(_numba_cuda, "grid"):
        try:
            from numba.cuda.simulator.kernel import _get_kernel_context
        except Exception:
            return

        def _grid(ndim):
            context = _get_kernel_context()
            if context is None:
                raise RuntimeError("cuda.grid() called outside a simulated kernel")
            return context.grid(ndim)

        _numba_cuda.grid = _grid

    try:
        from numba.core.registry import CPUDispatcher as _CPUDispatcher
    except Exception:
        return

    if not hasattr(_CPUDispatcher, "__getitem__"):
        def _getitem(self, _launch_config):
            def _launch(data, kernel, out):
                data_np = _to_numpy(data)
                kernel_np = _to_numpy(kernel)
                out_np = _to_numpy(out)
                rows, cols = data_np.shape
                hrows = kernel_np.shape[0] // 2
                hcols = kernel_np.shape[1] // 2

                for y in range(rows):
                    for x in range(cols):
                        window = _np.empty(kernel_np.shape, dtype=data_np.dtype)
                        window.fill(_np.nan)
                        for ky in range(y - hrows, y + hrows + 1):
                            for kx in range(x - hcols, x + hcols + 1):
                                if 0 <= ky < rows and 0 <= kx < cols:
                                    wy = ky - (y - hrows)
                                    wx = kx - (x - hcols)
                                    if kernel_np[wy, wx] == 1:
                                        window[wy, wx] = data_np[ky, kx]
                        out_np[y, x] = self(window)

            return _launch

        _CPUDispatcher.__getitem__ = _getitem


_patch_numba_cuda_simulator()


class ndarray:
    __array_priority__ = 1000

    def __init__(self, input_array=(), dtype=None, copy=False):
        if isinstance(input_array, ndarray):
            data = input_array._array
            if dtype is not None and data.dtype != _np.dtype(dtype):
                data = data.astype(dtype, copy=True)
            elif copy:
                data = data.copy()
        elif copy:
            data = _np.array(input_array, dtype=dtype, copy=True)
        else:
            data = _np.asarray(input_array, dtype=dtype)
        self._array = data

    @property
    def shape(self):
        return self._array.shape

    @property
    def dtype(self):
        return self._array.dtype

    @property
    def ndim(self):
        return self._array.ndim

    @property
    def size(self):
        return self._array.size

    @property
    def T(self):
        return ndarray(self._array.T)

    def __array__(self, dtype=None):
        return _np.asarray(self._array, dtype=dtype)

    def __array_function__(self, func, types, args, kwargs):
        return _wrap(func(*_to_numpy(args), **_to_numpy(kwargs)))

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        out = kwargs.get("out")
        if out is not None:
            kwargs["out"] = _to_numpy(out)
        result = getattr(ufunc, method)(*_to_numpy(inputs), **_to_numpy(kwargs))
        if out is not None:
            return out[0] if len(out) == 1 else out
        return _wrap(result)

    def __len__(self):
        return len(self._array)

    def __iter__(self):
        for item in self._array:
            yield _wrap(item)

    def __getitem__(self, key):
        return _wrap(self._array[key])

    def __setitem__(self, key, value):
        self._array[_to_numpy(key)] = _to_numpy(value)

    def __eq__(self, other):
        return ndarray(self._array == _to_numpy(other))

    def __ne__(self, other):
        return ndarray(self._array != _to_numpy(other))

    def __lt__(self, other):
        return ndarray(self._array < _to_numpy(other))

    def __le__(self, other):
        return ndarray(self._array <= _to_numpy(other))

    def __gt__(self, other):
        return ndarray(self._array > _to_numpy(other))

    def __ge__(self, other):
        return ndarray(self._array >= _to_numpy(other))

    def __invert__(self):
        return ndarray(~self._array)

    def __repr__(self):
        return repr(self._array)

    def astype(self, dtype, copy=True):
        return ndarray(self._array.astype(dtype, copy=copy))

    def copy(self):
        return ndarray(self._array.copy())

    def get(self):
        return _np.asarray(self._array)

    def reshape(self, *shape):
        return ndarray(self._array.reshape(*shape))

    def transpose(self, *axes):
        return ndarray(self._array.transpose(*axes))

    def sum(self, axis=None, dtype=None):
        return _wrap(self._array.sum(axis=axis, dtype=dtype))

    def any(self, axis=None):
        return self._array.any(axis=axis)


def _to_numpy(obj):
    if isinstance(obj, ndarray):
        return obj._array
    if isinstance(obj, tuple):
        return tuple(_to_numpy(item) for item in obj)
    if isinstance(obj, list):
        return [_to_numpy(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _to_numpy(value) for key, value in obj.items()}
    return obj


def _wrap(obj):
    if isinstance(obj, ndarray):
        return obj
    if isinstance(obj, _np.ndarray):
        return ndarray(obj)
    return obj


def array(obj, dtype=None, copy=True):
    return ndarray(obj, dtype=dtype, copy=copy)


def asarray(obj, dtype=None):
    return ndarray(obj, dtype=dtype, copy=False)


def asnumpy(obj):
    return _np.asarray(_to_numpy(obj))


def empty(shape, dtype=float):
    return ndarray(_np.empty(shape, dtype=dtype))


def empty_like(a, dtype=None):
    return ndarray(_np.empty_like(asnumpy(a), dtype=dtype))


def zeros(shape, dtype=float):
    return ndarray(_np.zeros(shape, dtype=dtype))


def zeros_like(a, dtype=None):
    return ndarray(_np.zeros_like(asnumpy(a), dtype=dtype))


def full(shape, fill_value, dtype=None):
    return ndarray(_np.full(shape, fill_value, dtype=dtype))


def concatenate(seq, axis=0):
    return ndarray(_np.concatenate([asnumpy(item) for item in seq], axis=axis))


def take(a, indices, axis=None):
    return ndarray(_np.take(asnumpy(a), indices, axis=axis))


def tensordot(a, b, axes=2):
    return ndarray(_np.tensordot(asnumpy(a), asnumpy(b), axes=axes))


def stack(seq, axis=0):
    return ndarray(_np.stack([asnumpy(item) for item in seq], axis=axis))


def moveaxis(a, source, destination):
    return ndarray(_np.moveaxis(asnumpy(a), source, destination))


def ascontiguousarray(a, dtype=None):
    return ndarray(_np.ascontiguousarray(asnumpy(a), dtype=dtype))


def isnan(a):
    return ndarray(_np.isnan(asnumpy(a)))


def any(a, axis=None):
    return _np.any(asnumpy(a), axis=axis)


def where(condition, x=None, y=None):
    if x is None and y is None:
        return _np.where(_to_numpy(condition))
    return ndarray(_np.where(_to_numpy(condition), _to_numpy(x), _to_numpy(y)))


def putmask(a, mask, values):
    _np.putmask(_to_numpy(a), mask, values)


def nanmean(a, axis=None, dtype=None):
    return _wrap(_np.nanmean(asnumpy(a), axis=axis, dtype=dtype))


def nanmin(a, axis=None):
    return _wrap(_np.nanmin(asnumpy(a), axis=axis))


def nanmax(a, axis=None):
    return _wrap(_np.nanmax(asnumpy(a), axis=axis))


def nanmedian(a, axis=None):
    return _wrap(_np.nanmedian(asnumpy(a), axis=axis))


def around(a, decimals=0):
    return ndarray(_np.around(asnumpy(a), decimals=decimals))


def dtype(obj):
    return _np.dtype(_to_numpy(obj))


class _Testing:
    @staticmethod
    def assert_array_equal(actual, desired, *args, **kwargs):
        _np.testing.assert_array_equal(
            _np.asarray(actual), _np.asarray(desired), *args, **kwargs
        )


bool_ = _np.bool_
int8 = _np.int8
int32 = _np.int32
int64 = _np.int64
uint8 = _np.uint8
uint16 = _np.uint16
uint32 = _np.uint32
uint64 = _np.uint64
float32 = _np.float32
float64 = _np.float64
inf = _np.inf
nan = _np.nan
testing = _Testing()


class _Runtime:
    @staticmethod
    def getDeviceCount():
        return 1

    @staticmethod
    def memGetInfo():
        return (1 << 30, 1 << 30)


class _Device:
    def synchronize(self):
        return None


class _NullStream:
    def synchronize(self):
        return None


class _Stream:
    null = _NullStream()


class _Cuda:
    runtime = _Runtime()
    Stream = _Stream

    @staticmethod
    def Device():
        return _Device()

    @staticmethod
    def is_available():
        return True


cuda = _Cuda()
