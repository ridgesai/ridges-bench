"""Behavior contracts for rows_from_file error translation."""

import io
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(os.environ["REPO_ROOT"])
sys.path.insert(0, str(REPO_ROOT))

from sqlite_utils.utils import Format, rows_from_file


def test_text_stream_usage_error_suppresses_internal_attribute_context():
    with pytest.raises(TypeError) as excinfo:
        rows_from_file(io.StringIO("name\nCleo\n"))

    error = excinfo.value
    assert str(error) == (
        "rows_from_file() requires a file-like object that supports peek(), "
        "such as io.BytesIO"
    )
    assert error.__cause__ is None
    assert error.__suppress_context__ is True


@pytest.mark.parametrize(
    ("payload", "expected_format", "expected_rows"),
    [
        (b"name,age\nCleo,7\n", Format.CSV, [{"name": "Cleo", "age": "7"}]),
        (b"name\tage\nCleo\t7\n", Format.TSV, [{"name": "Cleo", "age": "7"}]),
        (b'[{"name": "Cleo", "age": 7}]', Format.JSON, [{"name": "Cleo", "age": 7}]),
    ],
)
def test_automatic_detection_and_rows_are_preserved(payload, expected_format, expected_rows):
    rows, detected = rows_from_file(io.BytesIO(payload))
    assert detected == expected_format
    assert list(rows) == expected_rows


def test_explicit_csv_extra_field_strategies_are_preserved():
    payload = b"name\nCleo,extra\n"
    with pytest.raises(Exception):
        rows, _ = rows_from_file(io.BytesIO(payload), format=Format.CSV)
        list(rows)

    rows, _ = rows_from_file(
        io.BytesIO(payload), format=Format.CSV, extras_key="rest"
    )
    assert list(rows) == [{"name": "Cleo", "rest": ["extra"]}]

