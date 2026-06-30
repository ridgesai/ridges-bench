from __future__ import annotations

from types import SimpleNamespace

import numpy as _np
from numba import cuda as _cuda
from numpy.lib.mixins import NDArrayOperatorsMixin


if not hasattr(_cuda, "get_current_device"):
    _cuda.get_current_device = lambda: SimpleNamespace(MAX_THREADS_PER_BLOCK=64)


cuda = SimpleNamespace(
    runtime=SimpleNamespace(
        CUDARuntimeError=RuntimeError,
        getDeviceCount=lambda: 1,
    )
)


class _DataPtr:
    def __init__(self, array):
        self.array = array
        self.ptr = int(array.__array_interface__["data"][0])


class ndarray(NDArrayOperatorsMixin):
    __array_priority__ = 1000

    def __init__(self, shape, dtype=float, memptr=None, strides=None, order="C"):
        if isinstance(shape, ndarray):
            array = shape._array
        elif memptr is not None and hasattr(memptr, "array"):
            base = memptr.array
            if (
                tuple(shape) == tuple(base.shape)
                and _np.dtype(dtype) == base.dtype
                and (strides is None or strides == base.strides)
            ):
                array = base
            else:
                array = _np.ndarray(
                    shape, dtype=dtype, buffer=base, strides=strides, order=order
                )
        elif isinstance(shape, tuple):
            array = _np.empty(shape, dtype=dtype, order=order)
        else:
            array = _np.asarray(shape, dtype=dtype)
        self._array = array

    @classmethod
    def _from_array(cls, array):
        obj = cls.__new__(cls)
        obj._array = _np.asarray(array)
        return obj

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
    def data(self):
        return _DataPtr(self._array)

    @property
    def strides(self):
        return self._array.strides

    def __len__(self):
        return len(self._array)

    def __iter__(self):
        return iter(self._array)

    def __getitem__(self, key):
        value = self._array[key]
        if isinstance(value, _np.ndarray):
            return ndarray._from_array(value)
        return value

    def __setitem__(self, key, value):
        self._array[key] = _to_numpy(value)

    def __array__(self, dtype=None):
        return _np.asarray(self._array, dtype=dtype)

    def __float__(self):
        return float(self._array)

    def __repr__(self):
        return f"cupy_stub.ndarray({self._array!r})"

    def item(self):
        return self._array.item()

    def get(self):
        return self._array

    def astype(self, dtype, *args, **kwargs):
        return ndarray._from_array(self._array.astype(dtype, *args, **kwargs))

    def view(self, dtype=None, type=None):
        cls = type or self.__class__
        if isinstance(dtype, type_cls) and issubclass(dtype, ndarray):
            cls = dtype
            dtype = None
        array = self._array.view(dtype=dtype) if dtype is not None else self._array
        if hasattr(cls, "_from_array"):
            return cls._from_array(array)
        return cls(array)

    def __array_function__(self, func, types, args, kwargs):
        return _wrap(func(*_to_numpy(args), **_to_numpy(kwargs)))

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        return _wrap(
            getattr(ufunc, method)(*_to_numpy(inputs), **_to_numpy(kwargs))
        )


type_cls = type


def _to_numpy(value):
    if isinstance(value, ndarray):
        return value._array
    if isinstance(value, tuple):
        return tuple(_to_numpy(item) for item in value)
    if isinstance(value, list):
        return [_to_numpy(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_numpy(item) for key, item in value.items()}
    return value


def _wrap(value):
    if isinstance(value, _np.ndarray):
        return ndarray._from_array(value)
    if isinstance(value, tuple):
        return tuple(_wrap(item) for item in value)
    return value


def asarray(value, dtype=None):
    return ndarray._from_array(_np.asarray(_to_numpy(value), dtype=dtype))


array = asarray


def asnumpy(value):
    return _np.asarray(_to_numpy(value))


def empty(shape, dtype=float):
    return ndarray._from_array(_np.empty(shape, dtype=dtype))


def zeros(shape, dtype=float):
    return ndarray._from_array(_np.zeros(shape, dtype=dtype))


def empty_like(value, dtype=None):
    return ndarray._from_array(_np.empty_like(_to_numpy(value), dtype=dtype))


def zeros_like(value, dtype=None):
    return ndarray._from_array(_np.zeros_like(_to_numpy(value), dtype=dtype))


def pad(value, pad_width, mode="constant", **kwargs):
    return ndarray._from_array(
        _np.pad(_to_numpy(value), pad_width, mode=mode, **kwargs)
    )


def isnan(value):
    return ndarray._from_array(_np.isnan(_to_numpy(value)))


def sqrt(value, *args, **kwargs):
    return _wrap(_np.sqrt(_to_numpy(value), *args, **kwargs))


def abs(value, *args, **kwargs):
    return _wrap(_np.abs(_to_numpy(value), *args, **kwargs))


absolute = abs


def nanmean(value, *args, **kwargs):
    return _np.nanmean(_to_numpy(value), *args, **kwargs)


def nanstd(value, *args, **kwargs):
    return _np.nanstd(_to_numpy(value), *args, **kwargs)


def nanmin(value, *args, **kwargs):
    return _np.nanmin(_to_numpy(value), *args, **kwargs)


def nanmax(value, *args, **kwargs):
    return _np.nanmax(_to_numpy(value), *args, **kwargs)


def minimum(left, right):
    return _wrap(_np.minimum(_to_numpy(left), _to_numpy(right)))


def maximum(left, right):
    return _wrap(_np.maximum(_to_numpy(left), _to_numpy(right)))


def where(condition, left, right):
    return _wrap(_np.where(_to_numpy(condition), _to_numpy(left), _to_numpy(right)))


float16 = _np.float16
float32 = _np.float32
float64 = _np.float64
int8 = _np.int8
int16 = _np.int16
int32 = _np.int32
int64 = _np.int64
uint8 = _np.uint8
uint16 = _np.uint16
uint32 = _np.uint32
uint64 = _np.uint64
bool_ = _np.bool_
integer = _np.integer
floating = _np.floating
nan = _np.nan
inf = _np.inf
