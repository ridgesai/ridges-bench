#!/bin/bash

cd /app/src

export CI=true
export MPLBACKEND=Agg
export NUMBA_CACHE_DIR=/tmp/numba-cache

mkdir -p "tests"
cp "/tests/test_open_geotiff_coregister_sparse_coverage.py" "tests/test_open_geotiff_coregister_sparse_coverage.py"

cat > "tests/conftest.py" <<'PY'
import os
import sys
import tempfile
from contextlib import contextmanager

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin


@contextmanager
def _disk_geotiff(
    *,
    crs="EPSG:3857",
    west=20.0,
    north=80.0,
    width=20,
    height=20,
    pixel_width=1.0,
    pixel_height=1.0,
):
    transform = from_origin(west, north, pixel_width, pixel_height)
    data = np.arange(width * height, dtype=np.float32).reshape(height, width)
    fd, path = tempfile.mkstemp(suffix=".tif")
    os.close(fd)
    try:
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype=data.dtype,
            crs=crs,
            transform=transform,
        ) as dataset:
            dataset.write(data, 1)
        yield path
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


@pytest.fixture(autouse=True)
def _use_disk_geotiff_helper():
    for module in list(sys.modules.values()):
        if str(getattr(module, "__file__", "")).endswith(
            "test_open_geotiff_coregister_sparse_coverage.py"
        ):
            module._memory_geotiff = _disk_geotiff
            if not getattr(module, "_caller_array_sets_attrs_crs", False):
                original_caller_array = module._caller_array

                def _caller_array_with_attrs_crs(*args, **kwargs):
                    result = original_caller_array(*args, **kwargs)
                    result.attrs["crs"] = kwargs.get("crs", "EPSG:3857")
                    return result

                module._caller_array = _caller_array_with_attrs_crs
                module._caller_array_sets_attrs_crs = True
            break
PY

/opt/venv/bin/python -m pytest -xvs "tests/test_open_geotiff_coregister_sparse_coverage.py"
test_status=$?

if [ $test_status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit "$test_status"
