import numpy as np
import pytest
import xarray as xr

from xrspatial.reproject import reproject


INTEGER_NODATA = -32768
WIDE_BOUNDS = (-2_000_000.0, 5_000_000.0, 2_000_000.0, 9_000_000.0)
NO_OVERLAP_BOUNDS = (5_000_000.0, 5_000_000.0, 6_000_000.0, 6_000_000.0)


def source_coords(size):
    return {
        "y": np.linspace(52.0, 51.0, size),
        "x": np.linspace(-2.0, -1.0, size),
    }


def int16_values(size):
    values = np.arange(size * size, dtype=np.int32).reshape(size, size) % 1000
    return values.astype(np.int16)


def int16_raster(size=200, chunks=None):
    data = int16_values(size)
    if chunks is not None:
        dask_array = pytest.importorskip("dask.array")
        data = dask_array.from_array(data, chunks=chunks)
    return xr.DataArray(
        data,
        dims=("y", "x"),
        coords=source_coords(size),
        attrs={"crs": "EPSG:4326", "nodata": INTEGER_NODATA},
    )


def float32_raster(size=200, chunks=None):
    data = np.linspace(0.0, 1.0, size * size, dtype=np.float32).reshape(size, size)
    if chunks is not None:
        dask_array = pytest.importorskip("dask.array")
        data = dask_array.from_array(data, chunks=chunks)
    return xr.DataArray(
        data,
        dims=("y", "x"),
        coords=source_coords(size),
        attrs={"crs": "EPSG:4326"},
    )


def test_dask_integer_reproject_keeps_dtype_and_fills_empty_chunks():
    raster = int16_raster(chunks=(64, 64))

    result = reproject(
        raster,
        "EPSG:3857",
        bounds=WIDE_BOUNDS,
        resolution=20_000,
        chunk_size=64,
        resampling="nearest",
    )

    assert result.dtype == np.dtype(np.int16)
    computed = result.compute()
    assert computed.dtype == np.dtype(np.int16)
    assert computed.values[0, 0] == INTEGER_NODATA
    assert (computed.values != INTEGER_NODATA).any()


def test_numpy_integer_reproject_no_overlap_returns_integer_nodata_fill():
    raster = int16_raster(size=32)

    result = reproject(
        raster,
        "EPSG:3857",
        bounds=NO_OVERLAP_BOUNDS,
        resolution=20_000,
        resampling="nearest",
    )

    assert result.dtype == np.dtype(np.int16)
    expected = np.full(result.shape, INTEGER_NODATA, dtype=np.int16)
    np.testing.assert_array_equal(result.values, expected)


def test_dask_float_empty_chunks_keep_float64_fill_behavior():
    raster = float32_raster(chunks=(64, 64))

    result = reproject(
        raster,
        "EPSG:3857",
        bounds=WIDE_BOUNDS,
        resolution=20_000,
        chunk_size=64,
        resampling="nearest",
    )

    assert np.issubdtype(result.dtype, np.floating)
    computed = result.compute()
    assert computed.dtype == np.dtype(np.float64)
    assert np.isnan(computed.values[0, 0])
    assert np.isfinite(computed.values).any()
