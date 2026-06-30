import dask.array as da
import numpy as np
import pytest
import xarray as xr

from xrspatial.proximity import allocation, direction, proximity


TARGET_VALUE = 7.0


def _raster(values, x_coords, y_coords):
    return xr.DataArray(
        values,
        dims=("y", "x"),
        coords={"y": y_coords, "x": x_coords},
    )


def _as_dask(raster, chunks):
    return xr.DataArray(
        da.from_array(np.asarray(raster.data), chunks=chunks),
        dims=raster.dims,
        coords=raster.coords,
    )


def _great_circle_values(operation, raster, max_distance):
    result = operation(
        raster,
        target_values=[TARGET_VALUE],
        distance_metric="GREAT_CIRCLE",
        max_distance=max_distance,
    )
    return result.compute().values


@pytest.mark.parametrize(
    "operation",
    [proximity, allocation, direction],
    ids=["proximity", "allocation", "direction"],
)
def test_bounded_great_circle_dask_matches_eager_across_antimeridian(operation):
    x_coords = np.arange(-179.5, 180.0, 1.0)
    y_coords = np.array([-1.0, 0.0, 1.0])
    values = np.zeros((len(y_coords), len(x_coords)), dtype=np.float64)
    target_y = 1
    target_x = 0
    wrap_adjacent_x = len(x_coords) - 1
    values[target_y, target_x] = TARGET_VALUE

    eager = _raster(values, x_coords, y_coords)
    dask_backed = _as_dask(eager, chunks=(len(y_coords), 180))

    expected = _great_circle_values(operation, eager, max_distance=150_000.0)
    actual = _great_circle_values(operation, dask_backed, max_distance=150_000.0)

    np.testing.assert_allclose(actual, expected, rtol=1e-6, atol=1e-6, equal_nan=True)
    assert np.isfinite(expected[target_y, wrap_adjacent_x])
    assert np.isfinite(actual[target_y, wrap_adjacent_x])


@pytest.mark.parametrize(
    "operation",
    [proximity, allocation, direction],
    ids=["proximity", "allocation", "direction"],
)
def test_bounded_great_circle_dask_matches_eager_for_high_latitude_longitude_reach(operation):
    x_coords = np.arange(-160.0, 160.0, 1.0)
    y_coords = np.array([88.0, 89.0])
    values = np.zeros((len(y_coords), len(x_coords)), dtype=np.float64)
    target_y = 1
    target_x = 40   # lon -120
    reachable_x = 200  # lon 40, far in column space but close over the pole
    values[target_y, target_x] = TARGET_VALUE

    eager = _raster(values, x_coords, y_coords)
    dask_backed = _as_dask(eager, chunks=(len(y_coords), 160))

    expected = _great_circle_values(operation, eager, max_distance=230_000.0)
    actual = _great_circle_values(operation, dask_backed, max_distance=230_000.0)

    np.testing.assert_allclose(actual, expected, rtol=1e-6, atol=1e-6, equal_nan=True)
    assert np.isfinite(expected[target_y, reachable_x])
    assert np.isfinite(actual[target_y, reachable_x])
