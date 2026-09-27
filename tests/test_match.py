from __future__ import annotations

import hashlib
import time

from fontbom.fonts.detect import FontFormat
from fontbom.fonts.metadata import read_faces
from fontbom.models import Confidence, FontRecord, Reference
from fontbom.references.match import link, normalize
from tests.conftest import make_font


def ref(name: str, ecosystem: str = "ios", kind: str = "uifont") -> Reference:
    return Reference(name, kind, ecosystem, "src/a.swift", 1, Confidence.HIGH)


def record(path: str, **kwargs: object) -> FontRecord:
    data = make_font(**kwargs)  # type: ignore[arg-type]
    return FontRecord(
        hashlib.sha256(data).hexdigest(),
        len(data),
        FontFormat.TRUETYPE,
        [path],
        read_faces(data, FontFormat.TRUETYPE),
    )


def test_normalize_ignores_case_separators_extensions_and_directories() -> None:
    assert normalize("Roboto-Bold") == "robotobold"
    assert normalize("roboto_bold") == "robotobold"
    assert normalize("Roboto Bold") == "robotobold"
    assert normalize("fonts/Roboto-Bold.ttf") == "robotobold"
    assert normalize("@font/roboto_bold") == "robotobold"
    assert normalize("../assets/Roboto-Bold.woff2") == "robotobold"


def test_matches_on_family_full_postscript_typographic_and_file_stem() -> None:
    rec = record(
        "fonts/rb.ttf",
        family="Roboto",
        style="Bold",
        postscript="Roboto-Bold",
        typographic_family="Roboto Display",
    )
    refs = [
        ref("Roboto"),
        ref("Roboto Bold"),
        ref("Roboto-Bold"),
        ref("Roboto Display"),
        ref("rb.ttf", "ios", "uiappfonts"),
        ref("Other"),
    ]
    unbundled = link([rec], refs)
    assert [r.name for r in rec.references] == [
        "Roboto",
        "Roboto Bold",
        "Roboto-Bold",
        "Roboto Display",
        "rb.ttf",
    ]
    assert rec.referenced is True
    assert [r.name for r in unbundled] == ["Other"]


def test_unreferenced_font_has_no_references() -> None:
    rec = record("fonts/x.ttf", family="Lonely")
    assert link([rec], [ref("Someone Else")]) == [ref("Someone Else")]
    assert rec.references == []
    assert rec.referenced is False


def test_system_and_generic_font_names_are_not_reported_as_unbundled() -> None:
    refs = [
        ref("System"),
        ref("Helvetica Neue"),
        ref("sans-serif-medium", "android", "font-family-attr"),
        ref("monospace", "web", "font-face"),
        ref("Roboto", "android", "font-family-attr"),
        ref("Custom Face"),
    ]
    assert [r.name for r in link([], refs)] == ["Custom Face"]


def test_unbundled_references_are_deduplicated_and_sorted() -> None:
    refs = [ref("Zeta"), ref("Alpha"), ref("Zeta")]
    assert [r.name for r in link([], refs)] == ["Alpha", "Zeta"]


def test_same_reference_is_attached_once() -> None:
    rec = record("fonts/x.ttf", family="Dup")
    link([rec], [ref("Dup"), ref("Dup")])
    assert len(rec.references) == 1


def test_linking_thousands_of_references_to_one_font_stays_fast() -> None:
    # A storyboard-heavy app links thousands of references to each font. Removing duplicates
    # with a list lookup made this quadratic: seconds here, half the scan time in real apps.
    rec = record("fonts/x.ttf", family="Busy")
    refs = [
        Reference("Busy", "storyboard", "ios", f"View{i}.xib", 1, Confidence.HIGH)
        for i in range(5_000)
    ]
    start = time.perf_counter()
    link([rec], refs + refs)
    assert time.perf_counter() - start < 1.0
    assert len(rec.references) == 5_000


def test_common_web_and_platform_font_stacks_are_not_reported_as_unbundled() -> None:
    stack = [
        "-apple-system", "BlinkMacSystemFont", "Segoe UI", "system-ui", "ui-sans-serif",
        "ui-monospace", "SFMono-Regular", "Consolas", "Liberation Mono", "Apple Color Emoji",
        "Segoe UI Emoji", "Noto Color Emoji", "Cantarell", "Oxygen", "Liberation Sans",
    ]  # fmt: skip
    refs = [ref(name, "web", "font-face") for name in stack] + [ref("Custom Face", "web")]
    assert [r.name for r in link([], refs)] == ["Custom Face"]


def test_file_name_with_spaces_links_to_bundled_font() -> None:
    rec = record("fonts/Example Sans Bold.ttf", family="Example Sans", style="Bold")
    literal = ref("fonts/Example Sans Bold.ttf", "android", "font-file-literal")
    assert link([rec], [literal]) == []
    assert rec.references == [literal]


def test_unmatched_quoted_string_with_spaces_is_not_reported_as_missing() -> None:
    # Quoted strings ending in .ttf that contain spaces are often messages, not file names.
    message = ref("Could not load Brand.ttf", "ios", "font-file-literal")
    missing_file = ref("fonts/Brand-Bold.ttf", "ios", "font-file-literal")
    missing_plist_entry = ref("Brand Bold.ttf", "ios", "uiappfonts")
    assert [r.name for r in link([], [message, missing_file, missing_plist_entry])] == [
        "Brand Bold.ttf",
        "fonts/Brand-Bold.ttf",
    ]


def test_unmatched_xml_text_with_spaces_is_not_reported_as_missing() -> None:
    message = ref("Download Brand.ttf", "android", "font-file-text")
    missing = ref("fonts/Brand-Bold.ttf", "android", "font-file-text")
    assert [r.name for r in link([], [message, missing])] == ["fonts/Brand-Bold.ttf"]


def test_ios_built_in_fonts_are_not_reported_as_unbundled() -> None:
    refs = [
        ref("HelveticaNeue-Bold", kind="storyboard"),
        ref("Avenir Next", kind="storyboard"),
        ref("AvenirNext-DemiBoldItalic"),
        ref("Arial-BoldMT"),
        ref("TimesNewRomanPSMT"),
        ref("Georgia-Italic", "web", "font-face"),
        ref(".AppleSystemUIFont", kind="storyboard"),
        ref(".SFUI-Semibold"),
        # Commercial families whose names start with a built-in family are still reported.
        ref("Futura PT"),
        ref("FuturaPT-Book"),
        ref("Avenir Next LT Pro"),
    ]
    assert [r.name for r in link([], refs)] == ["Avenir Next LT Pro", "Futura PT", "FuturaPT-Book"]


def test_ios_built_in_families_are_still_missing_on_android() -> None:
    missing = ref("Avenir Next", "android", "font-family-attr")
    assert link([], [missing]) == [missing]
