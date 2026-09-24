from __future__ import annotations

import hashlib

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


def test_common_web_and_platform_font_stacks_are_not_reported_as_unbundled() -> None:
    stack = [
        "-apple-system", "BlinkMacSystemFont", "Segoe UI", "system-ui", "ui-sans-serif",
        "ui-monospace", "SFMono-Regular", "Consolas", "Liberation Mono", "Apple Color Emoji",
        "Segoe UI Emoji", "Noto Color Emoji", "Cantarell", "Oxygen", "Liberation Sans",
    ]  # fmt: skip
    refs = [ref(name, "web", "font-face") for name in stack] + [ref("Custom Face", "web")]
    assert [r.name for r in link([], refs)] == ["Custom Face"]
