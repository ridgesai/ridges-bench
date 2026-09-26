#!/bin/bash
set -euo pipefail
cd /app
mkdir -p regression_tests
cat > regression_tests/test_inflect.py <<'PY'
"""Reference regression suite for inflect's English inflection engine."""
import pytest

import inflect


@pytest.fixture
def p():
    return inflect.engine()


PLURALS = [
    ("cat", "cats"),
    ("box", "boxes"),
    ("church", "churches"),
    ("bus", "buses"),
    ("quiz", "quizzes"),
    ("baby", "babies"),
    ("day", "days"),
    ("knife", "knives"),
    ("wolf", "wolves"),
    ("roof", "roofs"),
    ("potato", "potatoes"),
    ("photo", "photos"),
    ("hero", "heroes"),
    ("mouse", "mice"),
    ("child", "children"),
    ("man", "men"),
    ("woman", "women"),
    ("tooth", "teeth"),
    ("ox", "oxen"),
    ("person", "people"),
    ("sheep", "sheep"),
    ("deer", "deer"),
    ("fish", "fish"),
    ("analysis", "analyses"),
    ("criterion", "criteria"),
    ("datum", "data"),
    ("mother-in-law", "mothers-in-law"),
    ("goose", "geese"),
    ("snow goose", "snow geese"),
    ("wisdom tooth", "wisdom teeth"),
]


@pytest.mark.parametrize("singular, plural", PLURALS)
def test_plural_noun(p, singular, plural):
    assert p.plural_noun(singular) == plural
    assert p.plural(singular) == plural


@pytest.mark.parametrize("singular, plural", PLURALS)
def test_singular_noun(p, singular, plural):
    assert p.singular_noun(plural) == singular


def test_singular_noun_of_singular_is_false(p):
    assert p.singular_noun("cat") is False
    assert p.singular_noun("child") is False


def test_plural_preserves_case(p):
    assert p.plural("Cat") == "Cats"
    assert p.plural("CHILD") == "CHILDREN"


def test_plural_with_count(p):
    assert p.plural("cat", 1) == "cat"
    assert p.plural("cat", 2) == "cats"
    assert p.plural("cat", 0) == "cats"
    assert p.plural_noun("child", 1) == "child"
    assert p.plural_noun("child", 3) == "children"


def test_plural_of_pronouns_and_verbs(p):
    assert p.plural_noun("I") == "we"
    assert p.plural("was") == "were"
    assert p.plural("is") == "are"
    assert p.singular_noun("we") == "I"


@pytest.mark.parametrize(
    "word, expected",
    [
        ("apple", "an apple"),
        ("banana", "a banana"),
        ("hour", "an hour"),
        ("honest", "an honest"),
        ("unicorn", "a unicorn"),
        ("umbrella", "an umbrella"),
        ("European", "a European"),
        ("yak", "a yak"),
        ("ewe", "a ewe"),
        ("FBI", "an FBI"),
        ("X-ray", "an X-ray"),
    ],
)
def test_indefinite_article(p, word, expected):
    assert p.a(word) == expected
    assert p.an(word) == expected


def test_indefinite_article_with_count(p):
    assert p.a("cat", 1) == "a cat"
    assert p.a("cat", 2) == "2 cat"


@pytest.mark.parametrize(
    "num, expected",
    [
        (1, "1st"),
        (2, "2nd"),
        (3, "3rd"),
        (4, "4th"),
        (11, "11th"),
        (12, "12th"),
        (13, "13th"),
        (21, "21st"),
        (22, "22nd"),
        (23, "23rd"),
        (101, "101st"),
        (111, "111th"),
        (112, "112th"),
        ("1", "1st"),
        ("2", "2nd"),
        ("11", "11th"),
        ("12", "12th"),
        ("13", "13th"),
        ("23", "23rd"),
        ("one", "first"),
        ("two", "second"),
        ("three", "third"),
        ("five", "fifth"),
        ("twelve", "twelfth"),
        ("twenty", "twentieth"),
        ("twenty-one", "twenty-first"),
        ("one hundred", "one hundredth"),
    ],
)
def test_ordinal(p, num, expected):
    assert p.ordinal(num) == expected


@pytest.mark.parametrize(
    "num, expected",
    [
        (0, "zero"),
        (1, "one"),
        (7, "seven"),
        (10, "ten"),
        (13, "thirteen"),
        (19, "nineteen"),
        (20, "twenty"),
        (21, "twenty-one"),
        (42, "forty-two"),
        (99, "ninety-nine"),
        (100, "one hundred"),
        (101, "one hundred and one"),
        (110, "one hundred and ten"),
        (999, "nine hundred and ninety-nine"),
        (1000, "one thousand"),
        (1001, "one thousand and one"),
        (1234, "one thousand, two hundred and thirty-four"),
        (1000000, "one million"),
        (
            1234567,
            "one million, two hundred and thirty-four thousand, five hundred and sixty-seven",
        ),
        (-5, "minus five"),
        ("3.14", "three point one four"),
        ("1234.5678", "one thousand, two hundred and thirty-four point five six seven eight"),
    ],
)
def test_number_to_words(p, num, expected):
    assert p.number_to_words(num) == expected


def test_number_to_words_andword(p):
    assert p.number_to_words(1234, andword="") == "one thousand, two hundred thirty-four"


def test_number_to_words_wantlist(p):
    assert p.number_to_words(1234, wantlist=True) == ["one thousand", "two hundred and thirty-four"]


def test_number_to_words_zero_one_decimal(p):
    assert p.number_to_words(0, zero="oh") == "oh"
    assert p.number_to_words(1, one="a") == "a"
    assert p.number_to_words("1.5", decimal="dot") == "one dot five"


def test_number_to_words_threshold(p):
    assert p.number_to_words(9, threshold=10) == "nine"
    assert p.number_to_words(10, threshold=10) == "ten"
    assert p.number_to_words(12345, threshold=10) == "12,345"
    assert p.number_to_words(12345, threshold=10, comma="") == "12345"


def test_number_to_words_group(p):
    assert p.number_to_words("1234", group=1) == "one, two, three, four"
    assert p.number_to_words("1234", group=2) == "twelve, thirty-four"
    assert p.number_to_words("1234", group=3) == "one twenty-three, four"
    assert p.number_to_words("5551202", group=1, one="oh") == "five, five, five, oh, two, zero, two"
PY
# The oracle harness diffs against HEAD, so stage the new files.
git add -A regression_tests
