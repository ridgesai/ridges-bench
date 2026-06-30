import numpy as np
import pytest
import xarray as xr
import dask.array as da
from dask import delayed
from shapely.geometry import box

from xrspatial.polygon_clip import clip_polygon


HEIGHT = 2560
WIDTH = 2560
CHUNK = 256
GEOMETRY = box(500, 500, 2000, 2000)
GRAPH_TASK_LIMIT = 4000


def make_representative_raster():
    values = np.arange(HEIGHT * WIDTH, dtype=np.float32).reshape(HEIGHT, WIDTH)
    data = da.from_array(values, chunks=(CHUNK, CHUNK))
    return xr.DataArray(
        data,
        dims=("y", "x"),
        coords={"y": np.arange(HEIGHT), "x": np.arange(WIDTH)},
        name="surface",
    )


def fail_if_computed(row_index, col_index):
    raise AssertionError("lazy source block was computed during graph construction")


def make_raster_with_failing_blocks():
    chunk = 32
    blocks = []
    for row_index in range(2):
        row = []
        for col_index in range(2):
            lazy_block = delayed(fail_if_computed)(row_index, col_index)
            row.append(da.from_delayed(lazy_block, shape=(chunk, chunk), dtype=np.float64))
        blocks.append(row)

    data = da.block(blocks)
    return xr.DataArray(
        data,
        dims=("y", "x"),
        coords={"y": np.arange(64), "x": np.arange(64)},
    )


@pytest.fixture(scope="module")
def representative_raster():
    return make_representative_raster()


def test_crop_true_returns_cropped_dask_raster_without_computing_source_blocks():
    raster = make_raster_with_failing_blocks()

    clipped = clip_polygon(raster, box(17, 17, 50, 50), crop=True)

    assert isinstance(clipped.data, da.Array)
    assert clipped.sizes["y"] == 34
    assert clipped.sizes["x"] == 34
    assert clipped["y"].values[0] == 17
    assert clipped["x"].values[0] == 17


def test_crop_true_partial_chunk_crop_keeps_bounded_lazy_graph(representative_raster):
    clipped = clip_polygon(representative_raster, GEOMETRY, crop=True)

    assert isinstance(clipped.data, da.Array)
    assert clipped.sizes["y"] == 1501
    assert clipped.sizes["x"] == 1501

    task_count = len(clipped.data.dask)
    assert task_count < GRAPH_TASK_LIMIT


def test_crop_true_values_match_crop_false_over_same_extent(representative_raster):
    cropped = clip_polygon(representative_raster, GEOMETRY, crop=True)
    not_cropped = clip_polygon(representative_raster, GEOMETRY, crop=False)
    matching_extent = not_cropped.sel(x=cropped["x"], y=cropped["y"])

    xr.testing.assert_equal(cropped.compute(), matching_extent.compute())


def test_crop_false_preserves_full_shape_and_existing_value_semantics(representative_raster):
    clipped = clip_polygon(representative_raster, GEOMETRY, crop=False)

    assert isinstance(clipped.data, da.Array)
    assert clipped.sizes["y"] == HEIGHT
    assert clipped.sizes["x"] == WIDTH

    sample = clipped.sel(x=[100, 1000, 2200], y=[100, 1000, 2200]).compute()
    expected = np.full((3, 3), np.nan, dtype=np.float32)
    expected[1, 1] = 1000 * WIDTH + 1000

    np.testing.assert_allclose(sample.values, expected, equal_nan=True)
