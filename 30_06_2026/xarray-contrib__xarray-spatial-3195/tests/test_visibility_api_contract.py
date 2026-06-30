import inspect
import types
from typing import Optional, Union, get_args, get_origin, get_type_hints

import numpy as np
import pytest
import xarray as xr

from xrspatial.visibility import (
    cumulative_viewshed,
    line_of_sight,
    visibility_frequency,
)


@pytest.fixture
def raster():
    return xr.DataArray(
        np.zeros((3, 3), dtype=np.float64),
        dims=("y", "x"),
        coords={"y": [0.0, 1.0, 2.0], "x": [0.0, 1.0, 2.0]},
    )


@pytest.fixture
def observers():
    return [{"x": 1.0, "y": 1.0}]


def is_optional_float_annotation(annotation):
    if annotation == Optional[float]:
        return True

    origin = get_origin(annotation)
    union_type = getattr(types, "UnionType", None)
    valid_union_origins = {Union}
    if union_type is not None:
        valid_union_origins.add(union_type)

    return origin in valid_union_origins and set(get_args(annotation)) == {
        float,
        type(None),
    }


def test_cumulative_viewshed_has_default_output_name(raster, observers):
    result = cumulative_viewshed(raster, observers)

    assert isinstance(result, xr.DataArray)
    assert result.name == "cumulative_viewshed"


@pytest.mark.parametrize("name", ["custom_cumulative_name", None])
def test_cumulative_viewshed_uses_explicit_output_name(raster, observers, name):
    result = cumulative_viewshed(raster, observers, name=name)

    assert isinstance(result, xr.DataArray)
    assert result.name == name


def test_visibility_frequency_has_default_output_name(raster, observers):
    result = visibility_frequency(raster, observers)

    assert isinstance(result, xr.DataArray)
    assert result.name == "visibility_frequency"


@pytest.mark.parametrize("name", ["custom_frequency_name", None])
def test_visibility_frequency_uses_explicit_output_name(raster, observers, name):
    result = visibility_frequency(raster, observers, name=name)

    assert isinstance(result, xr.DataArray)
    assert result.name == name


def test_line_of_sight_frequency_mhz_type_metadata_is_nullable():
    signature = inspect.signature(line_of_sight)

    assert "frequency_mhz" in signature.parameters
    parameter = signature.parameters["frequency_mhz"]
    assert parameter.default is None

    type_hints = get_type_hints(line_of_sight)
    assert is_optional_float_annotation(type_hints["frequency_mhz"])
