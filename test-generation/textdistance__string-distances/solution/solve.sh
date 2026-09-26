#!/bin/bash
set -euo pipefail
cd /app
mkdir -p regression_tests
cat > regression_tests/test_string_distances.py <<'PY'
"""Reference regression suite for textdistance's pure-Python algorithms."""
import pytest

import textdistance as td


def approx(x):
    return pytest.approx(x, abs=1e-9)


# ---- Hamming ---------------------------------------------------------------

def test_hamming_distance():
    assert td.hamming("test", "text") == 1
    assert td.hamming("test", "tesst") == 2
    assert td.hamming("abc", "abcde") == 2
    assert td.hamming("abc", "abc") == 0
    assert td.hamming("", "abc") == 3
    assert td.hamming("abc", "abd", "abe") == 1


def test_hamming_options():
    assert td.Hamming(truncate=True)("abc", "abcde") == 0
    assert td.Hamming(truncate=True)("abx", "abcde") == 1
    assert td.Hamming(qval=2)("test", "text") == 2
    assert td.Hamming(external=False)("test", "text") == 1


def test_hamming_interface():
    assert td.hamming.distance("test", "text") == 1
    assert td.hamming.similarity("test", "text") == 3
    assert td.hamming.maximum("test", "tester") == 6
    assert td.hamming.normalized_distance("test", "text") == approx(0.25)
    assert td.hamming.normalized_similarity("test", "text") == approx(0.75)


# ---- Levenshtein -----------------------------------------------------------

@pytest.mark.parametrize("left, right, expected", [
    ("test", "text", 1), ("test", "tset", 2), ("kitten", "sitting", 3),
    ("flaw", "lawn", 2), ("", "abc", 3), ("abc", "", 3), ("abc", "abc", 0),
    ("abc", "abcd", 1), ("abcd", "bcd", 1),
])
def test_levenshtein_distance(left, right, expected):
    assert td.levenshtein(left, right) == expected
    assert td.Levenshtein(external=False).distance(left, right) == expected


def test_levenshtein_other_sequences_and_qval():
    assert td.levenshtein(["a", "b", "c"], ["a", "c"]) == 1
    assert td.levenshtein((1, 2, 3), (1, 2, 4)) == 1
    assert td.Levenshtein(qval=2)("test", "text") == 2


def test_levenshtein_interface():
    assert td.levenshtein.maximum("kitten", "sitting") == 7
    assert td.levenshtein.similarity("kitten", "sitting") == 4
    assert td.levenshtein.normalized_distance("kitten", "sitting") == approx(3 / 7)
    assert td.levenshtein.normalized_similarity("kitten", "sitting") == approx(4 / 7)
    assert td.levenshtein.normalized_distance("", "") == 0
    assert td.levenshtein.normalized_similarity("", "") == 1


# ---- Damerau-Levenshtein ---------------------------------------------------

@pytest.mark.parametrize("left, right, expected", [
    ("test", "tset", 1), ("test", "text", 1), ("ca", "abc", 3), ("kitten", "sitting", 3),
    ("abcd", "badc", 2), ("abcdef", "abdcef", 1), ("", "ab", 2), ("ab", "ab", 0),
])
def test_damerau_levenshtein_restricted(left, right, expected):
    assert td.damerau_levenshtein(left, right) == expected


def test_damerau_levenshtein_unrestricted():
    unrestricted = td.DamerauLevenshtein(restricted=False)
    assert unrestricted("ca", "abc") == 2
    assert unrestricted("test", "tset") == 1
    assert unrestricted("kitten", "sitting") == 3
    assert unrestricted("abcd", "badc") == 2


def test_damerau_levenshtein_interface():
    assert td.damerau_levenshtein.normalized_distance("test", "tset") == approx(0.25)
    assert td.damerau_levenshtein.similarity("test", "tset") == 3


# ---- Jaro and Jaro-Winkler -------------------------------------------------

def test_jaro_winkler_similarity():
    assert td.jaro_winkler("MARTHA", "MARHTA") == approx(0.9611111111111111)
    assert td.jaro_winkler("DWAYNE", "DUANE") == approx(0.84)
    assert td.jaro_winkler("DIXON", "DICKSONX") == approx(0.8133333333333332)
    assert td.jaro_winkler("abc", "abc") == 1
    assert td.jaro_winkler("abc", "xyz") == 0
    assert td.jaro_winkler("", "abc") == 0


def test_jaro_similarity():
    assert td.jaro("MARTHA", "MARHTA") == approx(0.9444444444444445)
    assert td.jaro("DWAYNE", "DUANE") == approx(0.8222222222222223)
    assert td.JaroWinkler(winklerize=False)("MARTHA", "MARHTA") == approx(0.9444444444444445)


def test_jaro_winkler_long_tolerance():
    assert td.jaro_winkler("frog-food", "frog-feed") == approx(0.9111111111111111)
    assert td.JaroWinkler(long_tolerance=True)("frog-food", "frog-feed") == approx(0.9259259259259259)


def test_jaro_winkler_interface():
    assert td.jaro_winkler.maximum("a", "bc") == 1
    assert td.jaro_winkler.similarity("MARTHA", "MARHTA") == approx(0.9611111111111111)
    assert td.jaro_winkler.distance("MARTHA", "MARHTA") == approx(1 - 0.9611111111111111)
    assert td.jaro_winkler.normalized_distance("MARTHA", "MARHTA") == approx(1 - 0.9611111111111111)


# ---- Jaccard ---------------------------------------------------------------

def test_jaccard():
    assert td.jaccard("decide", "resize") == approx(1 / 3)
    assert td.jaccard("test", "text") == approx(0.6)
    assert td.jaccard("nelson", "neilsen") == approx(0.625)
    assert td.jaccard("", "abc") == 0
    assert td.jaccard("", "") == 1
    assert td.jaccard("abc", "abc") == 1


def test_jaccard_options():
    assert td.Jaccard(as_set=True)("test", "text") == approx(0.5)
    assert td.Jaccard(qval=2)("test", "text") == approx(0.2)
    assert td.Jaccard(qval=None)("the cat sat", "the dog sat") == approx(0.5)


def test_jaccard_interface():
    assert td.jaccard.maximum("ab", "c") == 1
    assert td.jaccard.distance("test", "text") == approx(0.4)
    assert td.jaccard.normalized_distance("test", "text") == approx(0.4)
    assert td.jaccard.normalized_similarity("test", "text") == approx(0.6)


# ---- LCS subsequence -------------------------------------------------------

def test_lcsseq():
    assert td.lcsseq("test", "text") == "tet"
    assert td.lcsseq("thisisatest", "testing123testing") == "tsitest"
    assert td.lcsseq("abc", "xyz") == ""
    assert td.lcsseq("", "abc") == ""
    assert td.lcsseq("ab", "ab", "acb") == "ab"


def test_lcsseq_interface():
    assert td.lcsseq.similarity("thisisatest", "testing123testing") == 7
    assert td.lcsseq.maximum("test", "texts") == 5
    assert td.lcsseq.distance("test", "text") == 1
    assert td.lcsseq.distance("test", "texts") == 2
    assert td.lcsseq.normalized_similarity("test", "texts") == approx(0.6)
    assert td.lcsseq.normalized_distance("test", "texts") == approx(0.4)


# ---- Prefix and postfix ----------------------------------------------------

def test_prefix():
    assert td.prefix("test", "text") == "te"
    assert td.prefix("abc", "xyz") == ""
    assert td.prefix([1, 2, 3], [1, 2, 4]) == [1, 2]
    assert td.prefix.similarity("test", "tesla") == 3
    assert td.prefix.maximum("ab", "abcd") == 4
    assert td.prefix.distance("test", "tesla") == 2
    assert td.prefix.normalized_similarity("test", "tesla") == approx(0.6)


def test_postfix():
    assert td.postfix("test", "best") == "est"
    assert td.postfix("abc", "xyz") == ""
    assert td.postfix([1, 2, 3], [0, 2, 3]) == [2, 3]
    assert td.postfix.similarity("testing", "resting") == 6
    assert td.postfix.distance("testing", "resting") == 1
PY
# Stage the new files so the oracle control sees them in git diff HEAD (runs inside the task container).
git add -A regression_tests
