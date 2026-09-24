"""Extract name, OS/2 and head metadata from font bytes with fontTools."""

from __future__ import annotations

import io
import logging
from collections.abc import Iterable
from typing import Any

from fontTools.ttLib import TTCollection, TTFont, TTLibError

from fontbom.fonts.detect import FontFormat
from fontbom.models import Embedding, FontFace

log = logging.getLogger(__name__)

NAME_IDS: tuple[int, ...] = (0, 1, 2, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 16, 17)

FS_RESTRICTED = 0x0002
FS_PREVIEW_PRINT = 0x0004
FS_EDITABLE = 0x0008
FS_NO_SUBSETTING = 0x0100
FS_BITMAP_ONLY = 0x0200


def decode_embedding(fs_type: int) -> Embedding:
    """Decode bits 0-3 of fsType. The least restrictive set bit wins (OpenType spec)."""
    if fs_type & FS_EDITABLE:
        return Embedding.EDITABLE
    if fs_type & FS_PREVIEW_PRINT:
        return Embedding.PREVIEW_PRINT
    if fs_type & FS_RESTRICTED:
        return Embedding.RESTRICTED
    return Embedding.INSTALLABLE


def read_faces(data: bytes, fmt: FontFormat) -> list[FontFace]:
    """Parse ``data`` and return one FontFace per face.

    Never raises for bad input: a face with an ``errors`` entry is returned instead.
    """
    try:
        if fmt is FontFormat.COLLECTION:
            collection = TTCollection(io.BytesIO(data), lazy=True)
            fonts: Iterable[TTFont] = collection.fonts
        else:
            fonts = [TTFont(io.BytesIO(data), lazy=True)]
        return [_read_face(font, index, fmt) for index, font in enumerate(fonts)]
    except (TTLibError, ValueError, KeyError, IndexError, AssertionError, EOFError) as exc:
        return [FontFace(index=0, format=fmt, errors=[f"parse error: {exc}"])]


def _read_face(font: TTFont, index: int, fmt: FontFormat) -> FontFace:
    face = FontFace(index=index, format=fmt)
    try:
        face.names = _read_names(font)
    except Exception as exc:
        face.errors.append(f"name table error: {exc}")
    try:
        if "OS/2" in font:
            os2 = font["OS/2"]
            face.fs_type = int(os2.fsType)
            face.embedding = decode_embedding(face.fs_type)
            face.no_subsetting = bool(face.fs_type & FS_NO_SUBSETTING)
            face.bitmap_only = bool(face.fs_type & FS_BITMAP_ONLY)
            vendor = os2.achVendID
            face.vendor_id = (vendor.strip("\x00 ") or None) if vendor else None
    except Exception as exc:
        face.errors.append(f"OS/2 table error: {exc}")
    try:
        if "head" in font:
            face.version = f"{float(font['head'].fontRevision):.3f}"
    except Exception as exc:
        face.errors.append(f"head table error: {exc}")
    return face


def _read_names(font: TTFont) -> dict[int, str]:
    if "name" not in font:
        return {}
    table = font["name"]
    names: dict[int, str] = {}
    for name_id in NAME_IDS:
        record = _best_record(table, name_id)
        if record is None:
            continue
        try:
            text = record.toUnicode()
        except UnicodeDecodeError:
            continue
        if text:
            names[name_id] = text
    return names


def _best_record(table: Any, name_id: int) -> Any | None:
    """Prefer Windows English, then any Windows record, then any Mac record."""
    records = [r for r in table.names if r.nameID == name_id]
    if not records:
        return None
    for platform, lang in ((3, 0x409), (3, None), (1, 0), (1, None)):
        for r in records:
            if r.platformID == platform and (lang is None or r.langID == lang):
                return r
    return records[0]
