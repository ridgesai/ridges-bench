#!/bin/bash
set -euo pipefail
cd /app
mkdir -p regression_tests
cat > regression_tests/test_query_language.py <<'PY'
"""Reference regression suite for jmespath's query language."""
import collections

import pytest

import jmespath
from jmespath import exceptions, functions


PEOPLE = {
    "people": [
        {"name": "ann", "age": 31, "tags": ["a", "b"], "score": 2.5},
        {"name": "bob", "age": 17, "tags": ["c"], "score": 9.25},
        {"name": "cy", "age": 45, "tags": [], "score": 0.5},
        {"name": "dee", "age": 31},
    ]
}


# --- identifiers, sub-expressions, index and slice -------------------------


def test_identifiers_and_subexpressions():
    data = {"a": {"b": {"c": 1}}, "with space": 2, "x-y": 3}
    assert jmespath.search("a", data) == {"b": {"c": 1}}
    assert jmespath.search("a.b.c", data) == 1
    assert jmespath.search("a.b.missing", data) is None
    assert jmespath.search("a.b.c.d", data) is None
    assert jmespath.search('"with space"', data) == 2
    assert jmespath.search('"x-y"', data) == 3
    assert jmespath.search("missing.b", data) is None
    assert jmespath.search("a", [1, 2]) is None
    assert jmespath.search("a", "text") is None


def test_index_expressions():
    data = {"a": [10, 20, 30, 40]}
    assert jmespath.search("a[0]", data) == 10
    assert jmespath.search("a[3]", data) == 40
    assert jmespath.search("a[-1]", data) == 40
    assert jmespath.search("a[-4]", data) == 10
    assert jmespath.search("a[4]", data) is None
    assert jmespath.search("a[-5]", data) is None
    assert jmespath.search("[1]", [5, 6]) == 6
    assert jmespath.search("[0]", {"a": 1}) is None
    assert jmespath.search("a[0][1]", {"a": [[1, 2], [3]]}) == 2
    assert jmespath.search("[0]", "abc") is None


@pytest.mark.parametrize(
    "expr, expected",
    [
        ("[0:2]", [0, 1]),
        ("[1:]", [1, 2, 3, 4, 5]),
        ("[:3]", [0, 1, 2]),
        ("[::2]", [0, 2, 4]),
        ("[1::2]", [1, 3, 5]),
        ("[::-1]", [5, 4, 3, 2, 1, 0]),
        ("[-2:]", [4, 5]),
        ("[:-2]", [0, 1, 2, 3]),
        ("[4:1:-1]", [4, 3, 2]),
        ("[10:]", []),
        ("[:]", [0, 1, 2, 3, 4, 5]),
        ("[0:6:3]", [0, 3]),
    ],
)
def test_slices(expr, expected):
    assert jmespath.search(expr, [0, 1, 2, 3, 4, 5]) == expected


def test_slice_errors_and_non_lists():
    assert jmespath.search("a[0:1]", {"a": "abc"}) is None
    assert jmespath.search("a[0:1]", {"a": {"b": 1}}) is None
    with pytest.raises(Exception):
        jmespath.search("[::0]", [1, 2])
    with pytest.raises(exceptions.ParseError):
        jmespath.compile("[1:2:3:4]")


def test_slice_is_a_projection():
    data = {"a": [{"b": 1}, {"b": 2}, {"c": 3}, {"b": 4}]}
    assert jmespath.search("a[1:].b", data) == [2, 4]
    assert jmespath.search("a[:2].b", data) == [1, 2]


# --- projections ------------------------------------------------------------


def test_list_projection():
    data = {"a": [{"b": 1}, {"b": 2}, {"c": 3}, {"b": [4, 5]}]}
    assert jmespath.search("a[*].b", data) == [1, 2, [4, 5]]
    assert jmespath.search("a[*]", data) == data["a"]
    assert jmespath.search("a[*].b[0]", data) == [4]
    assert jmespath.search("[*].x", [{"x": 1}, {"x": 2}]) == [1, 2]
    assert jmespath.search("a[*].b", {"a": {"b": 1}}) is None
    assert jmespath.search("people[*].name", PEOPLE) == ["ann", "bob", "cy", "dee"]


def test_object_projection():
    data = {"ops": {"x": {"n": 1}, "y": {"n": 2}, "z": {"m": 3}}}
    assert sorted(jmespath.search("ops.*.n", data)) == [1, 2]
    assert jmespath.search("ops.*", {"ops": {"x": 1}}) == [1]
    assert jmespath.search("*", {"k": "v"}) == ["v"]
    assert jmespath.search("ops.*.n", {"ops": [1, 2]}) is None
    assert jmespath.search("*.a", {"x": {"a": 1}, "y": {"b": 2}}) == [1]


def test_flatten_projection():
    data = {"a": [[1, 2], 3, [4, [5]]]}
    assert jmespath.search("a[]", data) == [1, 2, 3, 4, [5]]
    assert jmespath.search("a[][]", data) == [1, 2, 3, 4, 5]
    assert jmespath.search("[]", [[1], [2, 3]]) == [1, 2, 3]
    assert jmespath.search("a[]", {"a": {"b": 1}}) is None
    assert jmespath.search("people[].tags[]", PEOPLE) == ["a", "b", "c"]
    nested = {"r": [{"i": [{"s": 1}, {"s": 2}]}, {"i": [{"s": 3}]}]}
    assert jmespath.search("r[].i[].s", nested) == [1, 2, 3]
    assert jmespath.search("r[*].i[*].s", nested) == [[1, 2], [3]]


def test_projection_stops_at_pipe():
    data = {"a": [{"b": [1, 2]}, {"b": [3]}]}
    assert jmespath.search("a[*].b[0]", data) == [1, 3]
    assert jmespath.search("a[*].b | [0]", data) == [1, 2]
    assert jmespath.search("a[*].b | [1]", data) == [3]


def test_filter_projection():
    ppl = PEOPLE
    assert jmespath.search("people[?age > `30`].name", ppl) == ["ann", "cy", "dee"]
    assert jmespath.search("people[?age >= `31`].name", ppl) == ["ann", "cy", "dee"]
    assert jmespath.search("people[?age < `31`].name", ppl) == ["bob"]
    assert jmespath.search("people[?age <= `31`].name", ppl) == ["ann", "bob", "dee"]
    assert jmespath.search("people[?age == `31`].name", ppl) == ["ann", "dee"]
    assert jmespath.search("people[?age != `31`].name", ppl) == ["bob", "cy"]
    assert jmespath.search("people[?tags].name", ppl) == ["ann", "bob"]
    assert jmespath.search("people[?score].name", ppl) == ["ann", "bob", "cy"]
    assert jmespath.search("people[?name == 'bob'] | [0].age", ppl) == 17
    assert jmespath.search("[?@ > `2`]", [1, 2, 3, 4]) == [3, 4]
    assert jmespath.search("a[?b]", {"a": {"b": 1}}) is None


def test_filter_then_flatten():
    data = {"a": [{"v": [1, 2], "ok": True}, {"v": [3], "ok": False}, {"v": [4], "ok": True}]}
    assert jmespath.search("a[?ok].v[]", data) == [1, 2, 4]
    assert jmespath.search("a[?ok][]", data) == [data["a"][0], data["a"][2]]


def test_filter_with_string_ordering():
    data = [{"n": "apple"}, {"n": "pear"}, {"n": "fig"}]
    assert jmespath.search("[?n < 'g'].n", data) == ["apple", "fig"]
    assert jmespath.search("[?n > 'g'].n", data) == ["pear"]


# --- multiselect ------------------------------------------------------------


def test_multiselect_list():
    data = {"a": 1, "b": {"c": 2}, "d": [3, 4]}
    assert jmespath.search("[a, b.c, d[1]]", data) == [1, 2, 4]
    assert jmespath.search("[a, missing]", data) == [1, None]
    assert jmespath.search("[a]", None) is None
    assert jmespath.search("people[*].[name, age]", PEOPLE) == [
        ["ann", 31], ["bob", 17], ["cy", 45], ["dee", 31]
    ]
    assert jmespath.search("b.[c, c]", data) == [2, 2]


def test_multiselect_hash():
    data = {"a": 1, "b": {"c": 2}}
    assert jmespath.search("{x: a, y: b.c, z: nope}", data) == {"x": 1, "y": 2, "z": None}
    assert jmespath.search('{"quoted key": a}', data) == {"quoted key": 1}
    assert jmespath.search("{x: a}", None) is None
    assert jmespath.search("people[?age > `40`].{n: name, a: age}", PEOPLE) == [{"n": "cy", "a": 45}]
    assert jmespath.search("b.{c: c}", data) == {"c": 2}


def test_multiselect_hash_uses_dict_cls():
    options = jmespath.Options(dict_cls=collections.OrderedDict)
    result = jmespath.search("{b: b, a: a}", {"a": 1, "b": 2}, options=options)
    assert isinstance(result, collections.OrderedDict)
    assert list(result.items()) == [("b", 2), ("a", 1)]
    assert type(jmespath.search("{b: b}", {"b": 1})) is dict


# --- pipes, boolean logic, comparators ---------------------------------------


def test_pipes():
    data = {"a": {"b": [{"c": 1}, {"c": 2}]}}
    assert jmespath.search("a | b", data) == [{"c": 1}, {"c": 2}]
    assert jmespath.search("a.b[*].c | [0]", data) == 1
    assert jmespath.search("a.b | length(@)", data) == 2
    assert jmespath.search("a | b | [1] | c", data) == 2


def test_pipes_inside_nested_expressions():
    data = {"a": [{"b": 1}, {"b": 2}], "c": {"d": "x"}}
    assert jmespath.search("(a[*].b | [0])", data) == 1
    assert jmespath.search("[a[*].b | [1], c.d]", data) == [2, "x"]
    assert jmespath.search("{first: a[*].b | [0]}", data) == {"first": 1}
    assert jmespath.search("length(a[*].b | [0:1])", data) == 1
    assert jmespath.search("a[?b | @ > `1`].b", data) == [2]


def test_or_expression():
    assert jmespath.search("a || b", {"a": 0, "b": 1}) == 0
    assert jmespath.search("a || b", {"a": False, "b": 1}) == 1
    assert jmespath.search("a || b", {"a": "", "b": "y"}) == "y"
    assert jmespath.search("a || b", {"a": [], "b": 1}) == 1
    assert jmespath.search("a || b", {"a": {}, "b": 1}) == 1
    assert jmespath.search("a || b", {"b": 1}) == 1
    assert jmespath.search("a || b", {"a": "x", "b": 1}) == "x"
    assert jmespath.search("a || b", {}) is None


def test_and_expression():
    assert jmespath.search("a && b", {"a": 1, "b": 2}) == 2
    assert jmespath.search("a && b", {"a": [], "b": 2}) == []
    assert jmespath.search("a && b", {"a": "", "b": 2}) == ""
    assert jmespath.search("a && b", {"a": False, "b": 2}) is False
    assert jmespath.search("a && b", {"b": 2}) is None
    assert jmespath.search("a && b", {"a": 0, "b": 2}) == 2


def test_not_expression():
    assert jmespath.search("!a", {"a": True}) is False
    assert jmespath.search("!a", {"a": False}) is True
    assert jmespath.search("!a", {"a": 0}) is False
    assert jmespath.search("!a", {"a": 1}) is False
    assert jmespath.search("!a", {"a": ""}) is True
    assert jmespath.search("!a", {"a": []}) is True
    assert jmespath.search("!a", {}) is True
    assert jmespath.search("!!a", {"a": "x"}) is True


def test_operator_precedence():
    data = {"a": True, "b": False, "c": True}
    assert jmespath.search("a || b && c", {"a": "A", "b": "", "c": "C"}) == "A"
    assert jmespath.search("b && c || a", {"a": "A", "b": "", "c": "C"}) == "A"
    assert jmespath.search("!b && c", data) is True
    assert jmespath.search("!(a && b)", data) is True
    assert jmespath.search("(a || b) && c", {"a": "", "b": "B", "c": "C"}) == "C"
    assert jmespath.search("a || b && c", {"a": "", "b": "B", "c": "C"}) == "C"
    assert jmespath.search("x == `1` || y == `2`", {"x": 1, "y": 3}) is True
    assert jmespath.search("x == `1` && y == `2`", {"x": 1, "y": 3}) is False
    assert jmespath.search("!x == `1`", {"x": 1}) is False


def test_comparators():
    data = {"one": 1, "two": 2, "s": "abc", "t": True, "n": None, "l": [1], "o": {"k": 1}}
    assert jmespath.search("one < two", data) is True
    assert jmespath.search("one <= `1`", data) is True
    assert jmespath.search("one > `1`", data) is False
    assert jmespath.search("one >= `1`", data) is True
    assert jmespath.search("two > one", data) is True
    assert jmespath.search("one == `1`", data) is True
    assert jmespath.search("one != `1`", data) is False
    assert jmespath.search("s == 'abc'", data) is True
    assert jmespath.search("l == `[1]`", data) is True
    assert jmespath.search("o == `{\"k\": 1}`", data) is True
    assert jmespath.search("n == missing", data) is True
    assert jmespath.search("s < 'b'", data) is True
    assert jmespath.search("s >= 'b'", data) is False
    assert jmespath.search("t > `0`", data) is None
    assert jmespath.search("l < `2`", data) is None
    assert jmespath.search("one < n", data) is None
    assert jmespath.search("`1.5` < `2`", {}) is True


def test_equality_does_not_mix_booleans_and_numbers():
    assert jmespath.search("a == `true`", {"a": 1}) is False
    assert jmespath.search("a == `false`", {"a": 0}) is False
    assert jmespath.search("a != `true`", {"a": 1}) is True
    assert jmespath.search("`true` == a", {"a": 1}) is False
    assert jmespath.search("`false` == a", {"a": 0}) is False
    assert jmespath.search("a == `1`", {"a": 1.0}) is True
    assert jmespath.search("a == `true`", {"a": True}) is True
    assert jmespath.search("[?@ == `1`]", [1, True, 1.0]) == [1, 1.0]


# --- literals, raw strings, current node ---------------------------------------


def test_literals_and_raw_strings():
    assert jmespath.search("`\"foo\"`", {}) == "foo"
    assert jmespath.search("`[1, 2, {\"a\": null}]`", {}) == [1, 2, {"a": None}]
    assert jmespath.search("`true`", {}) is True
    assert jmespath.search("`null`", {}) is None
    assert jmespath.search("`-3.5`", {}) == -3.5
    assert jmespath.search("'raw string'", {}) == "raw string"
    assert jmespath.search("'it\\'s'", {}) == "it's"
    assert jmespath.search("'a\\nb'", {}) == "a\\nb"
    assert jmespath.search("`\"a\\u0041\"`", {}) == "aA"
    assert jmespath.search("`[1, \"\\`\"]`", {}) == [1, "`"]
    assert jmespath.search("''", {}) == ""


def test_quoted_identifiers_with_escapes():
    data = {"a\"b": 1, "tab\there": 2, "\u2713": 3}
    assert jmespath.search('"a\\"b"', data) == 1
    assert jmespath.search('"tab\\there"', data) == 2
    assert jmespath.search('"\\u2713"', data) == 3


def test_current_node():
    assert jmespath.search("@", {"a": 1}) == {"a": 1}
    assert jmespath.search("@.a", {"a": 1}) == 1
    assert jmespath.search("a[*] | [?@ != `1`]", {"a": [1, 2]}) == [2]
    assert jmespath.search("[*].[@, @]", [1, 2]) == [[1, 1], [2, 2]]


def test_whitespace_is_ignored():
    data = {"a": {"b": [1, 2, 3]}}
    assert jmespath.search("  a . b [ 1 ]  ", data) == 2
    assert jmespath.search("a.b[? @ > `1` ]", data) == [2, 3]


def test_syntax_errors():
    for expr in ["a.", "a[", "[a", "{a: }", "a..b", "foo(", "a ||", "'abc", "a[?]", "!", "a ~ b", ".a"]:
        with pytest.raises(exceptions.JMESPathError):
            jmespath.compile(expr)
    with pytest.raises(exceptions.LexerError):
        jmespath.compile("a ~ b")
    with pytest.raises(exceptions.ParseError):
        jmespath.compile('"foo"(@)')
    with pytest.raises(exceptions.IncompleteExpressionError):
        jmespath.compile("a.b ||")


def test_compile_returns_reusable_expression():
    expr = jmespath.compile("a[*].b")
    assert expr.search({"a": [{"b": 1}, {"b": 2}]}) == [1, 2]
    assert expr.search({"a": [{"b": "x"}]}) == ["x"]
    assert jmespath.compile("a[*].b").search({"a": []}) == []


# --- built-in functions ---------------------------------------------------------


@pytest.mark.parametrize(
    "expr, expected",
    [
        ("abs(`-3`)", 3),
        ("abs(`2.5`)", 2.5),
        ("avg(`[1, 2, 3, 4]`)", 2.5),
        ("avg(`[]`)", None),
        ("ceil(`1.2`)", 2),
        ("ceil(`-1.2`)", -1),
        ("floor(`1.8`)", 1),
        ("floor(`-1.2`)", -2),
        ("contains(`[1, 2, 3]`, `2`)", True),
        ("contains(`[1, 2, 3]`, `4`)", False),
        ("contains('foobar', 'oba')", True),
        ("contains('foobar', 'x')", False),
        ("ends_with('foobar', 'bar')", True),
        ("ends_with('foobar', 'foo')", False),
        ("starts_with('foobar', 'foo')", True),
        ("starts_with('foobar', 'bar')", False),
        ("join(', ', `[\"a\", \"b\", \"c\"]`)", "a, b, c"),
        ("join('-', `[]`)", ""),
        ("length('hello')", 5),
        ("length(`[1, 2, 3]`)", 3),
        ("length(`{\"a\": 1, \"b\": 2}`)", 2),
        ("length('')", 0),
        ("max(`[3, 9, 1]`)", 9),
        ("max(`[\"b\", \"c\", \"a\"]`)", "c"),
        ("max(`[7]`)", 7),
        ("max(`[2.5]`)", 2.5),
        ("max(`[]`)", None),
        ("min(`[3, 9, 1]`)", 1),
        ("min(`[\"b\", \"c\", \"a\"]`)", "a"),
        ("min(`[\"z\"]`)", "z"),
        ("min(`[]`)", None),
        ("sum(`[1, 2, 3.5]`)", 6.5),
        ("sum(`[]`)", 0),
        ("reverse(`[1, 2, 3]`)", [3, 2, 1]),
        ("reverse('abc')", "cba"),
        ("reverse(`[]`)", []),
        ("sort(`[3, 1, 2]`)", [1, 2, 3]),
        ("sort(`[\"b\", \"a\", \"c\"]`)", ["a", "b", "c"]),
        ("sort(`[5]`)", [5]),
        ("sort(`[]`)", []),
        ("not_null(`null`, `1`, `2`)", 1),
        ("not_null(`null`, `false`)", False),
        ("not_null(`null`, `null`)", None),
        ("to_array(`1`)", [1]),
        ("to_array(`[1]`)", [1]),
        ("to_array(`null`)", [None]),
        ("to_string('x')", "x"),
        ("to_string(`1`)", "1"),
        ("to_string(`[1, 2]`)", "[1,2]"),
        ("to_string(`{\"a\": 1}`)", '{"a":1}'),
        ("to_string(`null`)", "null"),
        ("to_string(`true`)", "true"),
        ("to_number('12')", 12),
        ("to_number('1.5')", 1.5),
        ("to_number('abc')", None),
        ("to_number(`3`)", 3),
        ("to_number(`true`)", None),
        ("to_number(`[1]`)", None),
        ("to_number(`null`)", None),
        ("type('a')", "string"),
        ("type(`1`)", "number"),
        ("type(`1.5`)", "number"),
        ("type(`true`)", "boolean"),
        ("type(`[]`)", "array"),
        ("type(`{}`)", "object"),
        ("type(`null`)", "null"),
        ("merge(`{\"a\": 1}`, `{\"b\": 2}`, `{\"a\": 3}`)", {"a": 3, "b": 2}),
        ("merge(`{\"a\": 1}`)", {"a": 1}),
    ],
)
def test_builtin_functions(expr, expected):
    result = jmespath.search(expr, {})
    assert result == expected
    assert type(result) is type(expected)


def test_keys_and_values():
    data = {"o": {"x": 1, "y": 2, "z": 3}}
    assert sorted(jmespath.search("keys(o)", data)) == ["x", "y", "z"]
    assert sorted(jmespath.search("values(o)", data)) == [1, 2, 3]
    assert jmespath.search("keys(`{}`)", data) == []


def test_functions_on_data():
    assert jmespath.search("length(people)", PEOPLE) == 4
    assert jmespath.search("max(people[*].age)", PEOPLE) == 45
    assert jmespath.search("sum(people[*].age)", PEOPLE) == 124
    assert jmespath.search("people[:3] | [?contains(tags, 'b')].name", PEOPLE) == ["ann"]
    assert jmespath.search("people[?starts_with(name, 'b')].name", PEOPLE) == ["bob"]
    assert jmespath.search("join(',', people[*].name)", PEOPLE) == "ann,bob,cy,dee"
    assert jmespath.search("people[:3] | [?length(tags) > `0`].name", PEOPLE) == ["ann", "bob"]
    assert jmespath.search("to_string(people[0].age)", PEOPLE) == "31"


def test_by_functions():
    ppl = PEOPLE["people"]
    assert jmespath.search("sort_by(people, &age)[*].name", PEOPLE) == ["bob", "ann", "dee", "cy"]
    assert jmespath.search("sort_by(people, &name)[*].name", PEOPLE) == ["ann", "bob", "cy", "dee"]
    assert jmespath.search("max_by(people, &age).name", PEOPLE) == "cy"
    assert jmespath.search("min_by(people, &age).name", PEOPLE) == "bob"
    assert jmespath.search("max_by(people, &name).name", PEOPLE) == "dee"
    assert jmespath.search("min_by(people, &name).name", PEOPLE) == "ann"
    assert jmespath.search("max_by(`[]`, &a)", {}) is None
    assert jmespath.search("min_by(`[]`, &a)", {}) is None
    assert jmespath.search("sort_by(`[]`, &a)", {}) == []
    scored = ppl[:3]
    assert jmespath.search("sort_by(@, &score)[*].name", scored) == ["cy", "ann", "bob"]
    assert jmespath.search("max_by(@, &score).name", scored) == "bob"
    assert jmespath.search("min_by(@, &score).name", scored) == "cy"
    assert jmespath.search("sort_by(@, &age)", [{"age": 3}]) == [{"age": 3}]


def test_sort_by_is_stable():
    data = [{"k": 1, "i": 0}, {"k": 0, "i": 1}, {"k": 1, "i": 2}, {"k": 0, "i": 3}]
    assert jmespath.search("sort_by(@, &k)[*].i", data) == [1, 3, 0, 2]


def test_map():
    data = {"a": [{"b": 1}, {"c": 2}, {"b": 3}]}
    assert jmespath.search("map(&b, a)", data) == [1, None, 3]
    assert jmespath.search("map(&length(@), `[\"ab\", \"c\"]`)", {}) == [2, 1]
    assert jmespath.search("map(&[0], `[[1, 2], [3]]`)", {}) == [1, 3]
    assert jmespath.search("map(&b, `[]`)", {}) == []


def test_function_type_errors():
    bad = [
        "abs('x')",
        "avg(`[1, \"a\"]`)",
        "length(`1`)",
        "max(`[1, \"a\"]`)",
        "max(`[\"a\", 1]`)",
        "min(`[true]`)",
        "sort(`[1, \"a\"]`)",
        "sum(`[\"a\"]`)",
        "join(',', `[1]`)",
        "keys(`[1]`)",
        "values('x')",
        "starts_with(`1`, 'a')",
        "ends_with('a', `1`)",
        "merge(`[1]`)",
        "ceil('1')",
        "reverse(`1`)",
        "contains(`1`, `1`)",
        "sort_by(`[{\"a\": true}]`, &a)",
        "sort_by(`[{\"a\": 1}, {\"a\": \"x\"}]`, &a)",
        "max_by(`[{\"a\": [1]}, {\"a\": [2]}]`, &a)",
        "min_by(`[{\"a\": null}]`, &a)",
        "map(&a, `{}`)",
    ]
    for expr in bad:
        with pytest.raises(exceptions.JMESPathTypeError):
            jmespath.search(expr, {})


def test_function_arity_errors():
    with pytest.raises(exceptions.ArityError):
        jmespath.search("abs(`1`, `2`)", {})
    with pytest.raises(exceptions.ArityError):
        jmespath.search("length()", {})
    with pytest.raises(exceptions.VariadictArityError):
        jmespath.search("not_null()", {})
    with pytest.raises(exceptions.VariadictArityError):
        jmespath.search("merge()", {})
    with pytest.raises(exceptions.UnknownFunctionError):
        jmespath.search("nope(`1`)", {})


# --- custom functions ------------------------------------------------------------


class CustomFunctions(functions.Functions):
    @functions.signature({"types": ["string"]})
    def _func_upper(self, s):
        return s.upper()

    @functions.signature({"types": ["number"]}, {"types": ["number"]})
    def _func_add(self, a, b):
        return a + b

    @functions.signature({"types": [], "variadic": True})
    def _func_count(self, *args):
        return len(args)

    @functions.signature({"types": ["array-number", "array-string"]})
    def _func_first(self, arr):
        return arr[0] if arr else None

    def _func_unregistered(self, x):
        return x

    def helper(self):
        return 1


def test_custom_functions():
    opts = jmespath.Options(custom_functions=CustomFunctions())
    assert jmespath.search("upper(name)", {"name": "ann"}, options=opts) == "ANN"
    assert jmespath.search("add(`1`, `2`)", {}, options=opts) == 3
    assert jmespath.search("count(`1`, `2`, `3`)", {}, options=opts) == 3
    assert jmespath.search("count(`1`)", {}, options=opts) == 1
    assert jmespath.search("first(`[\"q\", \"r\"]`)", {}, options=opts) == "q"
    assert jmespath.search("first(`[4]`)", {}, options=opts) == 4
    assert jmespath.search("people[*].name | [].upper(@)", PEOPLE, options=opts) == ["ANN", "BOB", "CY", "DEE"]
    # built-ins stay available through the subclass
    assert jmespath.search("length(`[1, 2]`)", {}, options=opts) == 2
    compiled = jmespath.compile("add(a, `10`)")
    assert compiled.search({"a": 5}, options=opts) == 15


def test_custom_function_validation():
    opts = jmespath.Options(custom_functions=CustomFunctions())
    with pytest.raises(exceptions.JMESPathTypeError):
        jmespath.search("upper(`1`)", {}, options=opts)
    with pytest.raises(exceptions.JMESPathTypeError):
        jmespath.search("first(`[1, \"a\"]`)", {}, options=opts)
    with pytest.raises(exceptions.ArityError):
        jmespath.search("add(`1`)", {}, options=opts)
    with pytest.raises(exceptions.VariadictArityError):
        jmespath.search("count()", {}, options=opts)
    with pytest.raises(exceptions.UnknownFunctionError):
        jmespath.search("unregistered(`1`)", {}, options=opts)
    with pytest.raises(exceptions.UnknownFunctionError):
        jmespath.search("helper()", {}, options=opts)
    with pytest.raises(exceptions.UnknownFunctionError):
        jmespath.search("upper('a')", {})
PY
# Stage the new files so the oracle control sees them in git diff HEAD.
git add -A regression_tests
