from __future__ import annotations

from pathlib import Path

from fontbom.references.literals import LiteralScanner
from tests.conftest import entry

KEYS = ["Brand Sans", "Brand Sans Bold", "BrandSans-Bold", "brand_sans_bold", "Abc"]


def names(refs: list) -> list[str]:  # type: ignore[type-arg]
    return sorted(r.name for r in refs)


def test_font_names_kept_in_constants_are_references(tmp_path: Path) -> None:
    swift = """
enum FontName: String {
    case bold = "BrandSans-Bold"
}
let family = "Brand Sans"
"""
    refs = list(LiteralScanner(KEYS).scan(entry(tmp_path, "Theme/Fonts.swift", swift), "ios"))
    assert names(refs) == ["Brand Sans", "BrandSans-Bold"]
    bold = next(r for r in refs if r.name == "BrandSans-Bold")
    assert bold.kind == "string-literal"
    assert bold.ecosystem == "ios"
    assert bold.line == 3
    assert bold.confidence == "high"


def test_names_match_after_normalising_case_and_separators(tmp_path: Path) -> None:
    kotlin = "private const val BOLD = \"brand-sans-BOLD\"\nval x = 'Brand_Sans'\n"
    refs = list(LiteralScanner(KEYS).scan(entry(tmp_path, "ui/Type.kt", kotlin), "android"))
    assert names(refs) == ["Brand_Sans", "brand-sans-BOLD"]


def test_strings_that_only_contain_a_font_name_are_ignored(tmp_path: Path) -> None:
    swift = 'let hint = "Brand Sans is our font"\nlet other = "Brand"\n'
    assert list(LiteralScanner(KEYS).scan(entry(tmp_path, "A.swift", swift), "ios")) == []


def test_short_font_names_are_ignored(tmp_path: Path) -> None:
    swift = 'let x = "Abc"\n'
    assert list(LiteralScanner(KEYS).scan(entry(tmp_path, "A.swift", swift), "ios")) == []


def test_plists_and_interface_builder_files_are_left_to_their_parsers(tmp_path: Path) -> None:
    scanner = LiteralScanner(KEYS)
    for name in ["Info.plist", "Main.storyboard", "Cell.xib"]:
        assert not scanner.accepts(entry(tmp_path, name, '"Brand Sans"')), name
    assert scanner.accepts(entry(tmp_path, "A.swift", ""))


def test_nothing_is_accepted_without_font_names(tmp_path: Path) -> None:
    assert not LiteralScanner([]).accepts(entry(tmp_path, "A.swift", '"Brand Sans"'))
