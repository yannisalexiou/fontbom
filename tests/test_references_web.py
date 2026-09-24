from __future__ import annotations

from pathlib import Path

from fontbom.references.web import WebScanner, google_fonts_families
from tests.conftest import entry

CSS = """
@font-face {
  font-family: "Inter";
  src: url("../fonts/Inter-Regular.woff2") format("woff2"),
       url(../fonts/Inter-Regular.woff) format("woff");
}
@font-face { font-family: Lora; src: url('fonts/Lora-Italic.ttf'); }
body { font-family: Inter, sans-serif; }
"""

HTML = """<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&family=Open+Sans&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css?family=Lato:400,700|Source+Sans+Pro" rel="stylesheet">"""


def names(refs: list) -> list[str]:  # type: ignore[type-arg]
    return sorted(r.name for r in refs)


def test_font_face_blocks(tmp_path: Path) -> None:
    refs = list(WebScanner().scan(entry(tmp_path, "css/app.css", CSS)))
    assert names(refs) == [
        "../fonts/Inter-Regular.woff",
        "../fonts/Inter-Regular.woff2",
        "Inter",
        "Lora",
        "fonts/Lora-Italic.ttf",
    ]
    inter = next(r for r in refs if r.name == "Inter")
    assert inter.kind == "font-face"
    assert inter.ecosystem == "web"
    assert inter.line == 3
    assert next(r for r in refs if r.name.endswith(".woff2")).kind == "font-face-src"


def test_google_fonts_urls_are_parsed_never_fetched(tmp_path: Path) -> None:
    refs = list(WebScanner().scan(entry(tmp_path, "index.html", HTML)))
    assert names(refs) == ["Lato", "Open Sans", "Roboto", "Source Sans Pro"]
    assert {r.kind for r in refs} == {"google-fonts-url"}


def test_google_fonts_family_parser() -> None:
    assert google_fonts_families(
        "https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&family=Open+Sans"
    ) == ["Roboto", "Open Sans"]
    assert google_fonts_families(
        "https://fonts.googleapis.com/css?family=Lato:400,700|Source+Sans+Pro:300"
    ) == ["Lato", "Source Sans Pro"]
    assert google_fonts_families("https://fonts.googleapis.com/icon?family=Material+Icons") == [
        "Material Icons"
    ]


def test_accepts_web_files(tmp_path: Path) -> None:
    scanner = WebScanner()
    for name in ["a.css", "a.scss", "a.less", "a.html", "a.htm"]:
        assert scanner.accepts(entry(tmp_path, name, "")), name
    assert not scanner.accepts(entry(tmp_path, "a.js", ""))
