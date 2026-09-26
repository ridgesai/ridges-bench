#!/bin/bash
set -euo pipefail
cd /app
mkdir -p regression_tests
cat > regression_tests/test_iterutils.py <<'PY'
"""Reference regression suite for boltons.iterutils."""
import random
from collections import namedtuple

import pytest

from boltons import iterutils
from boltons.iterutils import (
    PathAccessError,
    backoff,
    backoff_iter,
    bucketize,
    chunked,
    chunked_iter,
    default_enter,
    default_exit,
    first,
    flatten,
    flatten_iter,
    get_path,
    lstrip,
    lstrip_iter,
    one,
    pairwise,
    pairwise_iter,
    partition,
    redundant,
    remap,
    research,
    rstrip,
    rstrip_iter,
    same,
    split,
    split_iter,
    strip,
    strip_iter,
    unique,
    unique_iter,
    windowed,
    windowed_iter,
)


# ---------------------------------------------------------------- chunked


def test_chunked_basic():
    assert chunked(range(10), 3) == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
    assert chunked(range(9), 3) == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert chunked([1, 2], 5) == [[1, 2]]
    assert chunked([], 3) == []
    assert chunked(range(4), 1) == [[0], [1], [2], [3]]


def test_chunked_fill_and_count():
    assert chunked(range(10), 3, fill=None) == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, None, None]]
    assert chunked(range(10), 4, fill=0) == [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 0, 0]]
    assert chunked(range(9), 3, fill="x") == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    assert chunked(range(10), 3, count=2) == [[0, 1, 2], [3, 4, 5]]
    assert chunked(range(10), 3, count=0) == []
    assert chunked(range(4), 3, count=10) == [[0, 1, 2], [3]]


def test_chunked_strings_and_bytes():
    assert chunked("abcdefg", 3) == ["abc", "def", "g"]
    assert chunked("abcde", 2, fill="-") == ["ab", "cd", "e-"]
    assert chunked(b"abcde", 2) == [b"ab", b"cd", b"e"]


def test_chunked_iter_lazy_and_errors():
    gen = chunked_iter(iter(range(7)), 2)
    assert next(gen) == [0, 1]
    assert list(gen) == [[2, 3], [4, 5], [6]]
    with pytest.raises(ValueError):
        list(chunked_iter(range(3), 0))
    with pytest.raises(ValueError):
        list(chunked_iter(range(3), -2))
    with pytest.raises(TypeError):
        list(chunked_iter(5, 2))
    with pytest.raises(ValueError):
        list(chunked_iter(range(3), 2, fil=1))


# ---------------------------------------------------------------- windowed / pairwise


def test_windowed():
    assert windowed(range(5), 3) == [(0, 1, 2), (1, 2, 3), (2, 3, 4)]
    assert windowed(range(3), 3) == [(0, 1, 2)]
    assert windowed(range(2), 3) == []
    assert windowed([], 2) == []
    assert windowed(range(3), 1) == [(0,), (1,), (2,)]


def test_windowed_fill():
    assert windowed(range(4), 3, fill=None) == [(0, 1, 2), (1, 2, 3), (2, 3, None), (3, None, None)]
    assert windowed(range(2), 4, fill=0) == [(0, 1, 0, 0), (1, 0, 0, 0)]
    assert windowed([], 2, fill=0) == []


def test_windowed_iter_accepts_iterators():
    assert list(windowed_iter(iter("abcd"), 2)) == [("a", "b"), ("b", "c"), ("c", "d")]
    assert list(windowed_iter(iter("ab"), 3)) == []


def test_pairwise():
    assert pairwise(range(5)) == [(0, 1), (1, 2), (2, 3), (3, 4)]
    assert pairwise([1]) == []
    assert pairwise([]) == []
    assert pairwise(range(3), end=None) == [(0, 1), (1, 2), (2, None)]
    assert pairwise("ab", end="$") == [("a", "b"), ("b", "$")]
    assert list(pairwise_iter(iter([1, 2, 3]))) == [(1, 2), (2, 3)]
    assert list(pairwise_iter([7], end=0)) == [(7, 0)]


# ---------------------------------------------------------------- bucketize / partition


def test_bucketize_default_and_callable():
    assert bucketize(range(5)) == {False: [0], True: [1, 2, 3, 4]}
    assert bucketize(range(10), key=lambda x: x % 3) == {0: [0, 3, 6, 9], 1: [1, 4, 7], 2: [2, 5, 8]}
    assert bucketize([None, "hi", None]) == {False: [None, None], True: ["hi"]}
    assert bucketize([]) == {}


def test_bucketize_attribute_and_list_keys():
    Pt = namedtuple("Pt", "x y")
    pts = [Pt(1, 2), Pt(2, 2), Pt(1, 3)]
    assert bucketize(pts, key="x") == {1: [Pt(1, 2), Pt(1, 3)], 2: [Pt(2, 2)]}
    assert bucketize([1, 2], key="missing") == {1: [1], 2: [2]}
    assert bucketize([1, 2, 365, 4, 98], key=[0, 1, 2, 0, 2]) == {0: [1, 4], 1: [2], 2: [365, 98]}
    with pytest.raises(ValueError):
        bucketize([1, 2, 3], key=[0, 1])


def test_bucketize_options_and_errors():
    assert bucketize(range(5), value_transform=lambda x: x * x) == {False: [0], True: [1, 4, 9, 16]}
    assert bucketize(range(10), key=lambda x: x % 3, key_filter=lambda k: k % 2 == 0) == {0: [0, 3, 6, 9], 2: [2, 5, 8]}
    assert bucketize([5, 6], key=["a", "b"], value_transform=str) == {"a": ["5"], "b": ["6"]}
    with pytest.raises(TypeError):
        bucketize(5)
    with pytest.raises(TypeError):
        bucketize([1], key=3)
    with pytest.raises(TypeError):
        bucketize([1], value_transform=3)


def test_partition():
    assert partition(range(5)) == ([1, 2, 3, 4], [0])
    evens, odds = partition(range(7), lambda x: x % 2 == 0)
    assert evens == [0, 2, 4, 6] and odds == [1, 3, 5]
    assert partition([], bool) == ([], [])
    Obj = namedtuple("Obj", "flag")
    items = [Obj(True), Obj(False), Obj(1)]
    assert partition(items, key="flag") == ([Obj(True), Obj(1)], [Obj(False)])
    assert partition([object()], "nope")[0] == []


def test_partition_multiple_keys():
    pos, neg, zero = partition([1, -1, 0, 5, -3], lambda x: x > 0, lambda x: x < 0)
    assert (pos, neg, zero) == ([1, 5], [-1, -3], [0])
    first_match = partition([6, 2, 3, 7], lambda x: x % 2 == 0, lambda x: x % 3 == 0)
    assert first_match == ([6, 2], [3], [7])
    with pytest.raises(TypeError):
        partition([1], 5)
    with pytest.raises(TypeError):
        partition(5)


# ---------------------------------------------------------------- unique / redundant


def test_unique():
    assert unique([1, 2, 1, 3, 2, 4]) == [1, 2, 3, 4]
    assert unique("hello") == ["h", "e", "l", "o"]
    assert unique(["hi", "Hi", "HI", "yo"], key=str.lower) == ["hi", "yo"]
    assert unique(["a", "bb", "c", "dd"], key=len) == ["a", "bb"]
    assert unique([]) == []
    gen = unique_iter(iter([3, 3, 4]))
    assert next(gen) == 3
    assert list(gen) == [4]
    with pytest.raises(TypeError):
        unique(5)
    with pytest.raises(TypeError):
        unique([1], key=5)


def test_unique_attribute_key():
    Pt = namedtuple("Pt", "x")
    assert unique([Pt(1), Pt(1), Pt(2)], key="x") == [Pt(1), Pt(2)]
    assert unique([1, 1, 2], key="nope") == [1, 2]


def test_redundant():
    assert redundant([1, 2, 3, 4]) == []
    assert redundant([1, 2, 3, 2, 3, 3, 4]) == [2, 3]
    assert redundant([1, 2, 3, 2, 3, 3, 4], groups=True) == [[2, 2], [3, 3, 3]]
    assert redundant(["hi", "Hi", "HI", "hello"], key=str.lower) == ["Hi"]
    assert redundant(["hi", "Hi", "HI", "hello"], key=str.lower, groups=True) == [["hi", "Hi", "HI"]]
    assert redundant([3, 1, 3, 1]) == [3, 1]
    assert redundant([[1], [1]], key=tuple) == [[1]]
    with pytest.raises(TypeError):
        redundant([1], key=5)


def test_redundant_attribute_key():
    Pt = namedtuple("Pt", "x y")
    data = [Pt(1, 0), Pt(2, 0), Pt(1, 1)]
    assert redundant(data, key="x") == [Pt(1, 1)]
    assert redundant(data, key="x", groups=True) == [[Pt(1, 0), Pt(1, 1)]]


# ---------------------------------------------------------------- split / strip


def test_split_default_separator():
    assert split(["hi", "hello", None, None, "sup", None, "soap", None]) == [["hi", "hello"], ["sup"], ["soap"]]
    assert split([None, 1, None]) == [[1]]
    assert split([]) == []
    assert split([1, 2]) == [[1, 2]]


def test_split_explicit_separators():
    assert split(["hi", "hello", None, None, "sup", None], sep=[None]) == [["hi", "hello"], [], ["sup"], []]
    assert split([1, 0, 2, 0, 0, 3], 0) == [[1], [2], [], [3]]
    assert split([1, "a", 2, "b", 3], sep=["a", "b"]) == [[1], [2], [3]]
    assert split(["hi", "hello", None, "", "sup", False], lambda x: not x) == [["hi", "hello"], [], ["sup"], []]
    assert split([], 0) == [[]]
    assert split("a,b,c", ",") == [["a"], ["b"], ["c"]]


def test_split_maxsplit():
    assert split([1, 0, 2, 0, 3, 0, 4], 0, maxsplit=2) == [[1], [2], [3, 0, 4]]
    assert split([1, 0, 2, 0, 3], 0, maxsplit=0) == [[1, 0, 2, 0, 3]]
    assert split([1, 0, 2], 0, maxsplit=1) == [[1], [2]]
    assert split([1, 0, 2, 0], 0, maxsplit=5) == [[1], [2], []]
    assert split([None, 1, None, None, 2, None, 3], maxsplit=1) == [[1], [None, 2, None, 3]]
    with pytest.raises(TypeError):
        split(5)


def test_split_iter_is_lazy():
    gen = split_iter(iter([1, 0, 2]), 0)
    assert next(gen) == [1]
    assert list(gen) == [[2]]


def test_strip_family():
    assert lstrip(["a", "a", "b", "a"], "a") == ["b", "a"]
    assert rstrip(["a", "b", "a", "a"], "a") == ["a", "b"]
    assert strip(["a", "a", "b", "a", "c", "a"], "a") == ["b", "a", "c"]
    assert strip([None, 1, None]) == [1]
    assert lstrip([0, 0], 0) == []
    assert rstrip([0, 0], 0) == []
    assert strip([], 0) == []
    assert rstrip([1, 0, 0, 2, 0], 0) == [1, 0, 0, 2]
    assert lstrip([1, 2], 0) == [1, 2]
    assert list(lstrip_iter(iter([5, 5, 6]), 5)) == [6]
    assert list(rstrip_iter(iter([6, 5, 5]), 5)) == [6]
    assert list(strip_iter("xxaxbxx", "x")) == ["a", "x", "b"]


# ---------------------------------------------------------------- first / one / same / flatten


def test_first():
    assert first([0, False, None, [], (), 42]) == 42
    assert first([0, None]) is None
    assert first([0, None], default="d") == "d"
    assert first([]) is None
    assert first([1, 3, 4, 6], key=lambda x: x % 2 == 0) == 4
    assert first(["", "ab", "cd"], key=len) == "ab"
    assert first(iter([0, 7, 8])) == 7


def test_one():
    assert one((True, False, False)) is True
    assert one((True, False, True)) is None
    assert one((0, 0, "a", "")) == "a"
    assert one((0, False, None)) is None
    assert one((True, True), default=False) is False
    assert one([], default=42) == 42
    assert one((10, 20, 30, 42), key=lambda i: i > 40) == 42
    assert one((10, 20, 42, 50), key=lambda i: i > 40, default="many") == "many"


def test_same():
    assert same([]) is True
    assert same([1]) is True
    assert same(["a", "a", "a"]) is True
    assert same([1, 1, 2]) is False
    assert same([2, 1, 1]) is False
    assert same((1, 1), ref=1) is True
    assert same((1, 1), ref=2) is False
    assert same([], ref=5) is True
    assert same(iter([None, None])) is True


def test_flatten():
    assert flatten([[1, 2], [3, [4, [5]]]]) == [1, 2, 3, 4, 5]
    assert flatten([]) == []
    assert flatten(["ab", ["cd", [b"ef"]]]) == ["ab", "cd", b"ef"]
    assert flatten([(1, 2), {3}, range(4, 6), iter([6])]) == [1, 2, 3, 4, 5, 6]
    assert flatten([1, [], [[]], 2]) == [1, 2]
    assert list(flatten_iter([[1], 2])) == [1, 2]


# ---------------------------------------------------------------- backoff


def test_backoff_default_count():
    assert backoff(1, 10) == [1.0, 2.0, 4.0, 8.0, 10.0]
    assert backoff(1, 8) == [1.0, 2.0, 4.0, 8.0]
    assert backoff(0.25, 100.0, factor=10) == [0.25, 2.5, 25.0, 100.0]
    assert backoff(0, 4) == [0.0, 1.0, 2.0, 4.0]
    assert backoff(3, 3, factor=1) == [3.0]
    assert backoff(2, 2) == [2.0]


def test_backoff_explicit_count():
    assert backoff(1, 10, count=8) == [1.0, 2.0, 4.0, 8.0, 10.0, 10.0, 10.0, 10.0]
    assert backoff(1, 10, count=2) == [1.0, 2.0]
    assert backoff(1, 10, count=0) == []
    assert backoff(2, 5, count=3, factor=1) == [2.0, 2.0, 2.0]
    assert backoff(1, 100, count=4, factor=3) == [1.0, 3.0, 9.0, 27.0]


def test_backoff_repeat_and_iter():
    gen = backoff_iter(1, 4, count="repeat")
    assert [next(gen) for _ in range(6)] == [1.0, 2.0, 4.0, 4.0, 4.0, 4.0]
    with pytest.raises(ValueError):
        backoff(1, 4, count="repeat")


def test_backoff_validation():
    with pytest.raises(ValueError):
        backoff(-1, 10)
    with pytest.raises(ValueError):
        backoff(1, 10, factor=0.5)
    with pytest.raises(ValueError):
        backoff(0, 0)
    with pytest.raises(ValueError):
        backoff(5, 2)
    with pytest.raises(ValueError):
        backoff(1, 10, factor=1)
    with pytest.raises(ValueError):
        backoff(1, 10, count=-1)
    with pytest.raises(ValueError):
        backoff(1, 10, jitter=1.5)
    with pytest.raises(ValueError):
        backoff(1, 10, jitter=-1.1)
    assert len(backoff(1, 10, jitter=-1.0)) == 5
    assert backoff(1, 1, factor=1.0, count=None) == [1.0]


def test_backoff_jitter_bounds():
    random.seed(42)
    base = [1.0, 2.0, 4.0, 8.0, 10.0]
    for _ in range(50):
        vals = backoff(1, 10, jitter=True)
        assert len(vals) == 5
        assert all(0 <= v <= b for v, b in zip(vals, base))
    runs = [backoff(1, 10, jitter=0.5) for _ in range(50)]
    assert all(b / 2 <= v <= b for vals in runs for v, b in zip(vals, base))
    assert any(v != b for vals in runs for v, b in zip(vals, base))
    neg = [backoff(1, 10, jitter=-0.5) for _ in range(50)]
    assert all(b <= v <= b * 1.5 for vals in neg for v, b in zip(vals, base))
    assert any(v > b for vals in neg for v, b in zip(vals, base))


# ---------------------------------------------------------------- remap


def test_remap_identity_copies():
    data = {"a": [1, 2, {"b": (3, 4)}], "c": {5, 6}, "d": "str"}
    out = remap(data)
    assert out == data
    assert out is not data
    assert out["a"] is not data["a"]
    assert isinstance(out["a"][2]["b"], tuple)
    assert out["c"] == {5, 6}
    assert remap([]) == []
    assert remap(frozenset([1, 2])) == frozenset([1, 2])


def test_remap_visit_drop_and_transform():
    data = {"x": None, "y": [1, None, 2], "z": {"w": None, "v": 3}}
    assert remap(data, visit=lambda p, k, v: v is not None) == {"y": [1, 2], "z": {"v": 3}}
    doubled = remap([1, [2, (3,)]], visit=lambda p, k, v: (k, v * 2) if isinstance(v, int) else True)
    assert doubled == [2, [4, (6,)]]
    upper = remap({"a": {"b": 1}}, visit=lambda p, k, v: (k.upper(), v))
    assert upper == {"A": {"B": 1}}


def test_remap_visit_paths():
    seen = []

    def visit(path, key, value):
        seen.append((path, key))
        return True

    remap({"a": [10, {"b": 20}]}, visit=visit)
    assert sorted(seen, key=repr) == sorted(
        [(("a", 1), "b"), (("a",), 0), (("a",), 1), ((), "a")], key=repr
    )


def test_remap_reraise_visit():
    def visit(path, key, value):
        if value == 2:
            raise ValueError("no")
        return key, value

    with pytest.raises(ValueError):
        remap([1, 2, 3], visit=visit)
    assert remap([1, 2, 3], visit=visit, reraise_visit=False) == [1, 2, 3]


def test_remap_enter_and_exit():
    def enter(path, key, value):
        if isinstance(value, dict) and "skip" in value:
            return value, False
        return default_enter(path, key, value)

    data = {"keep": {"a": [1]}, "raw": {"skip": [None]}}
    out = remap(data, enter=enter)
    assert out["raw"] is data["raw"]
    assert out["keep"] is not data["keep"]

    def exit_sorted(path, key, old_parent, new_parent, new_items):
        ret = default_exit(path, key, old_parent, new_parent, new_items)
        if isinstance(ret, list):
            ret.sort()
        return ret

    assert remap({"a": [3, 1, 2], "b": [[9, 8]]}, exit=exit_sorted) == {"a": [1, 2, 3], "b": [[8, 9]]}


def test_remap_shared_and_cyclic_references():
    shared = [1, 2]
    data = {"a": shared, "b": shared}
    out = remap(data)
    assert out["a"] is out["b"]
    assert out["a"] is not shared
    pair = (1, 2)
    out = remap({"x": pair, "y": [pair]})
    assert out == {"x": (1, 2), "y": [(1, 2)]}
    assert out["x"] is out["y"][0]
    fz = frozenset([3])
    assert remap([fz, fz]) == [frozenset([3]), frozenset([3])]
    cyc = [1]
    cyc.append(cyc)
    res = remap(cyc)
    assert res[0] == 1
    assert res[1] is res


def test_remap_errors():
    with pytest.raises(TypeError):
        remap([], visit=5)
    with pytest.raises(TypeError):
        remap([], enter=5)
    with pytest.raises(TypeError):
        remap([], exit=5)
    with pytest.raises(TypeError):
        remap([], bogus=True)
    with pytest.raises(TypeError):
        remap([], enter=lambda p, k, v: None)
    with pytest.raises(TypeError):
        remap(5, visit=lambda p, k, v: True)


def test_remap_namedtuple_and_tuple_types():
    Pt = namedtuple("Pt", "x y")

    def enter(path, key, value):
        if isinstance(value, Pt):
            return [], enumerate(value)
        return default_enter(path, key, value)

    def exit_(path, key, old_parent, new_parent, new_items):
        if isinstance(old_parent, Pt):
            return Pt(*(v for _, v in new_items))
        return default_exit(path, key, old_parent, new_parent, new_items)

    out = remap([Pt(1, 2)], visit=lambda p, k, v: (k, v + 1) if isinstance(v, int) else True, enter=enter, exit=exit_)
    assert out == [Pt(2, 3)]
    assert type(out[0]) is Pt


# ---------------------------------------------------------------- get_path / research


def test_get_path():
    root = {"a": {"b": [10, {"c": "x"}]}, "l": [[1, 2], [3]]}
    assert get_path(root, ("a", "b", 1, "c")) == "x"
    assert get_path(root, ["l", 1, 0]) == 3
    assert get_path(root, "a.b.0") == 10
    assert get_path(root, ("l", "0", "1")) == 2
    assert get_path(root, ()) is root


def test_get_path_errors_and_default():
    root = {"a": [1, 2]}
    with pytest.raises(PathAccessError) as info:
        get_path(root, ("a", 5))
    assert info.value.seg == 5
    assert info.value.path == ("a", 5)
    assert isinstance(info.value, KeyError) and isinstance(info.value, IndexError)
    with pytest.raises(PathAccessError):
        get_path(root, ("b",))
    with pytest.raises(PathAccessError) as info:
        get_path(root, ("a", "x"))
    assert info.value.seg == "x"
    with pytest.raises(PathAccessError):
        get_path({"a": 5}, ("a", "b"))
    assert get_path(root, ("a", 5), default="d") == "d"
    assert get_path(root, "z.y", default=None) is None
    assert get_path(root, ("a", 0), default="d") == 1


def test_research():
    root = {"a": {"b": 1, "c": (2, "d", 3)}, "e": None}
    found = research(root, query=lambda p, k, v: isinstance(v, int))
    assert sorted(found, key=repr) == sorted(
        [(("a", "b"), 1), (("a", "c", 0), 2), (("a", "c", 2), 3)], key=repr
    )
    everything = research([1, [2]], query=lambda p, k, v: k is not None)
    assert sorted(everything, key=repr) == sorted([((0,), 1), ((1,), [2]), ((1, 0), 2)], key=repr)
    assert research([], query=lambda p, k, v: True) == [((None,), [])]
    with pytest.raises(TypeError):
        research(root, query=5)


def test_research_errors_in_query():
    def query(p, k, v):
        if v == 2:
            raise RuntimeError
        return isinstance(v, int)

    assert research([1, 2, 3], query=query) == [((0,), 1), ((2,), 3)]
    with pytest.raises(RuntimeError):
        research([1, 2, 3], query=query, reraise=True)


def test_research_visits_duplicates():
    shared = [7]
    found = research({"a": shared, "b": shared}, query=lambda p, k, v: v == 7)
    assert sorted(found) == [(("a", 0), 7), (("b", 0), 7)]


def test_module_level_names():
    assert iterutils.chunked is chunked
    assert iterutils.remap is remap
PY
# Stage the new files so the oracle control sees them in `git diff HEAD` (runs inside the task container).
git add -A regression_tests
