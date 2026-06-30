from time import perf_counter

import dask
import numpy as np
import xarray as xr

from xrspatial.proximity import proximity


TARGET_VALUES = [1.0]
MAX_DISTANCE = 2.25
NUMPY_WARMED_CALLS = 4
NUMPY_WARMED_CALLS_BUDGET_SECONDS = 1.0
DASK_WARMED_COMPUTES = 2
DASK_WARMED_COMPUTES_BUDGET_SECONDS = 3.0

SQRT2 = np.sqrt(2.0)
SQRT5 = np.sqrt(5.0)

EXPECTED_EUCLIDEAN = np.array(
    [
        [0.0, 1.0, 2.0, 2.0, SQRT5],
        [1.0, SQRT2, SQRT2, 1.0, SQRT2],
        [2.0, 2.0, 1.0, 0.0, 1.0],
        [np.nan, SQRT5, SQRT2, 1.0, SQRT2],
    ],
    dtype=np.float32,
)

EXPECTED_MANHATTAN = np.array(
    [
        [0.0, 1.0, 2.0, 2.0, np.nan],
        [1.0, 2.0, 2.0, 1.0, 2.0],
        [2.0, 2.0, 1.0, 0.0, 1.0],
        [np.nan, np.nan, 2.0, 1.0, 2.0],
    ],
    dtype=np.float32,
)


def _small_raster():
    data = np.array(
        [
            [1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0],
        ],
        dtype=np.float32,
    )
    return xr.DataArray(
        data,
        dims=("y", "x"),
        coords={
            "y": np.arange(data.shape[0], dtype=np.float64),
            "x": np.arange(data.shape[1], dtype=np.float64),
        },
    )


def _larger_raster():
    data = np.zeros((12, 12), dtype=np.float32)
    data[0, 0] = 1.0
    data[5, 5] = 1.0
    data[11, 10] = 1.0
    return xr.DataArray(
        data,
        dims=("y", "x"),
        coords={
            "y": np.arange(data.shape[0], dtype=np.float64),
            "x": np.arange(data.shape[1], dtype=np.float64),
        },
    )


def _proximity(raster, *, distance_metric=None, max_distance=MAX_DISTANCE):
    kwargs = {"target_values": TARGET_VALUES, "max_distance": max_distance}
    if distance_metric is not None:
        kwargs["distance_metric"] = distance_metric
    return proximity(raster, **kwargs)


def _assert_matches(result, expected):
    np.testing.assert_allclose(
        np.asarray(result), expected, rtol=1e-6, atol=1e-6, equal_nan=True
    )


def _assert_warmed_calls_stay_fast(call, expected, *, repeats, budget_seconds):
    _assert_matches(call(), expected)

    total_seconds = 0.0
    for _ in range(repeats):
        start = perf_counter()
        result = call()
        total_seconds += perf_counter() - start
        _assert_matches(result, expected)

    assert total_seconds < budget_seconds, (
        f"{repeats} warmed proximity calls took {total_seconds:.3f}s; "
        "the compiled line-sweep signature should be reused after warm-up"
    )


def test_numpy_default_euclidean_reuses_warmed_linesweep_signature():
    raster = _small_raster()

    _assert_warmed_calls_stay_fast(
        lambda: _proximity(raster),
        EXPECTED_EUCLIDEAN,
        repeats=NUMPY_WARMED_CALLS,
        budget_seconds=NUMPY_WARMED_CALLS_BUDGET_SECONDS,
    )


def test_numpy_explicit_euclidean_values_are_stable_on_repeated_calls():
    raster = _small_raster()

    first = _proximity(raster, distance_metric="EUCLIDEAN")
    second = _proximity(raster, distance_metric="EUCLIDEAN")

    _assert_matches(first, EXPECTED_EUCLIDEAN)
    _assert_matches(second, EXPECTED_EUCLIDEAN)
    np.testing.assert_allclose(
        np.asarray(second), np.asarray(first), rtol=1e-6, atol=1e-6, equal_nan=True
    )


def test_numpy_manhattan_reuses_warmed_linesweep_signature_and_values():
    raster = _small_raster()

    _assert_warmed_calls_stay_fast(
        lambda: _proximity(raster, distance_metric="MANHATTAN"),
        EXPECTED_MANHATTAN,
        repeats=NUMPY_WARMED_CALLS,
        budget_seconds=NUMPY_WARMED_CALLS_BUDGET_SECONDS,
    )


def test_dask_numpy_chunks_reuse_warmed_linesweep_signature():
    base = _larger_raster()
    expected = np.asarray(
        _proximity(base, distance_metric="EUCLIDEAN", max_distance=5.0)
    )
    chunked = base.chunk({"y": 3, "x": 3})

    def compute_chunked():
        # The single-threaded scheduler keeps all chunk work in one warm process.
        with dask.config.set(scheduler="single-threaded"):
            return _proximity(
                chunked, distance_metric="EUCLIDEAN", max_distance=5.0
            ).compute()

    _assert_warmed_calls_stay_fast(
        compute_chunked,
        expected,
        repeats=DASK_WARMED_COMPUTES,
        budget_seconds=DASK_WARMED_COMPUTES_BUDGET_SECONDS,
    )
