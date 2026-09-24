"""Shared test helpers: synthetic fonts and synthetic app bundles.

No binaries are committed for these; everything is built at test time with fontTools.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable, Mapping
from pathlib import Path

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTCollection, TTFont

from fontbom.inputs.walker import FileEntry

FIXTURES = Path(__file__).parent / "fixtures"


def make_font(
    *,
    family: str = "Test Sans",
    style: str = "Regular",
    postscript: str | None = None,
    full_name: str | None = None,
    copyright: str | None = "Copyright 2026 Test Foundry",
    license_text: str | None = None,
    license_url: str | None = None,
    designer: str | None = None,
    vendor_url: str | None = None,
    designer_url: str | None = None,
    trademark: str | None = None,
    manufacturer: str | None = None,
    typographic_family: str | None = None,
    typographic_style: str | None = None,
    fs_type: int = 0,
    vendor_id: str = "TEST",
    version: float = 1.0,
    flavor: str = "ttf",
    extra_names: Mapping[int, str] | None = None,
) -> bytes:
    """Build a minimal but valid font and return its bytes.

    flavor: "ttf", "otf", "woff", "woff2".
    """
    postscript = postscript or f"{family}-{style}".replace(" ", "")
    full_name = full_name or f"{family} {style}"
    is_cff = flavor == "otf"

    fb = FontBuilder(1000, isTTF=not is_cff)
    glyph_order = [".notdef", "space", "A"]
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap({0x20: "space", 0x41: "A"})
    advance_widths = {".notdef": 500, "space": 250, "A": 600}

    if is_cff:
        from fontTools.pens.t2CharStringPen import T2CharStringPen

        pen = T2CharStringPen(600, None)
        pen.moveTo((0, 0))
        pen.lineTo((0, 700))
        pen.lineTo((600, 700))
        pen.closePath()
        char_strings = {
            ".notdef": T2CharStringPen(500, None).getCharString(),
            "space": T2CharStringPen(250, None).getCharString(),
            "A": pen.getCharString(),
        }
        fb.setupCFF(postscript, {"FullName": full_name}, char_strings, {})
        metrics = {name: (advance_widths[name], 0) for name in glyph_order}
        fb.setupHorizontalMetrics(metrics)
    else:
        pen = TTGlyphPen(None)
        pen.moveTo((0, 0))
        pen.lineTo((0, 700))
        pen.lineTo((600, 700))
        pen.closePath()
        glyphs = {
            ".notdef": TTGlyphPen(None).glyph(),
            "space": TTGlyphPen(None).glyph(),
            "A": pen.glyph(),
        }
        fb.setupGlyf(glyphs)
        metrics = {name: (advance_widths[name], 0) for name in glyph_order}
        fb.setupHorizontalMetrics(metrics)

    fb.setupHorizontalHeader(ascent=800, descent=-200)
    name_strings: dict[str, str] = {
        "familyName": family,
        "styleName": style,
        "psName": postscript,
        "fullName": full_name,
        "uniqueFontIdentifier": f"{vendor_id};{postscript}",
        "version": f"Version {version:.3f}",
    }
    if copyright is not None:
        name_strings["copyright"] = copyright
    if license_text is not None:
        name_strings["licenseDescription"] = license_text
    if license_url is not None:
        name_strings["licenseInfoURL"] = license_url
    if designer is not None:
        name_strings["designer"] = designer
    if vendor_url is not None:
        name_strings["vendorURL"] = vendor_url
    if designer_url is not None:
        name_strings["designerURL"] = designer_url
    if trademark is not None:
        name_strings["trademark"] = trademark
    if manufacturer is not None:
        name_strings["manufacturer"] = manufacturer
    if typographic_family is not None:
        name_strings["typographicFamily"] = typographic_family
    if typographic_style is not None:
        name_strings["typographicSubfamily"] = typographic_style
    fb.setupNameTable(name_strings, mac=False)
    if extra_names:
        for name_id, text in extra_names.items():
            fb.font["name"].setName(text, name_id, 3, 1, 0x409)

    fb.setupOS2(fsType=fs_type, achVendID=vendor_id, sTypoAscender=800, usWinAscent=800)
    fb.setupPost()
    fb.font["head"].fontRevision = version

    if flavor in ("woff", "woff2"):
        fb.font.flavor = flavor

    buf = io.BytesIO()
    fb.save(buf)
    return buf.getvalue()


def make_collection(fonts: Iterable[bytes]) -> bytes:
    """Bundle several TrueType fonts into a .ttc."""
    collection = TTCollection()
    collection.fonts = [TTFont(io.BytesIO(data)) for data in fonts]
    buf = io.BytesIO()
    collection.save(buf)
    return buf.getvalue()


def write_zip(path: Path, members: Mapping[str, bytes]) -> Path:
    """Write a zip archive with the given member name -> bytes mapping."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return path


def write_tree(root: Path, files: Mapping[str, bytes | str]) -> Path:
    """Write a directory tree from a relative-path -> content mapping."""
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            target.write_text(content)
        else:
            target.write_bytes(content)
    return root


@pytest.fixture
def ttf_bytes() -> bytes:
    return make_font()


@pytest.fixture
def ofl_font_bytes() -> bytes:
    return make_font(
        family="Libre Test",
        license_text=(
            "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
            "This license is available with a FAQ at: https://openfontlicense.org"
        ),
        license_url="https://openfontlicense.org",
    )


def entry(root: Path, name: str, content: bytes | str, depth: int = 0) -> FileEntry:
    """Write ``content`` under ``root`` and return a FileEntry with ``name`` as logical path."""
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        target.write_text(content)
    else:
        target.write_bytes(content)
    return FileEntry(logical_path=name, real_path=target, size=target.stat().st_size, depth=depth)
