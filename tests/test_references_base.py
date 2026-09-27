from __future__ import annotations

from pathlib import Path

import pytest

from fontbom.references.base import read_source
from fontbom.references.ios import IOSScanner
from tests.conftest import entry


def test_source_that_cannot_name_a_font_is_not_decoded(tmp_path: Path) -> None:
    header = "#import <Foundation/Foundation.h>\n@interface Cache : NSObject\n@end\n"
    assert read_source(entry(tmp_path, "Sources/Cache.h", header)) is None


@pytest.mark.parametrize(
    "line",
    [
        'label.font = UIFont(name: "Inter-Medium", size: 12)',
        'let path = "Fonts/Inter.TTF"',
        "val tf = Typeface.createFromAsset(assets, name)",
    ],
)
def test_source_with_a_font_marker_is_decoded(tmp_path: Path, line: str) -> None:
    assert read_source(entry(tmp_path, "Sources/A.swift", line)) == line


@pytest.mark.parametrize(
    ("swift", "expected"),
    [
        ('let title: Headline = .custom("Inter-Medium", size: 12)', "Inter-Medium"),
        (
            'let url = Bundle.module.url(forResource: "Inter-Bold", withExtension: "ttf")',
            "Inter-Bold.ttf",
        ),
    ],
)
def test_references_without_the_word_font_are_still_found(
    tmp_path: Path, swift: str, expected: str
) -> None:
    refs = list(IOSScanner().scan(entry(tmp_path, "Sources/Theme.swift", swift)))
    assert [r.name for r in refs] == [expected]
