from __future__ import annotations

import pytest

from fontbom.report.escaping import csv_cell, markdown_code, markdown_text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Plain-Name", "`Plain-Name`"),
        ("One`Tick", "``One`Tick``"),
        ("Two``Ticks", "```Two``Ticks```"),
        ("`Leading", "`` `Leading ``"),  # CommonMark strips one space each side
        ("Pipe|Name", "`Pipe\\|Name`"),
        ("Line\nBreak", "`Line Break`"),
    ],
)
def test_markdown_code_span_cannot_be_closed_early(text: str, expected: str) -> None:
    assert markdown_code(text) == expected


def test_markdown_text_escapes_html_links_and_table_breaks() -> None:
    assert markdown_text("<b>[x](y)</b> a\\|b") == "&lt;b&gt;\\[x\\](y)&lt;/b&gt; a\\\\\\|b"


@pytest.mark.parametrize("start", ["=", "+", "-", "@"])
def test_csv_cell_neutralises_formula_starts(start: str) -> None:
    assert csv_cell(f"{start}SUM(A1)").startswith("'")


@pytest.mark.parametrize("start", ["\t", "\r"])
def test_csv_cell_shows_leading_control_characters(start: str) -> None:
    assert csv_cell(f"{start}=SUM(A1)") == f"\\x{ord(start):02x}=SUM(A1)"


def test_csv_cell_leaves_ordinary_text_alone() -> None:
    assert csv_cell("Roboto-Bold") == "Roboto-Bold"
