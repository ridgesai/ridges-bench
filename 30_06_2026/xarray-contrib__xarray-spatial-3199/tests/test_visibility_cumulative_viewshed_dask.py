import numpy as np
import pytest
import xarray as xr

import dask
import dask.array as da

from xrspatial.visibility import cumulative_viewshed


pytest.importorskip("dask")


def make_data_array(data):
    return xr.DataArray(
        data,
        dims=("y", "x"),
        coords={
            "y": np.arange(data.shape[0], dtype=np.float64),
            "x": np.arange(data.shape[1], dtype=np.float64),
        },
    )


def computed_values(data_array):
    return data_array.compute().values


def record_source_array(tracker, values):
    tracker["source_evaluations"] += 1
    return values


def make_counted_dask_raster(values, tracker):
    delayed_values = dask.delayed(record_source_array, pure=False)(tracker, values)
    data = da.from_delayed(delayed_values, shape=values.shape, dtype=values.dtype)
    return make_data_array(data)


def record_source_block(tracker, block_id, values, fail_if_computed):
    tracker["computed_blocks"].append(block_id)
    if fail_if_computed:
        raise AssertionError("block outside all max_distance windows was computed")
    return values


def make_window_sensitive_dask_raster(values, poison_block, chunk_size=2):
    tracker = {"computed_blocks": []}
    rows = []
    for y0 in range(0, values.shape[0], chunk_size):
        row = []
        for x0 in range(0, values.shape[1], chunk_size):
            block_id = (y0 // chunk_size, x0 // chunk_size)
            block_values = values[y0 : y0 + chunk_size, x0 : x0 + chunk_size]
            delayed_block = dask.delayed(record_source_block, pure=False)(
                tracker,
                block_id,
                block_values,
                block_id == poison_block,
            )
            row.append(
                da.from_delayed(
                    delayed_block,
                    shape=block_values.shape,
                    dtype=values.dtype,
                )
            )
        rows.append(row)
    return make_data_array(da.block(rows)), tracker


def test_cumulative_viewshed_no_max_distance_materializes_dask_source_once_and_keeps_dask_output():
    values = np.array(
        [
            [0.0, 0.0, 1.0, 0.0, 0.0],
            [0.0, 1.0, 2.0, 1.0, 0.0],
            [1.0, 2.0, 3.0, 2.0, 1.0],
            [0.0, 1.0, 2.0, 1.0, 0.0],
            [0.0, 0.0, 1.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    )
    observers = [
        {"x": 1.0, "y": 1.0, "observer_elev": 1.0},
        {"x": 3.0, "y": 1.0, "observer_elev": 1.0},
        {"x": 2.0, "y": 3.0, "observer_elev": 1.0},
    ]
    tracker = {"source_evaluations": 0}

    expected = cumulative_viewshed(
        make_data_array(values),
        observers=[dict(observer) for observer in observers],
        target_elev=0.0,
    )

    with dask.config.set(scheduler="single-threaded"):
        result = cumulative_viewshed(
            make_counted_dask_raster(values, tracker),
            observers=[dict(observer) for observer in observers],
            target_elev=0.0,
        )

    assert tracker["source_evaluations"] == 1
    assert isinstance(result.data, da.Array)

    with dask.config.set(scheduler="single-threaded"):
        actual_values = computed_values(result)

    assert tracker["source_evaluations"] == 1
    np.testing.assert_array_equal(actual_values, computed_values(expected))


@pytest.mark.parametrize(
    ("observers", "kwargs"),
    [
        (
            [
                {"x": 1.0, "y": 1.0, "observer_elev": 1.0},
                {"x": 2.0, "y": 1.0, "observer_elev": 1.0},
            ],
            {"max_distance": 1.5},
        ),
        (
            [
                {
                    "x": 1.0,
                    "y": 1.0,
                    "observer_elev": 1.0,
                    "max_distance": 1.5,
                },
                {
                    "x": 2.0,
                    "y": 1.0,
                    "observer_elev": 1.0,
                    "max_distance": 1.5,
                },
            ],
            {},
        ),
    ],
)
def test_cumulative_viewshed_with_max_distance_keeps_windowed_dask_behavior_and_matches_numpy(
    observers,
    kwargs,
):
    values = np.array(
        [
            [0.0, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
            [0.0, 0.2, 0.7, 1.1, 1.6, 2.1, 2.6, 3.1],
            [0.1, 0.3, 0.8, 1.2, 1.7, 2.2, 2.7, 3.2],
            [0.1, 0.4, 0.9, 1.3, 1.8, 2.3, 2.8, 3.3],
            [0.2, 0.5, 1.0, 1.4, 1.9, 2.4, 2.9, 3.4],
            [0.2, 0.6, 1.1, 1.5, 2.0, 2.5, 3.0, 3.5],
            [0.3, 0.7, 1.2, 1.6, 2.1, 2.6, 3.1, 3.6],
            [0.3, 0.8, 1.3, 1.7, 2.2, 2.7, 3.2, 3.7],
        ],
        dtype=np.float64,
    )
    poison_block = (3, 3)
    dask_raster, tracker = make_window_sensitive_dask_raster(values, poison_block)

    expected = cumulative_viewshed(
        make_data_array(values),
        observers=[dict(observer) for observer in observers],
        target_elev=0.0,
        **kwargs,
    )

    with dask.config.set(scheduler="single-threaded"):
        result = cumulative_viewshed(
            dask_raster,
            observers=[dict(observer) for observer in observers],
            target_elev=0.0,
            **kwargs,
        )
        actual_values = computed_values(result)

    assert poison_block not in tracker["computed_blocks"]
    np.testing.assert_array_equal(actual_values, computed_values(expected))
