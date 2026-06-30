import struct

import numpy as np

from xrspatial.geotiff import open_geotiff


TIFF_ASCII = 2
TIFF_SHORT = 3
TIFF_LONG = 4
TIFF_DOUBLE = 12


def pack_tiff_values(type_id, values):
    if type_id == TIFF_ASCII:
        return values
    fmt = {TIFF_SHORT: "H", TIFF_LONG: "I", TIFF_DOUBLE: "d"}[type_id]
    return struct.pack("<" + fmt * len(values), *values)


def aligned(value, multiple):
    return ((value + multiple - 1) // multiple) * multiple


def extra_data_size(tags):
    total = 0
    for _, type_id, values in sorted(tags):
        raw = pack_tiff_values(type_id, values)
        if len(raw) > 4:
            total = aligned(total + len(raw), 2)
    return total


def write_geotiff(path, array, nodata):
    data = np.asarray(array)
    assert data.ndim == 2

    if data.dtype.kind == "i":
        sample_format = 2
    elif data.dtype.kind == "u":
        sample_format = 1
    else:
        raise AssertionError(f"unsupported test dtype: {data.dtype}")

    height, width = data.shape
    little_dtype = data.dtype.newbyteorder("<")
    pixel_bytes = data.astype(little_dtype, copy=False).tobytes(order="C")
    nodata_ascii = str(int(nodata)).encode("ascii") + b"\x00"

    tags_without_strip_offset = [
        (256, TIFF_LONG, [width]),
        (257, TIFF_LONG, [height]),
        (258, TIFF_SHORT, [data.dtype.itemsize * 8]),
        (259, TIFF_SHORT, [1]),
        (262, TIFF_SHORT, [1]),
        (273, TIFF_LONG, [0]),
        (277, TIFF_SHORT, [1]),
        (278, TIFF_LONG, [height]),
        (279, TIFF_LONG, [len(pixel_bytes)]),
        (284, TIFF_SHORT, [1]),
        (339, TIFF_SHORT, [sample_format]),
        (33550, TIFF_DOUBLE, [1.0, 1.0, 0.0]),
        (33922, TIFF_DOUBLE, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        (34735, TIFF_SHORT, [1, 1, 0, 0]),
        (42113, TIFF_ASCII, nodata_ascii),
    ]
    ifd_end = 8 + 2 + 12 * len(tags_without_strip_offset) + 4
    pixel_offset = aligned(
        ifd_end + extra_data_size(tags_without_strip_offset), data.dtype.itemsize
    )
    tags = [
        (tag, type_id, [pixel_offset] if tag == 273 else values)
        for tag, type_id, values in tags_without_strip_offset
    ]

    entries = bytearray()
    extra = bytearray()
    for tag, type_id, values in sorted(tags):
        raw = pack_tiff_values(type_id, values)
        count = len(raw) if type_id == TIFF_ASCII else len(values)
        if len(raw) <= 4:
            value_or_offset = raw.ljust(4, b"\x00")
        else:
            value_or_offset = struct.pack("<I", ifd_end + len(extra))
            extra.extend(raw)
            while len(extra) % 2:
                extra.extend(b"\x00")
        entries.extend(struct.pack("<HHI", tag, type_id, count))
        entries.extend(value_or_offset)

    tiff = bytearray(b"II" + struct.pack("<HI", 42, 8))
    tiff.extend(struct.pack("<H", len(tags)))
    tiff.extend(entries)
    tiff.extend(struct.pack("<I", 0))
    tiff.extend(extra)
    tiff.extend(b"\x00" * (pixel_offset - len(tiff)))
    tiff.extend(pixel_bytes)
    path.write_bytes(tiff)
    return path


def values_2d(data_array):
    values = np.asarray(data_array.values)
    if values.ndim == 2:
        return values
    if values.ndim == 3 and values.shape[0] == 1:
        return values[0]
    if values.ndim == 3 and values.shape[-1] == 1:
        return values[..., 0]
    raise AssertionError(f"expected a single-band raster, got shape {values.shape}")


def open_chunked(path):
    last_error = None
    for chunks in ({"y": 2, "x": 2}, (2, 2), 2):
        try:
            return open_geotiff(str(path), masked=True, chunks=chunks)
        except (TypeError, ValueError) as exc:
            last_error = exc
    raise AssertionError("open_geotiff did not accept a chunk specification") from last_error


def test_eager_masked_integer_read_promotes_to_float64_without_sentinel_hit(tmp_path):
    sentinel = np.iinfo(np.int64).max
    source = np.array(
        [[sentinel - 1, sentinel - 100], [sentinel - 511, sentinel - 512]],
        dtype=np.int64,
    )
    path = write_geotiff(tmp_path / "int64_no_exact_nodata.tif", source, sentinel)

    result = open_geotiff(str(path), masked=True)
    values = values_2d(result)

    assert np.dtype(result.dtype) == np.dtype(np.float64)
    assert values.dtype == np.dtype(np.float64)
    assert np.all(np.isfinite(values))
    if "nodata_pixels_present" in result.attrs:
        assert bool(result.attrs["nodata_pixels_present"]) is False


def test_eager_int64_max_nodata_masks_only_exact_source_sentinel(tmp_path):
    sentinel = np.iinfo(np.int64).max
    source = np.array(
        [
            [sentinel, sentinel - 1, sentinel - 100],
            [sentinel - 511, sentinel - 512, sentinel - 2048],
        ],
        dtype=np.int64,
    )
    path = write_geotiff(tmp_path / "int64_exact_nodata.tif", source, sentinel)

    result = open_geotiff(str(path), masked=True)
    values = values_2d(result)

    assert np.dtype(result.dtype) == np.dtype(np.float64)
    np.testing.assert_array_equal(np.isnan(values), source == sentinel)
    assert np.all(np.isfinite(values[source != sentinel]))


def test_eager_uint64_max_nodata_masks_only_exact_source_sentinel(tmp_path):
    sentinel = np.iinfo(np.uint64).max
    source = np.array(
        [
            [sentinel, sentinel - 1, sentinel - 100],
            [sentinel - 511, sentinel - 512, sentinel - 2048],
        ],
        dtype=np.uint64,
    )
    path = write_geotiff(tmp_path / "uint64_exact_nodata.tif", source, sentinel)

    result = open_geotiff(str(path), masked=True)
    values = values_2d(result)

    assert np.dtype(result.dtype) == np.dtype(np.float64)
    np.testing.assert_array_equal(np.isnan(values), source == sentinel)
    assert np.all(np.isfinite(values[source != sentinel]))


def test_eager_and_chunked_reads_agree_on_int64_native_width_nodata_mask(tmp_path):
    sentinel = np.iinfo(np.int64).max
    source = np.array(
        [
            [sentinel, sentinel - 1, sentinel - 100],
            [sentinel - 511, sentinel - 512, 2**53 + 1],
        ],
        dtype=np.int64,
    )
    path = write_geotiff(tmp_path / "int64_eager_chunked_parity.tif", source, sentinel)

    eager = open_geotiff(str(path), masked=True)
    chunked = open_chunked(path)
    eager_values = values_2d(eager)
    chunked_values = values_2d(chunked)

    assert np.dtype(eager.dtype) == np.dtype(np.float64)
    assert np.dtype(chunked.dtype) == np.dtype(np.float64)
    np.testing.assert_array_equal(np.isnan(eager_values), source == sentinel)
    np.testing.assert_array_equal(np.isnan(chunked_values), source == sentinel)
    np.testing.assert_array_equal(np.isnan(eager_values), np.isnan(chunked_values))
