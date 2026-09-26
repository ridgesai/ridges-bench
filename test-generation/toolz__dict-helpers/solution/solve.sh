#!/bin/bash
set -euo pipefail
cd /app
mkdir -p regression_tests
cat > regression_tests/test_dict_helpers.py <<'PY'
"""Reference regression suite for toolz's dictionary helpers (toolz.dicttoolz)."""
from collections import OrderedDict, defaultdict

import pytest

import toolz
from toolz import (
    assoc, assoc_in, dissoc, get_in, itemfilter, itemmap, keyfilter, keymap, merge,
    merge_with, update_in, valfilter, valmap,
)


def iseven(x):
    return x % 2 == 0


# ---- merge / merge_with -----------------------------------------------------

def test_merge():
    assert merge({1: "one"}, {2: "two"}) == {1: "one", 2: "two"}
    assert merge({1: 2, 3: 4}, {3: 3, 4: 4}) == {1: 2, 3: 3, 4: 4}
    assert merge() == {}
    assert merge({}) == {}
    assert merge({1: 1}) == {1: 1}


def test_merge_accepts_a_collection_of_dicts():
    assert merge([{1: 1}, {1: 2, 2: 2}]) == {1: 2, 2: 2}
    assert merge(iter([{1: 1}, {2: 2}])) == {1: 1, 2: 2}
    assert merge(({"a": i} for i in range(3))) == {"a": 2}


def test_merge_does_not_mutate_inputs():
    a, b = {1: 1}, {2: 2}
    out = merge(a, b)
    assert a == {1: 1} and b == {2: 2}
    assert out is not a
    single = {1: 1}
    assert merge(single) is not single


def test_merge_factory():
    out = merge({1: 1}, {2: 2}, factory=OrderedDict)
    assert isinstance(out, OrderedDict)
    assert out == {1: 1, 2: 2}


def test_merge_rejects_unknown_keyword():
    with pytest.raises(Exception):
        merge({1: 1}, fatcory=dict)


def test_merge_with():
    assert merge_with(sum, {1: 1, 2: 2}, {1: 10, 2: 20}) == {1: 11, 2: 22}
    assert merge_with(list, {1: 1, 2: 2}, {2: 20, 3: 30}) == {1: [1], 2: [2, 20], 3: [30]}
    assert merge_with(max, [{"a": 1}, {"a": 5}, {"a": 3}]) == {"a": 5}
    assert merge_with(sum) == {}
    assert merge_with(tuple, {"k": 1}) == {"k": (1,)}


def test_merge_with_passes_values_in_order():
    assert merge_with(lambda vs: vs[0], {1: "a"}, {1: "b"}, {1: "c"}) == {1: "a"}
    assert merge_with(lambda vs: vs, [{1: "a"}, {2: "x"}, {1: "b"}]) == {1: ["a", "b"], 2: ["x"]}


def test_merge_with_factory():
    out = merge_with(sum, {1: 1}, {1: 2}, factory=lambda: defaultdict(int))
    assert isinstance(out, defaultdict)
    assert out == {1: 3}


def test_merge_with_rejects_unknown_keyword():
    with pytest.raises(Exception):
        merge_with(sum, {1: 1}, fatcory=dict)


# ---- maps and filters ----------------------------------------------------------

def test_valmap():
    assert valmap(sum, {"Alice": [20, 15, 30], "Bob": [10, 35]}) == {"Alice": 65, "Bob": 45}
    assert valmap(str.upper, {1: "a"}) == {1: "A"}
    assert valmap(len, {}) == {}
    out = valmap(len, {1: "ab"}, factory=OrderedDict)
    assert isinstance(out, OrderedDict) and out == {1: 2}


def test_keymap():
    assert keymap(str.lower, {"Alice": [20, 15, 30], "Bob": [10, 35]}) == {
        "alice": [20, 15, 30], "bob": [10, 35]}
    assert keymap(lambda k: 0, {1: "a", 2: "b"}) == {0: "b"}
    assert keymap(str, {}) == {}
    out = keymap(str, {1: 1}, factory=OrderedDict)
    assert isinstance(out, OrderedDict) and out == {"1": 1}


def test_itemmap():
    accountids = {"Alice": 10, "Bob": 20}
    assert itemmap(reversed, accountids) == {10: "Alice", 20: "Bob"}
    assert itemmap(lambda kv: (kv[0], kv[1] * 2), {"a": 1}) == {"a": 2}
    assert itemmap(reversed, {}) == {}
    out = itemmap(reversed, {1: 2}, factory=OrderedDict)
    assert isinstance(out, OrderedDict) and out == {2: 1}


def test_valfilter():
    assert valfilter(iseven, {1: 2, 2: 3, 3: 4, 4: 5}) == {1: 2, 3: 4}
    assert valfilter(lambda v: False, {1: 1}) == {}
    out = valfilter(iseven, {1: 2}, factory=OrderedDict)
    assert isinstance(out, OrderedDict) and out == {1: 2}


def test_keyfilter():
    assert keyfilter(iseven, {1: 2, 2: 3, 3: 4, 4: 5}) == {2: 3, 4: 5}
    assert keyfilter(lambda k: False, {1: 1}) == {}
    out = keyfilter(iseven, {2: 2}, factory=OrderedDict)
    assert isinstance(out, OrderedDict) and out == {2: 2}


def test_itemfilter():
    def isvalid(item):
        k, v = item
        return k % 2 == 0 and v < 4

    assert itemfilter(isvalid, {1: 2, 2: 3, 3: 4, 4: 5}) == {2: 3}
    assert itemfilter(lambda item: True, {}) == {}
    out = itemfilter(isvalid, {2: 1}, factory=OrderedDict)
    assert isinstance(out, OrderedDict) and out == {2: 1}


def test_maps_and_filters_do_not_mutate_input():
    d = {1: 1, 2: 2}
    for f in (valmap, keymap):
        f(lambda x: x * 10, d)
    itemmap(reversed, d)
    valfilter(iseven, d)
    keyfilter(iseven, d)
    itemfilter(lambda kv: False, d)
    assert d == {1: 1, 2: 2}


# ---- assoc / dissoc / assoc_in -----------------------------------------------

def test_assoc():
    d = {"x": 1}
    assert assoc(d, "x", 2) == {"x": 2}
    assert assoc(d, "y", 3) == {"x": 1, "y": 3}
    assert d == {"x": 1}
    out = assoc({}, 1, 2, factory=OrderedDict)
    assert isinstance(out, OrderedDict) and out == {1: 2}


def test_dissoc():
    d = {"x": 1, "y": 2, "z": 3}
    assert dissoc(d, "y") == {"x": 1, "z": 3}
    assert dissoc(d, "x", "y") == {"z": 3}
    assert dissoc(d, "x", "y", "z") == {}
    assert dissoc({"x": 1}, "y") == {"x": 1}
    assert dissoc({"x": 1, "y": 2}, "q", "r", "y") == {"x": 1}
    assert dissoc(d) == d
    assert d == {"x": 1, "y": 2, "z": 3}


def test_dissoc_many_keys():
    d = {i: str(i) for i in range(10)}
    assert dissoc(d, *range(8)) == {8: "8", 9: "9"}
    assert dissoc(d, *range(3)) == {i: str(i) for i in range(3, 10)}
    assert dissoc(d, *range(20)) == {}
    assert len(d) == 10


def test_dissoc_factory():
    out = dissoc({"x": 1, "y": 2}, "y", factory=OrderedDict)
    assert isinstance(out, OrderedDict) and out == {"x": 1}
    out = dissoc({"x": 1, "y": 2, "z": 3}, "x", "y", factory=OrderedDict)
    assert isinstance(out, OrderedDict) and out == {"z": 3}


def test_assoc_in():
    assert assoc_in({"a": 1}, ["a"], 2) == {"a": 2}
    assert assoc_in({"a": {"b": 1}}, ["a", "b"], 2) == {"a": {"b": 2}}
    assert assoc_in({}, ["a", "b"], 1) == {"a": {"b": 1}}
    purchase = {"name": "Alice", "order": {"items": ["Apple", "Orange"], "costs": [0.50, 1.25]}}
    out = assoc_in(purchase, ["order", "costs"], [0.25, 1.00])
    assert out == {"name": "Alice", "order": {"items": ["Apple", "Orange"], "costs": [0.25, 1.00]}}
    assert purchase["order"]["costs"] == [0.50, 1.25]


def test_assoc_in_factory():
    out = assoc_in({}, ["a", "b"], 1, factory=OrderedDict)
    assert isinstance(out, OrderedDict) and isinstance(out["a"], OrderedDict)
    assert out == {"a": {"b": 1}}


# ---- get_in / update_in -------------------------------------------------------

TRANSACTION = {"name": "Alice", "purchase": {"items": ["Apple", "Orange"], "costs": [0.50, 1.25]},
               "credit card": "5555-1234-1234-1234"}


def test_get_in():
    assert get_in(["purchase", "items", 0], TRANSACTION) == "Apple"
    assert get_in(["name"], TRANSACTION) == "Alice"
    assert get_in(("purchase", "costs", 1), TRANSACTION) == 1.25
    assert get_in([], TRANSACTION) is TRANSACTION


def test_get_in_missing_returns_default():
    assert get_in(["purchase", "total"], TRANSACTION) is None
    assert get_in(["purchase", "items", "apple"], TRANSACTION) is None
    assert get_in(["purchase", "items", 10], TRANSACTION) is None
    assert get_in(["purchase", "total"], TRANSACTION, 0) == 0
    assert get_in(["nope", "deeper"], TRANSACTION, default="d") == "d"
    assert get_in(["name", 0, 1], TRANSACTION, "x") == "x"


def test_get_in_no_default():
    with pytest.raises(KeyError):
        get_in(["y"], {"x": 1}, no_default=True)
    with pytest.raises(IndexError):
        get_in([5], [1, 2], no_default=True)
    assert get_in(["x"], {"x": 1}, no_default=True) == 1
    assert get_in(["x"], {"x": None}, no_default=True) is None


def test_update_in():
    inc = lambda x: x + 1
    assert update_in({"a": 0}, ["a"], inc) == {"a": 1}
    out = update_in(TRANSACTION, ["purchase", "costs"], sum)
    assert out == {"name": "Alice", "purchase": {"items": ["Apple", "Orange"], "costs": 1.75},
                   "credit card": "5555-1234-1234-1234"}
    assert TRANSACTION["purchase"]["costs"] == [0.50, 1.25]


def test_update_in_missing_keys_use_default():
    assert update_in({}, [1, 2, 3], str, default="bar") == {1: {2: {3: "bar"}}}
    assert update_in({1: "foo"}, [2, 3, 4], lambda x: x + 1, default=0) == {1: "foo", 2: {3: {4: 1}}}
    assert update_in({"a": {}}, ["a", "b"], lambda x: x) == {"a": {"b": None}}
    assert update_in({"a": {"x": 1}}, ["a", "b"], lambda x: x, default=5) == {"a": {"x": 1, "b": 5}}


def test_update_in_does_not_mutate_nested_input():
    d = {"a": {"b": {"c": 1}}}
    out = update_in(d, ["a", "b", "c"], lambda x: x + 1)
    assert out == {"a": {"b": {"c": 2}}}
    assert d == {"a": {"b": {"c": 1}}}
    assert out["a"] is not d["a"]


def test_update_in_factory():
    out = update_in({"a": {"b": 1}}, ["a", "b"], lambda x: x * 10, factory=OrderedDict)
    assert isinstance(out, OrderedDict) and isinstance(out["a"], OrderedDict)
    assert out == {"a": {"b": 10}}


def test_top_level_names_are_the_dicttoolz_functions():
    from toolz import dicttoolz
    for name in dicttoolz.__all__:
        assert getattr(toolz, name) is getattr(dicttoolz, name)
PY
# Stage the new files so the oracle control sees them in git diff HEAD (runs inside the task container).
git add -A regression_tests
