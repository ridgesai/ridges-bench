import contextlib
import re
import warnings

import numpy as np
import pytest
import xarray as xr

rasterio = pytest.importorskip("rasterio")
pytest.importorskip("rioxarray")

from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds

from xrspatial.accessor import (
    XrsSpatialDataArrayAccessor,
    XrsSpatialDatasetAccessor,
)


def _caller_array(*, crs="EPSG:3857", width=100, height=100, west=0.0, north=100.0, pixel_size=1.0):
    x = west + pixel_size * (np.arange(width) + 0.5)
    y = north - pixel_size * (np.arange(height) + 0.5)
    data = np.zeros((height, width), dtype=np.float32)
    arr = xr.DataArray(data, dims=("y", "x"), coords={"y": y, "x": x}, name="caller")
    transform = from_origin(west, north, pixel_size, pixel_size)
    return arr.rio.write_crs(crs).rio.write_transform(transform)


def _caller_dataset(**kwargs):
    return xr.Dataset({"caller": _caller_array(**kwargs)})


@contextlib.contextmanager
def _memory_geotiff(*, crs="EPSG:3857", west=20.0, north=80.0, width=20, height=20, pixel_width=1.0, pixel_height=1.0):
    transform = from_origin(west, north, pixel_width, pixel_height)
    data = np.arange(width * height, dtype=np.float32).reshape(height, width)
    with MemoryFile(ext=".tif") as memfile:
        with memfile.open(
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype=data.dtype,
            crs=crs,
            transform=transform,
        ) as dataset:
            dataset.write(data, 1)
        yield memfile.name


def _record_warnings(call):
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        result = call()
    return result, records


def _is_sparse_coregister_warning(record):
    message = str(record.message).lower()
    return (
        issubclass(record.category, UserWarning)
        and "covers only" in message
        and "caller grid" in message
        and "mostly nan" in message
    )


def _sparse_coregister_warnings(records):
    return [record for record in records if _is_sparse_coregister_warning(record)]


def _assert_sparse_warning_message(record):
    message = str(record.message)
    lower = message.lower()
    assert issubclass(record.category, UserWarning)
    assert re.search(r"covers only\s+\d+(?:\.\d+)?%", message)
    assert "caller grid" in lower
    assert "mostly nan" in lower
    assert "small raster first" in lower
    assert "crop" in lower and "caller" in lower
    assert "coregister" in lower


def _assert_aligned_to_caller(result, caller):
    assert result.sizes["x"] == caller.sizes["x"]
    assert result.sizes["y"] == caller.sizes["y"]
    np.testing.assert_allclose(result.coords["x"].values, caller.coords["x"].values)
    np.testing.assert_allclose(result.coords["y"].values, caller.coords["y"].values)


def test_dataarray_coregister_warns_for_sparse_source_and_keeps_caller_grid():
    caller = _caller_array()

    with _memory_geotiff(west=20.0, north=80.0, width=20, height=20) as source:
        result, records = _record_warnings(
            lambda: XrsSpatialDataArrayAccessor(caller).open_geotiff(source, coregister=True)
        )

    sparse_warnings = _sparse_coregister_warnings(records)
    assert sparse_warnings
    _assert_sparse_warning_message(sparse_warnings[0])
    _assert_aligned_to_caller(result, caller)


def test_dataset_coregister_warns_for_sparse_source_and_keeps_caller_grid():
    caller = _caller_dataset()

    with _memory_geotiff(west=20.0, north=80.0, width=20, height=20) as source:
        result, records = _record_warnings(
            lambda: XrsSpatialDatasetAccessor(caller).open_geotiff(source, coregister=True)
        )

    sparse_warnings = _sparse_coregister_warnings(records)
    assert sparse_warnings
    _assert_sparse_warning_message(sparse_warnings[0])
    _assert_aligned_to_caller(result, caller)


def test_coregister_does_not_emit_sparse_warning_when_source_covers_at_least_ten_percent():
    caller = _caller_array()

    with _memory_geotiff(west=0.0, north=100.0, width=10, height=100) as source:
        _, records = _record_warnings(
            lambda: XrsSpatialDataArrayAccessor(caller).open_geotiff(source, coregister=True)
        )

    assert not _sparse_coregister_warnings(records)


def test_auto_reproject_does_not_emit_sparse_coregistration_warning_for_sparse_source():
    caller = _caller_array()

    with _memory_geotiff(west=20.0, north=80.0, width=20, height=20) as source:
        _, records = _record_warnings(
            lambda: XrsSpatialDataArrayAccessor(caller).open_geotiff(source, auto_reproject=True)
        )

    assert not _sparse_coregister_warnings(records)


def test_coregister_sparse_warning_uses_transformed_footprint_for_different_crs():
    caller = _caller_array(
        crs="EPSG:4326",
        width=100,
        height=100,
        west=-1.0,
        north=1.0,
        pixel_size=0.02,
    )
    west, south, east, north = transform_bounds(
        "EPSG:4326",
        "EPSG:3857",
        -0.1,
        -0.1,
        0.1,
        0.1,
        densify_pts=21,
    )
    pixel_width = (east - west) / 20
    pixel_height = (north - south) / 20

    with _memory_geotiff(
        crs="EPSG:3857",
        west=west,
        north=north,
        width=20,
        height=20,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
    ) as source:
        _, records = _record_warnings(
            lambda: XrsSpatialDataArrayAccessor(caller).open_geotiff(source, coregister=True)
        )

    sparse_warnings = _sparse_coregister_warnings(records)
    assert sparse_warnings
    _assert_sparse_warning_message(sparse_warnings[0])
