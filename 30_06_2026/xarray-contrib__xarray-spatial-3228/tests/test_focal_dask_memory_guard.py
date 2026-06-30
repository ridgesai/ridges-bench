import dask.array as da
import numpy as np
import pytest
import xarray as xr

import xrspatial.focal as focal_module
from xrspatial.focal import apply, focal_stats, hotspots


RASTER_SHAPE = (100, 100)
SMALL_CHUNKS = (10, 10)
OVERSIZED_CHUNKS = (95, 95)
AVAILABLE_MEMORY_BYTES = 70_000


def set_available_memory(monkeypatch, available=AVAILABLE_MEMORY_BYTES):
    monkeypatch.setattr(focal_module, "_available_memory_bytes", lambda: available)


def kernel():
    return np.ones((3, 3), dtype=np.uint8)


def raster_values():
    return np.arange(np.prod(RASTER_SHAPE), dtype=np.float32).reshape(RASTER_SHAPE)


def eager_raster():
    return xr.DataArray(raster_values(), dims=("y", "x"))


def dask_raster(chunks):
    return xr.DataArray(da.from_array(raster_values(), chunks=chunks), dims=("y", "x"))


def call_apply(raster, kernel):
    return apply(raster, kernel=kernel, boundary="nan")


def call_focal_stats(raster, kernel):
    return focal_stats(raster, kernel=kernel, stats_funcs=["mean"], boundary="nan")


def call_hotspots(raster, kernel):
    return hotspots(raster, kernel=kernel, boundary="nan")


FOCAL_CALLS = (
    pytest.param(call_apply, id="apply"),
    pytest.param(call_focal_stats, id="focal_stats"),
    pytest.param(call_hotspots, id="hotspots"),
)


@pytest.mark.parametrize("call_focal", FOCAL_CALLS)
def test_dask_backed_raster_uses_chunk_memory_guard_when_full_raster_exceeds_limit(
    monkeypatch,
    call_focal,
):
    # At 70,000 available bytes, the half-memory guard is 35,000 bytes.
    # The padded 100x100 raster exceeds it, but a padded 10x10 chunk does not.
    set_available_memory(monkeypatch)

    result = call_focal(dask_raster(SMALL_CHUNKS), kernel())

    assert result.shape[-2:] == RASTER_SHAPE


@pytest.mark.parametrize("call_focal", FOCAL_CALLS)
def test_eager_raster_uses_full_raster_memory_guard(monkeypatch, call_focal):
    set_available_memory(monkeypatch)

    with pytest.raises(MemoryError):
        call_focal(eager_raster(), kernel())


@pytest.mark.parametrize("call_focal", FOCAL_CALLS)
def test_dask_backed_raster_rejects_largest_padded_chunk_over_limit(
    monkeypatch,
    call_focal,
):
    set_available_memory(monkeypatch)

    with pytest.raises(MemoryError):
        call_focal(dask_raster(OVERSIZED_CHUNKS), kernel())
