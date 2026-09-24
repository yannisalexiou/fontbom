"""Flutter references: the pubspec.yaml fonts section and Dart TextStyle fontFamily."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import PurePosixPath

from fontbom.inputs.walker import FileEntry
from fontbom.models import Confidence, Reference
from fontbom.references.base import (
    FONT_EXTENSION_GROUP,
    Pattern,
    RegexScanner,
    read_text,
    strip_quotes,
)

PUBSPEC_NAMES = frozenset({"pubspec.yaml", "pubspec.yml"})

# pubspec.yaml is read line by line so no YAML dependency is needed.
PUBSPEC_LINE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("pubspec-family", re.compile(r"^\s*-?\s*family:\s*(.+?)\s*$")),
    ("pubspec-asset", re.compile(r"^\s*-?\s*asset:\s*(.+?)\s*$")),
    ("pubspec-asset", re.compile(rf"^\s*-\s*(\S+\.{FONT_EXTENSION_GROUP})\s*$", re.IGNORECASE)),
)


class FlutterScanner(RegexScanner):
    ecosystem = "flutter"
    extensions = frozenset({".dart"})
    patterns = (Pattern("dart-fontfamily", re.compile(r"fontFamily:\s*['\"]([^'\"]+)['\"]")),)

    def accepts(self, entry: FileEntry) -> bool:
        return _is_pubspec(entry) or super().accepts(entry)

    def scan(self, entry: FileEntry) -> Iterator[Reference]:
        if _is_pubspec(entry):
            yield from _scan_pubspec(entry)
        else:
            yield from super().scan(entry)


def _is_pubspec(entry: FileEntry) -> bool:
    return PurePosixPath(entry.logical_path).name.lower() in PUBSPEC_NAMES


def _scan_pubspec(entry: FileEntry) -> Iterator[Reference]:
    text = read_text(entry)
    if text is None:
        return
    for number, line in enumerate(text.splitlines(), start=1):
        for kind, regex in PUBSPEC_LINE_PATTERNS:
            match = regex.match(line)
            if match:
                name = strip_quotes(match.group(1))
                if name:
                    yield Reference(
                        name, kind, "flutter", entry.logical_path, number, Confidence.HIGH
                    )
                break
