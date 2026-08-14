"""Deterministic differential oracle for mistletoe's core tokenizer.

The expected digests were generated from the pinned, unmodified upstream
revision.  The corpus deliberately mixes well-formed Markdown with abandoned,
escaped, nested, whitespace-heavy, and control-character fragments.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(os.environ["REPO_ROOT"])
sys.path.insert(0, str(REPO_ROOT))

from mistletoe import markdown
from mistletoe.core_tokens import find_core_tokens, match_link_dest


EXPECTED_CORPUS_DIGEST = "c830eb7034c0f38b6470d919bece44a2ae3fe78d231d2a97a038409238cf9979"
EXPECTED_BEHAVIOR_DIGESTS = {
    "match_link_dest": "031c0626346de1b7558aa229c0075c0d25f524404e361724646cd25ce2dee7a5",
    "find_core_tokens": "4911480aec2614bc092d543e6eaf474050c2452a2e1ae2a3d41f5f36010fe263",
    "markdown": "1d196f9b521ca1aed450543bb90047d3e8c3005c9392b54be8695d6e54157485",
}

STRUCTURAL_FRAGMENTS = (
    "[",
    "]",
    "(",
    ")",
    "!",
    "<",
    ">",
    "\\",
    "\\[",
    "\\]",
    "*",
    "_",
    "`",
    "[x](y)",
    "![x](y)",
    "\x01",
)

FRAGMENTS = (
    "a",
    "bc",
    " ",
    "\t",
    "\n",
    "[",
    "]",
    "(",
    ")",
    "!",
    "<",
    ">",
    "\\",
    "\\[",
    "\\]",
    "\\(",
    "\\)",
    "\\<",
    "\\>",
    "*",
    "_",
    "**",
    "__",
    "`",
    "``",
    "[x](y)",
    "![x](y)",
    "[x](<y>)",
    "[x][y]",
    "\x01",
    "\x7f",
)

SEED_CASES = (
    "",
    "plain text",
    "[a](b)",
    "![a](b)",
    "!x[a](b)",
    "!![a](b)",
    "`[a](b)`",
    "``[a](b)``",
    "[outer [inner](x)](y)",
    "![a](<x\\>y>)",
    "[a](x(y)z)",
    "[a](x(y(z)))",
    "[a](x\\(y\\)z)",
    "[a](abc def)",
    "[a](<a<b>)",
    "[a](<a\\>b>)",
    "\\![a](b)",
    "[a] (b)",
    "[a]\n(b)",
    "[a](b)![c](d)",
    "![a](b)[c](d)",
    "**a [b](c) d**",
    "__a ![b](c) d__",
    "[abandoned",
    "![abandoned",
    "[a]",
    "![a]",
    "[]()",
    "![]()",
    "[a](\x01)",
    "[a](\x7f)",
)


def _next(state):
    return (1664525 * state + 1013904223) & 0xFFFFFFFF


def _generated_cases():
    cases = list(SEED_CASES)

    # Exhaustive short interactions expose delimiter-state leakage between
    # otherwise ordinary constructs.
    short = SEED_CASES[2:23]
    cases.extend(left + right for left in short for right in short)
    cases.extend(left + "x" + right for left in short for right in short)
    cases.extend(left + right for left in FRAGMENTS for right in FRAGMENTS)
    cases.extend(
        left + middle + right
        for left in STRUCTURAL_FRAGMENTS
        for middle in STRUCTURAL_FRAGMENTS
        for right in STRUCTURAL_FRAGMENTS
    )

    # A stable grammar-ish fuzzer.  This uses an explicit LCG instead of the
    # random module so the corpus is independent of Python's RNG internals.
    state = 0x5EEDC0DE
    for index in range(16384):
        state = _next(state ^ index)
        part_count = 1 + state % 14
        parts = []
        for _ in range(part_count):
            state = _next(state)
            parts.append(FRAGMENTS[state % len(FRAGMENTS)])
        cases.append("".join(parts))

    # Preserve generation order while removing duplicates.
    return tuple(dict.fromkeys(cases))


def _destination_cases(token_cases):
    cases = [
        ("(abc)", 0),
        ("prefix(a(b)c)", 6),
        ("(<a\\>b>)", 0),
        ("(<a<b>)", 0),
        ("(a\\(b\\)c)", 0),
        ("(abc def)", 0),
        ("(abc", 0),
        ("(\x01)", 0),
        ("(\x7f)", 0),
    ]
    for source in token_cases:
        offset = source.find("(")
        if offset >= 0:
            cases.append((source, offset))
    return tuple(dict.fromkeys(cases))


def _capture(call):
    try:
        return ("ok", call())
    except Exception as error:  # The baseline's failure type is behavior too.
        return ("error", type(error).__module__, type(error).__qualname__)


def _normalize_matches(source):
    matches = find_core_tokens(source, None)
    return [
        (
            match.type,
            match.start(),
            match.end(),
            match.group(),
            getattr(match, "dest_type", None),
        )
        for match in matches
    ]


def _digest(records):
    digest = hashlib.sha256()
    for record in records:
        encoded = json.dumps(
            record, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _observed_digests():
    token_cases = _generated_cases()
    destination_cases = _destination_cases(token_cases)
    corpus_digest = _digest((token_cases, destination_cases))

    behavior = {
        "match_link_dest": _digest(
            _capture(lambda source=source, offset=offset: match_link_dest(source, offset))
            for source, offset in destination_cases
        ),
        "find_core_tokens": _digest(
            _capture(lambda source=source: _normalize_matches(source))
            for source in token_cases
        ),
        "markdown": _digest(
            _capture(lambda source=source: markdown(source)) for source in token_cases
        ),
    }
    return corpus_digest, behavior


def test_deterministic_baseline_differential_corpus():
    corpus_digest, behavior = _observed_digests()
    assert corpus_digest == EXPECTED_CORPUS_DIGEST, "differential corpus drifted"
    assert behavior == EXPECTED_BEHAVIOR_DIGESTS


if __name__ == "__main__":
    print(json.dumps(_observed_digests(), indent=2))
