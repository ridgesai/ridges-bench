#!/bin/bash
set -euo pipefail
cd /app
mkdir -p regression_tests
cat > regression_tests/test_natsort.py <<'PY'
"""Reference regression suite for natsort's natural ordering API."""
import pytest

from natsort import (
    humansorted,
    index_natsorted,
    natsort_keygen,
    natsorted,
    ns,
    order_by_index,
    realsorted,
)

ITEMS = ["item10", "item9", "item1", "item2"]
MIXED_CASE = ["Banana", "apple", "banana", "Apple"]


def test_natsorted_numbers_inside_strings():
    assert natsorted(ITEMS) == ["item1", "item2", "item9", "item10"]


def test_natsorted_multiple_numbers():
    data = ["v1.10.2", "v1.9.10", "v1.9.9", "v1.10.10"]
    assert natsorted(data) == ["v1.9.9", "v1.9.10", "v1.10.2", "v1.10.10"]


def test_natsorted_does_not_modify_input():
    data = list(ITEMS)
    natsorted(data)
    assert data == ITEMS


def test_natsorted_reverse():
    assert natsorted(ITEMS, reverse=True) == ["item10", "item9", "item2", "item1"]


def test_natsorted_key():
    data = [("b", 2), ("a10", 1), ("a2", 3)]
    assert natsorted(data, key=lambda x: x[0]) == [("a2", 3), ("a10", 1), ("b", 2)]


def test_natsorted_plain_numbers_and_mixed_types():
    assert natsorted([10, 2, 33, 1]) == [1, 2, 10, 33]
    assert natsorted(["a1", "a", "1", "b"]) == ["1", "a", "a1", "b"]


def test_natsorted_is_stable_for_equal_keys():
    assert natsorted(["a01", "a1", "a001"]) == ["a01", "a1", "a001"]


def test_default_is_unsigned_int():
    assert natsorted(["a-5", "a+2", "a3", "a-1"]) == ["a3", "a+2", "a-1", "a-5"]
    assert natsorted(["1.5", "1.10", "1.2"]) == ["1.2", "1.5", "1.10"]


def test_float_flag():
    assert natsorted(["1.5", "1.10", "1.2"], alg=ns.FLOAT) == ["1.10", "1.2", "1.5"]
    assert natsorted(["a5.6E5", "a1e3", "a7"], alg=ns.FLOAT) == ["a7", "a1e3", "a5.6E5"]


def test_noexp_flag():
    assert natsorted(["a5.6E5", "a1e3", "a7"], alg=ns.FLOAT | ns.NOEXP) == ["a1e3", "a5.6E5", "a7"]


def test_signed_flag():
    assert natsorted(["a-5", "a+2", "a3", "a-1"], alg=ns.SIGNED) == ["a-5", "a-1", "a+2", "a3"]


def test_realsorted():
    assert realsorted(["a-5", "a+2", "a3", "a-1"]) == ["a-5", "a-1", "a+2", "a3"]
    assert realsorted(["-1.5", "2", "-3", "0.5"]) == ["-3", "-1.5", "0.5", "2"]
    assert realsorted(["b2", "b-1.5", "b0.25"], reverse=True) == ["b2", "b0.25", "b-1.5"]


def test_case_flags():
    assert natsorted(MIXED_CASE) == ["Apple", "Banana", "apple", "banana"]
    assert natsorted(MIXED_CASE, alg=ns.IGNORECASE) == ["apple", "Apple", "Banana", "banana"]
    assert natsorted(MIXED_CASE, alg=ns.LOWERCASEFIRST) == ["apple", "banana", "Apple", "Banana"]
    assert natsorted(MIXED_CASE, alg=ns.GROUPLETTERS) == ["Apple", "apple", "Banana", "banana"]


def test_path_flag():
    data = ["Folder (10)/", "Folder/", "Folder (1)/"]
    assert natsorted(data) == ["Folder (1)/", "Folder (10)/", "Folder/"]
    assert natsorted(data, alg=ns.PATH) == ["Folder/", "Folder (1)/", "Folder (10)/"]
    files = ["dir/file10.txt", "dir/file2.txt", "dir/file1.txt"]
    assert natsorted(files, alg=ns.PATH) == ["dir/file1.txt", "dir/file2.txt", "dir/file10.txt"]


def test_path_flag_with_extensions():
    data = ["data10.json", "data.json", "data2.json", "data.csv"]
    assert natsorted(data) == ["data2.json", "data10.json", "data.csv", "data.json"]
    assert natsorted(data, alg=ns.PATH) == ["data.csv", "data.json", "data2.json", "data10.json"]
    pages = ["report2.html", "report.html", "report10.html"]
    assert natsorted(pages, alg=ns.PATH) == ["report.html", "report2.html", "report10.html"]


def test_float_nan_strings():
    assert natsorted(["5", "nan", "1"], alg=ns.FLOAT) == ["nan", "1", "5"]
    assert natsorted(["5", "nan", "1"], alg=ns.FLOAT | ns.NANLAST) == ["1", "5", "nan"]


def test_numafter_flag():
    assert natsorted(["a1", "a", "1", "b"], alg=ns.NUMAFTER) == ["a", "a1", "b", "1"]


def test_nan_handling():
    nan = float("nan")
    result = natsorted([nan, 5, 1])
    assert result[1:] == [1, 5] and result[0] != result[0]
    result = natsorted([nan, 5, 1], alg=ns.NANLAST)
    assert result[:2] == [1, 5] and result[2] != result[2]


def test_compatibility_normalize_flag():
    assert natsorted(["⑦", "5", "10"], alg=ns.CN) == ["5", "⑦", "10"]


def test_presort_flag():
    assert natsorted(["a2", "a02", "a002"]) == ["a2", "a02", "a002"]
    assert natsorted(["a2", "a02", "a002"], alg=ns.PRESORT) == ["a002", "a02", "a2"]


def test_humansorted():
    assert humansorted(["a10", "a9", "a1"]) == ["a1", "a9", "a10"]
    assert humansorted(MIXED_CASE) == ["apple", "Apple", "banana", "Banana"]


def test_natsort_keygen():
    key = natsort_keygen()
    assert sorted(ITEMS, key=key) == ["item1", "item2", "item9", "item10"]
    assert key("a10b2") < key("a10b10") < key("a11")
    assert key("x9") < key("x10")
    assert key("10") < key("a")


def test_natsort_keygen_with_options():
    key = natsort_keygen(alg=ns.REAL)
    assert sorted(["x-2.5", "x1", "x-10"], key=key) == ["x-10", "x-2.5", "x1"]
    key = natsort_keygen(key=lambda s: s.upper(), alg=ns.IGNORECASE)
    assert sorted(["b2", "A10", "a2"], key=key) == ["a2", "A10", "b2"]


def test_index_natsorted():
    assert index_natsorted(ITEMS) == [2, 3, 1, 0]
    assert index_natsorted(ITEMS, reverse=True) == [0, 1, 3, 2]
    assert order_by_index(ITEMS, index_natsorted(ITEMS)) == ["item1", "item2", "item9", "item10"]


def test_index_natsorted_with_key_and_alg():
    data = [("x", "-2"), ("y", "3"), ("z", "-10")]
    assert index_natsorted(data, key=lambda t: t[1], alg=ns.SIGNED) == [2, 0, 1]


def test_ns_aliases():
    assert ns.REAL == ns.FLOAT | ns.SIGNED
    assert ns.I == ns.INT and ns.F == ns.FLOAT and ns.IC == ns.IGNORECASE
    assert ns.LOCALE == ns.LOCALEALPHA | ns.LOCALENUM


@pytest.mark.parametrize(
    "data, expected",
    [
        (["x2-y08", "x2-g8", "x8-y8", "x2-y7"], ["x2-g8", "x2-y7", "x2-y08", "x8-y8"]),
        (["1.2.10", "1.2.9", "1.10.1"], ["1.2.9", "1.2.10", "1.10.1"]),
    ],
)
def test_natsorted_examples(data, expected):
    assert natsorted(data) == expected
PY
# The oracle harness diffs against HEAD, so stage the new files.
git add -A regression_tests
