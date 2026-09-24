"""Orchestrate one scan: walk, discover, classify, cross-reference."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from fontbom import __version__
from fontbom.discovery import discover_fonts
from fontbom.inputs.limits import Limits
from fontbom.inputs.walker import FileEntry, walk
from fontbom.licenses.adjacent import AdjacentFile, find_adjacent, is_license_filename
from fontbom.licenses.classify import classify
from fontbom.models import FontRecord, Reference, ScanResult
from fontbom.references.android import AndroidScanner
from fontbom.references.base import Scanner
from fontbom.references.binary import scan_binaries
from fontbom.references.flutter import FlutterScanner
from fontbom.references.ios import IOSScanner
from fontbom.references.match import NAME_IDS_FOR_MATCHING, link
from fontbom.references.react_native import ReactNativeScanner
from fontbom.references.web import WebScanner

MAX_LICENSE_FILE_BYTES = 1024 * 1024


def default_jobs() -> int:
    return os.cpu_count() or 1


@dataclass(frozen=True)
class ScanOptions:
    limits: Limits = field(default_factory=Limits)
    references: bool = True
    jobs: int = field(default_factory=default_jobs)


@dataclass(frozen=True)
class Progress:
    """One progress event. ``phase`` is walking, classifying, referencing or done."""

    phase: str
    files: int
    fonts: int
    current: str = ""


ProgressCallback = Callable[[Progress], None]


def source_scanners() -> list[Scanner]:
    return [IOSScanner(), AndroidScanner(), FlutterScanner(), ReactNativeScanner(), WebScanner()]


def scan(
    path: Path, options: ScanOptions, on_progress: ProgressCallback | None = None
) -> ScanResult:
    """Scan ``path`` and return the result. Archive extraction is cleaned up before returning.

    ``on_progress`` is called once per file walked and once per phase change.
    """
    scanned_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = on_progress or (lambda _: None)
    with tempfile.TemporaryDirectory(prefix="fontbom-") as workdir:
        entries: list[FileEntry] = []
        for entry in walk(path, options.limits, Path(workdir)):
            entries.append(entry)
            report(Progress("walking", len(entries), 0, entry.logical_path))
        records = discover_fonts(entries)
        report(Progress("classifying", len(entries), len(records)))
        _classify_all(records, entries)
        unbundled: list[Reference] = []
        if options.references:
            report(Progress("referencing", len(entries), len(records)))
            unbundled = _cross_reference(
                records,
                entries,
                lambda current: report(
                    Progress("referencing", len(entries), len(records), current)
                ),
                options.jobs,
            )
        report(Progress("done", len(entries), len(records)))
    return ScanResult(
        tool=f"fontbom {__version__}",
        scanned_at=scanned_at,
        input=str(path),
        fonts=records,
        unbundled_references=unbundled,
    )


def _classify_all(records: list[FontRecord], entries: list[FileEntry]) -> None:
    license_files = {
        entry.logical_path: entry
        for entry in entries
        if is_license_filename(PurePosixPath(entry.logical_path).name)
        and entry.size <= MAX_LICENSE_FILE_BYTES
    }
    texts: dict[str, str] = {}
    for record in records:
        adjacent: list[AdjacentFile] = []
        for font_path in record.paths:
            for license_path, distance in find_adjacent(font_path, license_files):
                if license_path not in texts:
                    texts[license_path] = (
                        license_files[license_path].read().decode("utf-8", errors="replace")
                    )
                adjacent.append(AdjacentFile(license_path, distance, texts[license_path]))
        record.license = classify(record, adjacent)


def _cross_reference(
    records: list[FontRecord],
    entries: list[FileEntry],
    on_file: Callable[[str], None],
    jobs: int,
) -> list[Reference]:
    references: list[Reference] = []
    scanners = source_scanners()
    for entry in entries:
        on_file(entry.logical_path)
        for scanner in scanners:
            if scanner.accepts(entry):
                references.extend(scanner.scan(entry))
    names = {
        face.names[name_id]
        for record in records
        for face in record.faces
        for name_id in NAME_IDS_FOR_MATCHING
        if name_id in face.names
    }
    references.extend(scan_binaries(entries, names, jobs=jobs, on_file=on_file))
    return link(records, references)
