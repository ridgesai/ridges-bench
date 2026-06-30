import numpy as np
import pytest
import xarray as xr

from xrspatial.zonal import hypsometric_integral


def _zones():
    return xr.DataArray(
        np.array([[1, 1, 2], [1, 2, 2]], dtype=np.int16),
        dims=("y", "x"),
        name="zones",
    )


def _real_values():
    return xr.DataArray(
        np.array([[0.0, 2.0, 10.0], [4.0, 10.0, 30.0]], dtype=np.float64),
        dims=("y", "x"),
        name="values",
    )


def _assert_real_numeric_values_error(excinfo):
    message = str(excinfo.value).lower()
    assert "values" in message
    assert "real" in message
    assert "numeric" in message or "number" in message


def _assert_zone_values(result, expected, zones=None):
    if zones is not None and isinstance(result, xr.DataArray) and result.shape == zones.shape:
        for zone, value in expected.items():
            actual = result.values[zones.values == zone]
            assert np.allclose(actual, value, equal_nan=False)
        return

    if hasattr(result, "to_dataframe"):
        frame = result.to_dataframe().reset_index()
    elif hasattr(result, "columns") and hasattr(result, "reset_index"):
        frame = result.reset_index()
    else:
        pytest.fail(f"unexpected result type from hypsometric_integral: {type(result)!r}")

    columns = list(frame.columns)
    for zone_col in columns:
        try:
            zone_values = [int(zone) for zone in frame[zone_col]]
        except (TypeError, ValueError):
            continue

        if not set(expected).issubset(zone_values):
            continue

        for value_col in columns:
            if value_col == zone_col:
                continue
            try:
                by_zone = {
                    int(zone): float(value)
                    for zone, value in zip(frame[zone_col], frame[value_col])
                }
            except (TypeError, ValueError):
                continue

            if all(
                zone in by_zone and by_zone[zone] == pytest.approx(value)
                for zone, value in expected.items()
            ):
                return

    pytest.fail(f"result did not contain expected per-zone values: {result!r}")


def test_complex_values_dtype_is_rejected_as_not_real_numeric():
    values = xr.DataArray(
        np.array(
            [[0.0 + 1.0j, 2.0 + 0.5j, 10.0 + 3.0j], [4.0, 10.0, 30.0]],
            dtype=np.complex128,
        ),
        dims=("y", "x"),
        name="values",
    )

    with pytest.raises(ValueError) as excinfo:
        hypsometric_integral(_zones(), values)

    _assert_real_numeric_values_error(excinfo)


def test_non_numeric_values_dtype_is_rejected_as_not_real_numeric():
    values = xr.DataArray(
        np.array([["low", "mid", "high"], ["mid", "high", "low"]], dtype=object),
        dims=("y", "x"),
        name="values",
    )

    with pytest.raises(ValueError) as excinfo:
        hypsometric_integral(_zones(), values)

    _assert_real_numeric_values_error(excinfo)


@pytest.mark.parametrize(
    ("zones", "values"),
    [
        (
            xr.DataArray(np.array([1, 1, 2], dtype=np.int16), dims=("x",), name="zones"),
            _real_values(),
        ),
        (
            _zones(),
            xr.DataArray(
                np.arange(12, dtype=np.float64).reshape(2, 2, 3),
                dims=("band", "y", "x"),
                name="values",
            ),
        ),
    ],
    ids=["zones-not-2d", "values-not-2d"],
)
def test_non_2d_raster_inputs_are_rejected(zones, values):
    with pytest.raises(ValueError):
        hypsometric_integral(zones, values)


def test_valid_real_numeric_2d_rasters_compute_hypsometric_integral_by_zone():
    zones = _zones()
    result = hypsometric_integral(zones, _real_values())

    _assert_zone_values(result, {1: 0.5, 2: 1.0 / 3.0}, zones=zones)
