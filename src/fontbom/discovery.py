"""Turn a stream of files into deduplicated font records."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from fontbom.fonts.detect import detect
from fontbom.fonts.metadata import read_faces
from fontbom.inputs.walker import FileEntry
from fontbom.models import FontRecord


def discover_fonts(entries: Iterable[FileEntry]) -> list[FontRecord]:
    """Detect fonts among ``entries``, parse each distinct file once, and aggregate paths."""
    by_hash: dict[str, FontRecord] = {}
    for entry in entries:
        fmt = detect(entry.logical_path, entry.header)
        if fmt is None:
            continue
        data = entry.read()
        digest = hashlib.sha256(data).hexdigest()
        record = by_hash.get(digest)
        if record is None:
            record = FontRecord(
                sha256=digest,
                size=len(data),
                format=fmt,
                paths=[],
                faces=read_faces(data, fmt),
            )
            by_hash[digest] = record
        record.paths.append(entry.logical_path)
    records = list(by_hash.values())
    for record in records:
        record.paths.sort()
    records.sort(key=lambda r: r.paths[0])
    return records
