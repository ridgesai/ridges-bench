"""Direct and rendered contracts for the core Markdown tokenizer."""

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(os.environ["REPO_ROOT"])
sys.path.insert(0, str(REPO_ROOT))

from mistletoe import markdown
from mistletoe.core_tokens import find_core_tokens, match_link_dest


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("(abc)", (1, 4, "abc")),
        ("(a(b)c)", (1, 6, "a(b)c")),
        ("(<a\\>b>)", (1, 7, "a\\>b")),
        ("(<a<b>)", None),
        ("(a\\(b\\)c)", (1, 8, "a\\(b\\)c")),
        ("(abc def)", (1, 4, "abc")),
        ("(abc", None),
    ],
)
def test_link_destination_boundaries_and_text(source, expected):
    assert match_link_dest(source, 0) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("!x[a](b)", [("Link", 2, 8, "ab", "uri")]),
        ("!![a](b)", [("Image", 1, 8, "ab", "uri")]),
        ("`[a](b)`", []),
        (
            "[a](b)![c](d)",
            [("Link", 0, 6, "ab", "uri"), ("Image", 6, 13, "cd", "uri")],
        ),
        (
            "![a](b)[c](d)",
            [("Image", 0, 7, "ab", "uri"), ("Link", 7, 13, "cd", "uri")],
        ),
        ("[a](<x\\>y>)", [("Link", 0, 11, "ax\\>y", "angle_uri")]),
        ("[a](x(y)z)", [("Link", 0, 10, "ax(y)z", "uri")]),
    ],
)
def test_match_types_offsets_and_state_transitions(source, expected):
    matches = find_core_tokens(source, None)
    observed = [
        (match.type, match.start(), match.end(), match.group(), match.dest_type)
        for match in matches
    ]
    assert observed == expected


@pytest.mark.parametrize(
    ("source", "expected_html"),
    [
        ("`[a](b)`", "<p><code>[a](b)</code></p>\n"),
        ("[outer [inner](x)](y)", '<p>[outer <a href="x">inner</a>](y)</p>\n'),
        (
            "**a [b](c) d**",
            '<p><strong>a <a href="c">b</a> d</strong></p>\n',
        ),
        ("![a](<x\\>y>)", '<p><img src="x%3Ey" alt="a" /></p>\n'),
        ("\\![a](b)", '<p>!<a href="b">a</a></p>\n'),
    ],
)
def test_rendered_markdown_edge_cases(source, expected_html):
    assert markdown(source) == expected_html
