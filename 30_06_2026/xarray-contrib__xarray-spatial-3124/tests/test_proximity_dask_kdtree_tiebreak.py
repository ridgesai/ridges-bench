import numpy as np
import pytest
import xarray as xr

from xrspatial.proximity import allocation, direction


dask_array = pytest.importorskip("dask.array")

TIED_PIXEL = (2, 3)
TARGET_VALUES = [2.0, 3.0]
LOWEST_FLAT_TARGET_VALUE = 2.0


def source_values():
    values = np.zeros((5, 5), dtype=np.float32)
    values[1, 3] = 2.0  # flat index 8
    values[2, 2] = 3.0  # flat index 12
    return values


def single_target_values(row, col, value):
    values = np.zeros((5, 5), dtype=np.float32)
    values[row, col] = value
    return values


def raster_from(values, chunks=None):
    data = values.copy()
    if chunks is not None:
        data = dask_array.from_array(data, chunks=chunks)
    return xr.DataArray(
        data,
        dims=("y", "x"),
        coords={
            "y": np.arange(values.shape[0], dtype=np.float64),
            "x": np.arange(values.shape[1], dtype=np.float64),
        },
    )


def computed_values(data_array):
    data = data_array.data
    if hasattr(data, "compute"):
        data = data.compute()
    return np.asarray(data)


def allocation_values(values, chunks=None):
    return computed_values(
        allocation(
            raster_from(values, chunks=chunks),
            target_values=TARGET_VALUES,
            max_distance=np.inf,
            distance_metric="EUCLIDEAN",
        )
    )


def direction_values(values, target_values, chunks=None):
    return computed_values(
        direction(
            raster_from(values, chunks=chunks),
            target_values=target_values,
            max_distance=np.inf,
            distance_metric="EUCLIDEAN",
        )
    )


def test_allocation_tie_across_chunk_columns_uses_lowest_global_flat_index():
    values = source_values()
    numpy_result = allocation_values(values)

    dask_result = allocation(
        raster_from(values, chunks=(5, 3)),
        target_values=TARGET_VALUES,
        max_distance=np.inf,
        distance_metric="EUCLIDEAN",
    )
    dask_values = dask_result.data.compute()

    assert numpy_result[TIED_PIXEL] == LOWEST_FLAT_TARGET_VALUE
    assert dask_values[TIED_PIXEL] == LOWEST_FLAT_TARGET_VALUE
    np.testing.assert_allclose(dask_values, numpy_result, equal_nan=True)


def test_direction_tie_across_chunk_columns_matches_lowest_flat_target_direction():
    values = source_values()
    lowest_target_only = single_target_values(1, 3, 2.0)
    later_target_only = single_target_values(2, 2, 3.0)

    expected_direction = direction_values(lowest_target_only, target_values=[2.0])[TIED_PIXEL]
    later_target_direction = direction_values(later_target_only, target_values=[3.0])[TIED_PIXEL]
    assert not np.isclose(expected_direction, later_target_direction, equal_nan=True)

    numpy_result = direction_values(values, target_values=TARGET_VALUES)
    dask_result = direction_values(values, target_values=TARGET_VALUES, chunks=(5, 3))

    assert np.isclose(numpy_result[TIED_PIXEL], expected_direction, equal_nan=True)
    assert np.isclose(dask_result[TIED_PIXEL], expected_direction, equal_nan=True)
    np.testing.assert_allclose(dask_result, numpy_result, equal_nan=True)


@pytest.mark.parametrize("chunks", [(5, 5), (5, 3), (5, 2), (5, 1)])
def test_allocation_tied_pixel_is_invariant_to_chunk_column_layout(chunks):
    values = source_values()
    numpy_result = allocation_values(values)
    dask_result = allocation_values(values, chunks=chunks)

    assert numpy_result[TIED_PIXEL] == LOWEST_FLAT_TARGET_VALUE
    assert dask_result[TIED_PIXEL] == LOWEST_FLAT_TARGET_VALUE
    np.testing.assert_allclose(dask_result, numpy_result, equal_nan=True)


@pytest.mark.parametrize("chunks", [(5, 5), (5, 3), (5, 2), (5, 1)])
def test_direction_tied_pixel_is_invariant_to_chunk_column_layout(chunks):
    values = source_values()
    numpy_result = direction_values(values, target_values=TARGET_VALUES)
    dask_result = direction_values(values, target_values=TARGET_VALUES, chunks=chunks)

    np.testing.assert_allclose(dask_result, numpy_result, equal_nan=True)
    assert np.isclose(dask_result[TIED_PIXEL], numpy_result[TIED_PIXEL], equal_nan=True)
