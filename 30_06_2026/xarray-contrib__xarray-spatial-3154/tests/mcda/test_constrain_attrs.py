import numpy as np
import pytest
import xarray as xr

from xrspatial.mcda.constrain import constrain


def make_suitability():
    return xr.DataArray(
        np.array([[0.1, 0.5, 0.9], [0.2, 0.6, 1.0]], dtype="float64"),
        dims=("y", "x"),
        coords={"y": [10.0, 0.0], "x": [100.0, 110.0, 120.0]},
        name="suitability",
        attrs={
            "res": (10.0, 10.0),
            "crs": "EPSG:3857",
            "nodatavals": (-9999.0,),
            "description": "weighted suitability surface",
        },
    )


def make_masks(suitability):
    return [
        xr.DataArray(
            np.array([[False, True, False], [False, False, False]]),
            dims=suitability.dims,
            coords=suitability.coords,
        ),
        xr.DataArray(
            np.array([[False, False, False], [True, False, True]]),
            dims=suitability.dims,
            coords=suitability.coords,
        ),
    ]


@pytest.mark.parametrize("mask_count", [0, 1, 2])
def test_constrain_preserves_suitability_attrs_for_any_number_of_exclusion_masks(mask_count):
    suitability = make_suitability()
    expected_attrs = dict(suitability.attrs)
    exclude = make_masks(suitability)[:mask_count]

    result = constrain(suitability, exclude=exclude)

    assert result.attrs == expected_attrs
    assert result.attrs["res"] == (10.0, 10.0)
    assert result.attrs["crs"] == "EPSG:3857"
    assert result.attrs["nodatavals"] == (-9999.0,)


def test_constrain_preserves_suitability_attrs_with_custom_fill_value():
    suitability = make_suitability()
    expected_attrs = dict(suitability.attrs)
    exclude = make_masks(suitability)[:1]

    result = constrain(suitability, exclude=exclude, fill=-123.5)

    assert result.attrs == expected_attrs
