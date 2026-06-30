import io

import numpy as np
import xarray as xr

from xrspatial.geotiff import open_geotiff, to_geotiff


def two_band_values():
    return np.dstack(
        [
            np.arange(1, 7).reshape(2, 3),
            np.arange(10, 70, 10).reshape(2, 3),
        ]
    ).astype(np.uint16)


def write_multiband_geotiff(gdal_metadata):
    values = two_band_values()
    data = xr.DataArray(
        values,
        dims=("y", "x", "band"),
        coords={"y": [1.5, 0.5], "x": [0.5, 1.5, 2.5], "band": [0, 1]},
        attrs={"crs": 4326, "nodata": 65535, "gdal_metadata": gdal_metadata},
    )
    out = io.BytesIO()
    to_geotiff(data, out, compression="none", tiled=False)
    out.seek(0)
    return out, values


def write_packed_geotiff(data):
    out = io.BytesIO()
    to_geotiff(data, out, pack=True, compression="none", tiled=False)
    out.seek(0)
    return out


def array_values(data):
    return np.asarray(data.data)


def test_packed_single_band_subset_reopens_with_unpack_without_band_selection():
    source, values = write_multiband_geotiff(
        {("SCALE", 0): "0.1", ("SCALE", 1): "0.2"}
    )

    subset = open_geotiff(source, band=1, unpack=True)
    np.testing.assert_allclose(array_values(subset), values[:, :, 1] * 0.2)

    packed = write_packed_geotiff(subset)
    reopened = open_geotiff(packed, unpack=True)

    np.testing.assert_allclose(array_values(reopened), array_values(subset))


def test_packed_single_band_subset_uses_selected_band_scale_for_band_zero():
    source, values = write_multiband_geotiff(
        {("SCALE", 0): "0.1", ("SCALE", 1): "0.2"}
    )
    assert values[1, 1, 1] == 50

    subset = open_geotiff(source, band=1, unpack=True)
    packed = write_packed_geotiff(subset)
    reopened = open_geotiff(packed, unpack=True, band=0)

    np.testing.assert_allclose(array_values(reopened), array_values(subset))
    np.testing.assert_allclose(array_values(reopened)[1, 1], 10.0)


def test_packed_single_band_subset_preserves_selected_band_offset():
    source, values = write_multiband_geotiff(
        {
            ("SCALE", 0): "0.5",
            ("SCALE", 1): "2.0",
            ("OFFSET", 0): "-20.0",
            ("OFFSET", 1): "3.0",
        }
    )

    subset = open_geotiff(source, band=1, unpack=True)
    np.testing.assert_allclose(array_values(subset), values[:, :, 1] * 2.0 + 3.0)

    packed = write_packed_geotiff(subset)
    reopened = open_geotiff(packed, unpack=True, band=0)

    np.testing.assert_allclose(array_values(reopened), array_values(subset))
    np.testing.assert_allclose(array_values(reopened)[1, 1], 103.0)


def test_dataset_level_scale_offset_round_trips_when_packed():
    source, values = write_multiband_geotiff({"SCALE": "0.25", "OFFSET": "2.0"})

    subset = open_geotiff(source, band=1, unpack=True)
    np.testing.assert_allclose(array_values(subset), values[:, :, 1] * 0.25 + 2.0)

    packed = write_packed_geotiff(subset)
    reopened = open_geotiff(packed, unpack=True)

    np.testing.assert_allclose(array_values(reopened), array_values(subset))
