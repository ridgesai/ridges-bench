from collections import Counter

import dask
import dask.array as da
from dask import delayed
import numpy as np
import pytest
import xarray as xr

from xrspatial.geotiff._writers.eager import to_geotiff

rasterio = pytest.importorskip("rasterio")

SCALE = 0.5
OFFSET = -7.0
TARGET_DTYPE = "int16"


def packing_attrs():
    return {
        "scale_factor": SCALE,
        "add_offset": OFFSET,
        "mask_and_scale_dtype": TARGET_DTYPE,
        "gdal_metadata": {"SCALE": str(SCALE), "OFFSET": str(OFFSET)},
    }


def unpack_values(packed):
    return packed.astype(np.float64) * SCALE + OFFSET


def delayed_chunk(label, values, events):
    values = np.asarray(values, dtype=np.float64)

    def produce():
        events.append(label)
        return np.array(values, copy=True)

    task = delayed(produce, pure=False)()
    return da.from_delayed(task, shape=values.shape, dtype=values.dtype)


def delayed_data_array(unpacked, chunk_shape, events):
    rows = []
    labels = []
    row_chunks, col_chunks = chunk_shape

    for row_start in range(0, unpacked.shape[0], row_chunks):
        row = []
        for col_start in range(0, unpacked.shape[1], col_chunks):
            label = f"r{row_start // row_chunks}c{col_start // col_chunks}"
            labels.append(label)
            values = unpacked[
                row_start : row_start + row_chunks,
                col_start : col_start + col_chunks,
            ]
            row.append(delayed_chunk(label, values, events))
        rows.append(row)

    data = da.block(rows)
    return xr.DataArray(data, dims=("y", "x"), attrs=packing_attrs()), labels


def read_packed_raster(path):
    with rasterio.open(path) as src:
        tags = src.tags()
        return {
            "array": src.read(1),
            "dtype": src.dtypes[0],
            "scale": float(tags["SCALE"]),
            "offset": float(tags["OFFSET"]),
            "nodata": src.nodata,
        }


def assert_no_sentinel_nan_pack_error(exc_info):
    message = str(exc_info.value).lower()
    assert "integer dtype" in message
    assert "nan" in message
    assert "nodata" in message


def test_clean_dask_pack_write_computes_source_chunks_once_and_matches_numpy(tmp_path):
    packed = np.arange(64 * 64, dtype=np.int16).reshape(64, 64)
    unpacked = unpack_values(packed)
    events = []
    dask_data, labels = delayed_data_array(unpacked, (32, 32), events)

    dask_path = tmp_path / "clean_dask.tif"
    with dask.config.set(scheduler="synchronous"):
        to_geotiff(dask_data, dask_path, pack=True)

    assert Counter(events) == Counter({label: 1 for label in labels})

    numpy_path = tmp_path / "clean_numpy.tif"
    numpy_data = xr.DataArray(
        np.array(unpacked, copy=True), dims=("y", "x"), attrs=packing_attrs()
    )
    to_geotiff(numpy_data, numpy_path, pack=True)

    dask_raster = read_packed_raster(dask_path)
    numpy_raster = read_packed_raster(numpy_path)

    assert dask_raster["dtype"] == numpy_raster["dtype"] == TARGET_DTYPE
    np.testing.assert_array_equal(numpy_raster["array"], packed)
    np.testing.assert_array_equal(dask_raster["array"], numpy_raster["array"])
    assert dask_raster["scale"] == pytest.approx(numpy_raster["scale"])
    assert dask_raster["offset"] == pytest.approx(numpy_raster["offset"])
    assert dask_raster["scale"] == pytest.approx(SCALE)
    assert dask_raster["offset"] == pytest.approx(OFFSET)
    assert dask_raster["nodata"] is None
    assert numpy_raster["nodata"] is None


def test_dask_nan_without_nodata_raises_from_write_chunk_compute(tmp_path):
    chunk_shape = (256, 256)
    nan_chunk = unpack_values(np.zeros(chunk_shape, dtype=np.int16))
    nan_chunk[0, 0] = np.nan
    later_chunks = [
        unpack_values(np.full(chunk_shape, value, dtype=np.int16))
        for value in range(1, 5)
    ]

    events = []
    labels = ["nan-row"] + [f"later-row-{idx}" for idx in range(1, 5)]
    chunks = [delayed_chunk(labels[0], nan_chunk, events)]
    chunks.extend(
        delayed_chunk(label, values, events)
        for label, values in zip(labels[1:], later_chunks)
    )
    data = xr.DataArray(
        da.concatenate(chunks, axis=0), dims=("y", "x"), attrs=packing_attrs()
    )

    with pytest.raises(ValueError) as exc_info:
        with dask.config.set(scheduler="synchronous"):
            to_geotiff(
                data,
                tmp_path / "dask_nan.tif",
                pack=True,
                streaming_buffer_bytes=(
                    chunk_shape[0]
                    * chunk_shape[1]
                    * np.dtype(np.float64).itemsize
                    + 4096
                ),
            )

    assert_no_sentinel_nan_pack_error(exc_info)
    assert "nan-row" in events
    assert set(labels[1:]) - set(events)


def test_numpy_nan_without_nodata_is_validated_eagerly(tmp_path):
    packed = np.arange(32 * 32, dtype=np.int16).reshape(32, 32)
    unpacked = unpack_values(packed)
    unpacked[4, 7] = np.nan
    data = xr.DataArray(unpacked, dims=("y", "x"), attrs=packing_attrs())
    path = tmp_path / "numpy_nan.tif"

    with pytest.raises(ValueError) as exc_info:
        to_geotiff(data, path, pack=True)

    assert_no_sentinel_nan_pack_error(exc_info)
    assert not path.exists()
