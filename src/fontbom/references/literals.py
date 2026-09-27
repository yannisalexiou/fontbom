"""Quoted strings in source code that equal the name of a discovered font.

A font name is often kept in a constant and passed to `UIFont(name:)` or `Typeface` later, where
no call-site pattern can see it. After discovery the names are known, so a quoted string that
equals one of them after normalisation is a reference. Only discovered names are matched, so
this pass never reports a font as missing.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from pathlib import PurePosixPath

from fontbom.inputs.walker import FileEntry
from fontbom.models import Confidence, Reference
from fontbom.references.base import line_of, read_text
from fontbom.references.match import normalize

MIN_NAME_LENGTH = 4
# Plists and Interface Builder files have their own parsers in references.ios.
LEFT_TO_PARSERS = frozenset({".plist", ".storyboard", ".xib"})
# Strings are paired left to right with no minimum length, so a short string cannot pair its
# closing quote with the next string's opening quote.
QUOTED = re.compile(r"\"([^\"\n]*)\"|'([^'\n]*)'")


class LiteralScanner:
    """Find quoted strings that name a discovered font, in files a source scanner accepted."""

    def __init__(self, names: Iterable[str]) -> None:
        self.keys = {key for key in map(normalize, names) if len(key) >= MIN_NAME_LENGTH}

    def accepts(self, entry: FileEntry) -> bool:
        suffix = PurePosixPath(entry.logical_path).suffix.lower()
        return bool(self.keys) and suffix not in LEFT_TO_PARSERS

    def scan(self, entry: FileEntry, ecosystem: str) -> Iterator[Reference]:
        text = read_text(entry)
        if text is None:
            return
        for match in QUOTED.finditer(text):
            value = match.group(1) if match.group(1) is not None else match.group(2)
            # Normalising only removes characters, so shorter strings cannot match.
            if len(value) >= MIN_NAME_LENGTH and normalize(value) in self.keys:
                yield Reference(
                    value,
                    "string-literal",
                    ecosystem,
                    entry.logical_path,
                    line_of(text, match.start()),
                    Confidence.HIGH,
                )
