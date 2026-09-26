#!/bin/bash
set -euo pipefail
cd /app
mkdir -p regression_tests
cat > regression_tests/test_slugify.py <<'PY'
"""Reference regression suite for python-slugify's modern slugify() algorithm."""
import re

import pytest

from slugify import slugify


def modern(text, **kwargs):
    return slugify(text, algorithm="modern", **kwargs)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("This is a test ---", "this-is-a-test"),
        ("Hello, World!", "hello-world"),
        ("C'est déjà l'été.", "c-est-deja-l-ete"),
        ("影師嗎", "ying-shi-ma"),
        ("Компьютер", "kompiuter"),
        ("i love 🦄", "i-love"),
        ("hello_world", "hello-world"),
        ("  --leading and trailing--  ", "leading-and-trailing"),
        ("", ""),
    ],
)
def test_default_slugs(text, expected):
    assert modern(text) == expected


def test_numbers_with_thousands_separators():
    assert modern("1,000 reasons") == "1000-reasons"
    assert modern("12,345,678 items") == "12345678-items"
    assert modern("a,b 1, 2") == "a-b-1-2"


def test_bytes_input_is_decoded():
    assert modern("Café Noir".encode("utf-8")) == "cafe-noir"
    assert modern(bytearray(b"abc def")) == "abc-def"


def test_html_references_decoded_by_default():
    assert modern("foo &amp; bar") == "foo-bar"
    assert modern("&#381;") == "z"
    assert modern("&#x17D;") == "z"
    assert modern("&#X17D;") == "z"
    assert modern("a&#39;b") == "a-b"


def test_reference_flags_can_be_disabled():
    assert modern("foo &amp; bar", entities=False) == "foo-amp-bar"
    assert modern("&#381;", decimal=False) == "381"
    assert modern("&#x17D;", hexadecimal=False) == "x17d"


def test_separator():
    assert modern("one two three", separator="_") == "one_two_three"
    assert modern("one two three", separator=".") == "one.two.three"
    assert modern("a b c", separator="") == "abc"
    assert modern("a b", separator="--") == "a--b"


def test_max_length_hard_cut():
    assert modern("abcdefghij", max_length=5) == "abcde"
    assert modern("ab cd", max_length=5) == "ab-cd"
    assert modern("ab cd", max_length=4) == "ab-c"
    assert modern("ab cd", max_length=3) == "ab"
    assert modern("aa bb cc", max_length=7) == "aa-bb-c"
    assert modern("one two three four five", max_length=10) == "one-two-th"
    assert modern("jaja---lol-méméméoo--a", max_length=15) == "jaja-lol-mememe"


def test_max_length_counts_separator_characters():
    assert modern("a b c", separator="---", max_length=5) == "a---b"
    assert modern("aa bb cc", separator="__", max_length=9) == "aa__bb__c"


def test_max_length_zero_means_unlimited():
    text = "a fairly long title for a blog post"
    assert modern(text, max_length=0) == "a-fairly-long-title-for-a-blog-post"
    assert modern("short text", max_length=50) == "short-text"


def test_word_boundary():
    assert modern("jaja---lol-méméméoo--a", max_length=15, word_boundary=True) == "jaja-lol-a"
    assert modern("one two three four", max_length=12, word_boundary=True) == "one-two-four"
    assert modern("one two three", max_length=7, word_boundary=True) == "one-two"
    assert modern("abcdefghij", max_length=4, word_boundary=True) == "abcd"


def test_save_order():
    text = "one two three four"
    assert modern(text, max_length=12, word_boundary=True, save_order=True) == "one-two"
    assert modern(text, max_length=12, word_boundary=True, save_order=False) == "one-two-four"


def test_stopwords():
    text = "the quick brown fox jumps over the lazy dog"
    assert modern(text, stopwords=["the"]) == "quick-brown-fox-jumps-over-lazy-dog"
    assert modern(text, stopwords=["the", "over"]) == "quick-brown-fox-jumps-lazy-dog"
    assert modern("The quick brown fox", stopwords=["THE"]) == "quick-brown-fox"
    assert modern("The quick brown fox", stopwords=["the"], lowercase=False) == "The-quick-brown-fox"
    assert modern("The quick brown fox", stopwords=["The"], lowercase=False) == "quick-brown-fox"


def test_lowercase_flag():
    assert modern("Hello World") == "hello-world"
    assert modern("Hello World", lowercase=False) == "Hello-World"


def test_replacements():
    assert modern("10 | 20 %", replacements=[["|", "or"], ["%", "percent"]]) == "10-or-20-percent"
    assert modern("I ♥ you", replacements=[["♥", "love"]]) == "i-love-you"


def test_regex_pattern():
    assert modern("___This is a test___", regex_pattern=r"[^-a-z0-9_]+") == "___this-is-a-test___"
    assert modern("___This is a test___", regex_pattern=re.compile(r"[^-a-z0-9_]+")) == "___this-is-a-test___"
    assert modern("___This is a test___") == "this-is-a-test"


def test_allow_unicode():
    assert modern("影師嗎", allow_unicode=True) == "影師嗎"
    assert modern("影師嗎 test", allow_unicode=True) == "影師嗎-test"
    assert modern("Компьютер", allow_unicode=True) == "компьютер"
    assert modern("C'est déjà l'été.", allow_unicode=True) == "c-est-déjà-l-été"
    assert modern("hello_world", allow_unicode=True) == "hello-world"
PY
# The oracle harness diffs against HEAD, so stage the new files.
git add -A regression_tests
