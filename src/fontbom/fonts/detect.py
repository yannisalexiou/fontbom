"""Detect font files by extension or by magic bytes."""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath


class FontFormat(StrEnum):
    TRUETYPE = "truetype"
    OPENTYPE_CFF = "opentype-cff"
    COLLECTION = "collection"
    WOFF = "woff"
    WOFF2 = "woff2"


FONT_EXTENSIONS: dict[str, FontFormat] = {
    ".ttf": FontFormat.TRUETYPE,
    ".otf": FontFormat.OPENTYPE_CFF,
    ".ttc": FontFormat.COLLECTION,
    ".otc": FontFormat.COLLECTION,
    ".woff": FontFormat.WOFF,
    ".woff2": FontFormat.WOFF2,
}

MAGIC: dict[bytes, FontFormat] = {
    b"\x00\x01\x00\x00": FontFormat.TRUETYPE,
    b"true": FontFormat.TRUETYPE,
    b"OTTO": FontFormat.OPENTYPE_CFF,
    b"ttcf": FontFormat.COLLECTION,
    b"wOFF": FontFormat.WOFF,
    b"wOF2": FontFormat.WOFF2,
}

HEADER_LENGTH = 4


def detect(name: str, header: bytes) -> FontFormat | None:
    """Return the font format for a file, or None if it is not a font.

    ``name`` is the file's path or logical path; ``header`` is at least the first four bytes.
    Extension wins so that files claiming to be fonts are always inspected downstream.
    """
    by_extension = FONT_EXTENSIONS.get(PurePosixPath(name).suffix.lower())
    if by_extension is not None:
        return by_extension
    return MAGIC.get(header[:HEADER_LENGTH])
