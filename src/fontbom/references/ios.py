"""iOS and macOS references: UIKit, SwiftUI, Info.plist, Core Text, storyboards."""

from __future__ import annotations

import plistlib
import re
from collections.abc import Iterator
from pathlib import PurePosixPath

from fontbom.inputs.walker import FileEntry
from fontbom.models import Confidence, Reference
from fontbom.references.base import (
    FONT_EXTENSION_GROUP,
    Pattern,
    RegexScanner,
    emit,
    read_text,
)

SOURCE_EXTENSIONS = frozenset({".swift", ".m", ".mm", ".h"})
PLIST_EXTENSIONS = frozenset({".plist"})
INTERFACE_EXTENSIONS = frozenset({".storyboard", ".xib"})

SOURCE_PATTERNS: tuple[Pattern, ...] = (
    Pattern("uifont", re.compile(r"\b(?:UI|NS)Font(?:\.init)?\(\s*name:\s*\"([^\"]+)\"")),
    Pattern("uifont", re.compile(r"fontWithName:\s*@\"([^\"]+)\"")),
    Pattern("swiftui-font-custom", re.compile(r"\bFont\.custom\(\s*\"([^\"]+)\"")),
    Pattern(
        "swiftui-font-custom",
        re.compile(r"\.custom\(\s*\"([^\"]+)\"\s*,\s*(?:size|fixedSize)\s*:"),
    ),
    Pattern(
        "bundle-resource",
        re.compile(
            rf"forResource:\s*\"([^\"]+)\"\s*,\s*withExtension:\s*\"({FONT_EXTENSION_GROUP})\"",
            re.IGNORECASE,
        ),
        build=lambda m: f"{m.group(1)}.{m.group(2)}",
    ),
    Pattern(
        "font-file-literal",
        re.compile(rf"\"([^\"\s]+\.{FONT_EXTENSION_GROUP})\"", re.IGNORECASE),
    ),
)

FONT_DESCRIPTION = re.compile(r"<fontDescription\b[^>]*>")
INTERFACE_PATTERNS: tuple[Pattern, ...] = (
    Pattern("storyboard", re.compile(r"\bname=\"([^\"]+)\"")),
    Pattern("storyboard", re.compile(r"\bfamily=\"([^\"]+)\"")),
)


class IOSScanner(RegexScanner):
    ecosystem = "ios"
    extensions = SOURCE_EXTENSIONS | PLIST_EXTENSIONS | INTERFACE_EXTENSIONS
    patterns = SOURCE_PATTERNS

    def scan(self, entry: FileEntry) -> Iterator[Reference]:
        suffix = PurePosixPath(entry.logical_path).suffix.lower()
        if suffix in PLIST_EXTENSIONS:
            yield from _scan_plist(entry)
        elif suffix in INTERFACE_EXTENSIONS:
            yield from _scan_interface(entry)
        else:
            yield from super().scan(entry)


def _scan_plist(entry: FileEntry) -> Iterator[Reference]:
    try:
        data = plistlib.loads(entry.read())
    except Exception:  # plistlib raises several unrelated exception types on bad input
        return
    if not isinstance(data, dict):
        return
    fonts = data.get("UIAppFonts")
    if not isinstance(fonts, list):
        return
    for item in fonts:
        if isinstance(item, str) and item.strip():
            yield Reference(
                item.strip(), "uiappfonts", "ios", entry.logical_path, None, Confidence.HIGH
            )


def _scan_interface(entry: FileEntry) -> Iterator[Reference]:
    text = read_text(entry)
    if text is None:
        return
    for tag in FONT_DESCRIPTION.finditer(text):
        line = text.count("\n", 0, tag.start())
        yield from emit(INTERFACE_PATTERNS, tag.group(0), entry.logical_path, "ios", offset=line)
