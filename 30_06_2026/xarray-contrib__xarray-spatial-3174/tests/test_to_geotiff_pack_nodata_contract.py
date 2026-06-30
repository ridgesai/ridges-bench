import numpy as np
import pytest
import rasterio
import xarray as xr

from xrspatial.geotiff._writers.eager import to_geotiff


HOLE_MASK = np.array(
    [
        [False, True, False],
        [True, False, False],
    ],
    dtype=bool,
)


def unpacked_int16_data(attrs_nodata):
    values = np.array(
        [
            [10.0, np.nan, 30.0],
            [np.nan, 50.0, 60.0],
        ],
        dtype=np.float32,
    )
    return xr.DataArray(
        values,
        dims=("y", "x"),
        coords={
            "y": np.array([1.5, 0.5], dtype=np.float64),
            "x": np.array([0.5, 1.5, 2.5], dtype=np.float64),
        },
        name="band1",
        attrs={
            "scale_factor": 1.0,
            "add_offset": 0.0,
            "mask_and_scale_dtype": "int16",
            "nodata": np.int16(attrs_nodata),
            "crs": "EPSG:4326",
        },
    )


def read_written(data, tmp_path, name, **to_geotiff_kwargs):
    path = tmp_path / f"{name}.tif"
    to_geotiff(data, str(path), **to_geotiff_kwargs)
    with rasterio.open(path) as dataset:
        return {
            "raw": dataset.read(1, masked=False),
            "masked": dataset.read(1, masked=True),
            "nodata": dataset.nodatavals[0],
        }


def assert_holes_are_nodata(written, expected_nodata):
    raw = written["raw"]
    np.testing.assert_array_equal(
        raw[HOLE_MASK],
        np.full(HOLE_MASK.sum(), expected_nodata, dtype=raw.dtype),
    )
    assert written["nodata"] == pytest.approx(float(expected_nodata))


def test_pack_with_explicit_nodata_fills_nan_holes_with_override_not_attrs_sentinel(
    tmp_path,
):
    attrs_nodata = -32768
    explicit_nodata = -9999

    written = read_written(
        unpacked_int16_data(attrs_nodata),
        tmp_path,
        "explicit_override_pixels",
        pack=True,
        nodata=explicit_nodata,
    )

    assert_holes_are_nodata(written, explicit_nodata)
    assert not np.any(written["raw"][HOLE_MASK] == attrs_nodata)


def test_pack_with_explicit_nodata_writes_holes_that_masked_read_treats_as_nodata(
    tmp_path,
):
    explicit_nodata = -9999

    written = read_written(
        unpacked_int16_data(-32768),
        tmp_path,
        "explicit_override_masked_read",
        pack=True,
        nodata=explicit_nodata,
    )

    assert_holes_are_nodata(written, explicit_nodata)
    np.testing.assert_array_equal(np.ma.getmaskarray(written["masked"]), HOLE_MASK)


def test_pack_without_explicit_nodata_uses_attrs_sentinel_for_pixels_and_tag(tmp_path):
    attrs_nodata = -12345

    written = read_written(
        unpacked_int16_data(attrs_nodata),
        tmp_path,
        "attrs_sentinel",
        pack=True,
    )

    assert_holes_are_nodata(written, attrs_nodata)
    np.testing.assert_array_equal(np.ma.getmaskarray(written["masked"]), HOLE_MASK)


@pytest.mark.parametrize(
    ("bad_nodata", "case_name"),
    [
        (int(np.iinfo(np.int16).min) - 1, "too_low"),
        (int(np.iinfo(np.int16).max) + 1, "too_high"),
        (-9999.5, "fractional"),
    ],
)
def test_pack_rejects_explicit_nodata_not_representable_in_packed_integer_dtype(
    bad_nodata, case_name, tmp_path
):
    path = tmp_path / f"invalid_{case_name}.tif"
    with pytest.raises(ValueError):
        to_geotiff(
            unpacked_int16_data(-32768),
            str(path),
            pack=True,
            nodata=bad_nodata,
        )
