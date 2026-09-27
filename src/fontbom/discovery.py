"""Turn a stream of files into deduplicated font records."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import PurePosixPath

from fontbom.fonts.detect import FONT_EXTENSIONS, detect
from fontbom.fonts.metadata import read_faces
from fontbom.inputs.walker import FileEntry
from fontbom.models import FontRecord


def discover_fonts(entries: Iterable[FileEntry]) -> list[FontRecord]:
    """Detect fonts among ``entries``, parse each distinct file once, and aggregate paths.

    A file named like a font is always reported, with errors if it does not parse. A file found
    only by its magic bytes is reported only if it parses, because caches, models and text files
    can start with the same bytes.
    """
    by_hash: dict[str, FontRecord] = {}
    not_fonts: set[str] = set()
    for entry in entries:
        fmt = detect(entry.logical_path, entry.header)
        if fmt is None:
            continue
        data = entry.read()
        digest = hashlib.sha256(data).hexdigest()
        named_as_font = PurePosixPath(entry.logical_path).suffix.lower() in FONT_EXTENSIONS
        if digest in not_fonts and not named_as_font:
            continue
        record = by_hash.get(digest)
        if record is None:
            faces = read_faces(data, fmt)
            if not named_as_font and all(face.errors for face in faces):
                not_fonts.add(digest)
                continue
            record = FontRecord(
                sha256=digest,
                size=len(data),
                format=fmt,
                paths=[],
                faces=faces,
            )
            by_hash[digest] = record
        record.paths.append(entry.logical_path)
    records = list(by_hash.values())
    for record in records:
        record.paths.sort()
    records.sort(key=lambda r: r.paths[0])
    return records
