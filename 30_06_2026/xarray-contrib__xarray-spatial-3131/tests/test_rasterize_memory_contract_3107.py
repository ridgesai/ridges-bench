import gc
import tracemalloc

import numpy as np
import pytest
from numba import njit
from shapely.geometry import Point, box

from xrspatial.rasterize import rasterize


MEMORY_SIDE = 2048
SUM_PEAK_LIMIT_BYTES_PER_PIXEL = 14.0
LAST_PEAK_LIMIT_BYTES_PER_PIXEL = 22.0


def _measure_peak_bytes(call):
    gc.collect()
    tracemalloc.start()
    try:
        result = call()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, peak


def _full_cover_rasterize(geometries, side, merge):
    return rasterize(
        geometries,
        width=side,
        height=side,
        bounds=(0.0, 0.0, 1.0, 1.0),
        fill=0.0,
        merge=merge,
        use_cuda=False,
    )


@njit
def callable_weighted_sum(pixel, props, is_first):
    if is_first:
        return props[0] * 2.0
    return pixel + props[0] * 2.0


def test_default_float64_sum_peak_memory_excludes_owner_order_and_cast_copy():
    geometries = [(box(-1.0, -1.0, 2.0, 2.0), 2.0)]
    _full_cover_rasterize(geometries, 8, merge="sum")

    result, peak = _measure_peak_bytes(
        lambda: _full_cover_rasterize(geometries, MEMORY_SIDE, merge="sum")
    )

    array = np.asarray(result)
    assert array.dtype == np.dtype("float64")
    assert array.shape == (MEMORY_SIDE, MEMORY_SIDE)
    assert float(array.min()) == 2.0
    assert float(array.max()) == 2.0
    assert peak / array.size < SUM_PEAK_LIMIT_BYTES_PER_PIXEL


def test_last_peak_memory_preserves_input_order_semantics_without_final_copy():
    geometries = [
        (box(-1.0, -1.0, 2.0, 2.0), 2.0),
        (box(-1.0, -1.0, 2.0, 2.0), 9.0),
    ]
    _full_cover_rasterize(geometries, 8, merge="last")

    result, peak = _measure_peak_bytes(
        lambda: _full_cover_rasterize(geometries, MEMORY_SIDE, merge="last")
    )

    array = np.asarray(result)
    assert array.dtype == np.dtype("float64")
    assert array.shape == (MEMORY_SIDE, MEMORY_SIDE)
    assert float(array.min()) == 9.0
    assert float(array.max()) == 9.0
    assert peak / array.size < LAST_PEAK_LIMIT_BYTES_PER_PIXEL


def test_non_default_dtype_conversion_and_all_touched_values_are_observable():
    result = rasterize(
        [(box(0.9, 0.9, 1.1, 1.1), 7.9)],
        width=2,
        height=2,
        bounds=(0.0, 0.0, 2.0, 2.0),
        fill=-2.0,
        dtype=np.int16,
        all_touched=True,
        merge="last",
        use_cuda=False,
    )

    array = np.asarray(result)
    assert array.dtype == np.dtype("int16")
    np.testing.assert_array_equal(array, np.full((2, 2), 7, dtype=np.int16))


@pytest.mark.parametrize(
    ("merge", "expected_value"),
    [
        ("first", 2.0),
        ("last", 3.0),
        ("max", 5.0),
        ("min", 2.0),
        ("sum", 10.0),
        ("count", 3.0),
        (callable_weighted_sum, 20.0),
    ],
    ids=["first", "last", "max", "min", "sum", "count", "callable"],
)
def test_supported_merge_modes_and_callable_preserve_burned_values_and_fill(
    merge, expected_value
):
    geometries = [
        (Point(1.5, 1.5), 2.0),
        (Point(1.5, 1.5), 5.0),
        (Point(1.5, 1.5), 3.0),
    ]

    result = rasterize(
        geometries,
        width=3,
        height=3,
        bounds=(0.0, 0.0, 3.0, 3.0),
        fill=-1.0,
        dtype=np.float64,
        all_touched=False,
        merge=merge,
        use_cuda=False,
    )

    expected = np.full((3, 3), -1.0, dtype=np.float64)
    expected[1, 1] = expected_value
    array = np.asarray(result)

    assert array.dtype == np.dtype("float64")
    np.testing.assert_array_equal(array, expected)
