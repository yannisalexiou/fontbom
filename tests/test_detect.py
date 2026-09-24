from __future__ import annotations

import pytest

from fontbom.fonts.detect import FontFormat, detect
from tests.conftest import make_collection, make_font


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Foo.ttf", FontFormat.TRUETYPE),
        ("Foo.TTF", FontFormat.TRUETYPE),
        ("Foo.otf", FontFormat.OPENTYPE_CFF),
        ("Foo.ttc", FontFormat.COLLECTION),
        ("Foo.otc", FontFormat.COLLECTION),
        ("Foo.woff", FontFormat.WOFF),
        ("Foo.woff2", FontFormat.WOFF2),
    ],
)
def test_detects_by_extension_without_reading_header(name: str, expected: FontFormat) -> None:
    assert detect(name, b"") == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (make_font(flavor="ttf"), FontFormat.TRUETYPE),
        (make_font(flavor="otf"), FontFormat.OPENTYPE_CFF),
        (make_font(flavor="woff"), FontFormat.WOFF),
        (make_font(flavor="woff2"), FontFormat.WOFF2),
        (make_collection([make_font(family="A"), make_font(family="B")]), FontFormat.COLLECTION),
        (b"true\x00\x00\x00\x01", FontFormat.TRUETYPE),
    ],
)
def test_detects_renamed_font_by_magic_bytes(data: bytes, expected: FontFormat) -> None:
    assert detect("assets/data.bin", data[:4]) == expected


def test_extensionless_file_with_magic_is_detected() -> None:
    assert detect("Payload/App.app/fontdata", b"OTTO") == FontFormat.OPENTYPE_CFF


@pytest.mark.parametrize("data", [b"", b"PK\x03\x04", b"\x89PNG", b"<?xm", b"\x00\x00\x00\x00"])
def test_non_font_bytes_without_font_extension_are_ignored(data: bytes) -> None:
    assert detect("assets/image.png", data) is None


def test_font_extension_wins_over_mismatched_magic() -> None:
    # Files that claim to be fonts are still passed on; metadata extraction records the error.
    assert detect("Broken.ttf", b"PK\x03\x04") == FontFormat.TRUETYPE
