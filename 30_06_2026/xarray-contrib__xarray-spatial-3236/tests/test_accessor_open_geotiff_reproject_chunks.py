import dask.array as dask_array
import numpy as np
import pytest
import rasterio
import xarray as xr
from rasterio.transform import from_origin

from xrspatial.accessor import XrsSpatialDataArrayAccessor


SOURCE_BOUNDS = (0.0, 0.0, 1.0, 1.0)
SOURCE_CRS = "EPSG:4326"
SOURCE_HEIGHT = 64
SOURCE_WIDTH = 64
WEB_MERCATOR_BOUNDS_INSIDE_SOURCE = (25_000.0, 25_000.0, 75_000.0, 75_000.0)
WGS84_BOUNDS_INSIDE_SOURCE = (0.2, 0.2, 0.8, 0.8)


def transform_for_bounds(bounds, width, height):
    west, south, east, north = bounds
    return from_origin(west, north, (east - west) / width, (north - south) / height)


def coordinates_for_bounds(bounds, width, height):
    west, south, east, north = bounds
    x_step = (east - west) / width
    y_step = (north - south) / height
    x = west + x_step * (np.arange(width) + 0.5)
    y = north - y_step * (np.arange(height) + 0.5)
    return x, y


def write_geotiff_source(path):
    transform = transform_for_bounds(SOURCE_BOUNDS, SOURCE_WIDTH, SOURCE_HEIGHT)
    values = np.arange(SOURCE_HEIGHT * SOURCE_WIDTH, dtype="float32").reshape(
        SOURCE_HEIGHT, SOURCE_WIDTH
    )

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=SOURCE_WIDTH,
        height=SOURCE_HEIGHT,
        count=1,
        dtype="float32",
        crs=SOURCE_CRS,
        transform=transform,
    ) as dataset:
        dataset.write(values, 1)

    return str(path)


def make_caller(bounds, width, height, crs, chunks=None):
    x, y = coordinates_for_bounds(bounds, width, height)
    transform = transform_for_bounds(bounds, width, height)
    x_res = (bounds[2] - bounds[0]) / width
    y_res = (bounds[3] - bounds[1]) / height

    if chunks is None:
        values = np.zeros((height, width), dtype="float32")
    else:
        values = dask_array.zeros((height, width), chunks=chunks, dtype="float32")

    return xr.DataArray(
        values,
        dims=("y", "x"),
        coords={"y": y, "x": x},
        attrs={"crs": crs, "res": (x_res, y_res), "transform": transform},
    )


def first_yx_chunks(data_array):
    assert data_array.chunks is not None
    chunks = data_array.chunks
    if isinstance(chunks, dict):
        return int(chunks["y"][0]), int(chunks["x"][0])
    return (
        int(chunks[data_array.get_axis_num("y")][0]),
        int(chunks[data_array.get_axis_num("x")][0]),
    )


def test_coregistered_open_geotiff_uses_dask_caller_y_and_x_chunks(tmp_path):
    caller = make_caller(
        WGS84_BOUNDS_INSIDE_SOURCE,
        width=20,
        height=12,
        crs=SOURCE_CRS,
        chunks=(3, 5),
    )
    assert first_yx_chunks(caller) == (3, 5)

    source = write_geotiff_source(tmp_path / "source.tif")
    result = XrsSpatialDataArrayAccessor(caller).open_geotiff(
        source,
        coregister=True,
    )
    assert first_yx_chunks(result) == (3, 5)


def test_auto_reprojected_open_geotiff_uses_dask_caller_y_and_x_chunks(tmp_path):
    caller = make_caller(
        WEB_MERCATOR_BOUNDS_INSIDE_SOURCE,
        width=20,
        height=12,
        crs="EPSG:3857",
        chunks=(3, 5),
    )
    assert first_yx_chunks(caller) == (3, 5)

    source = write_geotiff_source(tmp_path / "source.tif")
    result = XrsSpatialDataArrayAccessor(caller).open_geotiff(
        source,
        auto_reproject=True,
    )
    assert first_yx_chunks(result) == (3, 5)


@pytest.mark.parametrize(
    ("caller_crs", "caller_bounds", "open_kwargs"),
    [
        (SOURCE_CRS, WGS84_BOUNDS_INSIDE_SOURCE, {"coregister": True}),
        (
            "EPSG:3857",
            WEB_MERCATOR_BOUNDS_INSIDE_SOURCE,
            {"auto_reproject": True},
        ),
    ],
)
def test_reprojected_open_geotiff_uses_explicit_chunks_for_numpy_caller(
    caller_crs,
    caller_bounds,
    open_kwargs,
    tmp_path,
):
    caller = make_caller(
        caller_bounds,
        width=10,
        height=8,
        crs=caller_crs,
        chunks=None,
    )
    assert caller.chunks is None

    source = write_geotiff_source(tmp_path / "source.tif")
    result = XrsSpatialDataArrayAccessor(caller).open_geotiff(
        source,
        chunks=2,
        **open_kwargs,
    )
    assert first_yx_chunks(result) == (2, 2)
