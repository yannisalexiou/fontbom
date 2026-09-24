"""Shared machinery for reference scanners."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import ClassVar, Protocol

from fontbom.inputs.walker import FileEntry
from fontbom.models import Confidence, Reference

MAX_TEXT_BYTES = 5 * 1024 * 1024
FONT_EXTENSION_GROUP = r"(?:ttf|otf|ttc|otc|woff2?)"


class Scanner(Protocol):
    ecosystem: ClassVar[str]

    def accepts(self, entry: FileEntry) -> bool: ...

    def scan(self, entry: FileEntry) -> Iterator[Reference]: ...


@dataclass(frozen=True)
class Pattern:
    kind: str
    regex: re.Pattern[str]
    build: Callable[[re.Match[str]], str] | None = None

    def name(self, match: re.Match[str]) -> str:
        return self.build(match) if self.build else match.group(1)


def read_text(entry: FileEntry) -> str | None:
    """Decode a source file, or return None when it is too large to be source."""
    if entry.size > MAX_TEXT_BYTES:
        return None
    return entry.read().decode("utf-8", errors="replace")


def line_of(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


class RegexScanner:
    """Scan text files with a fixed list of patterns. Subclasses set the class attributes."""

    ecosystem: ClassVar[str]
    extensions: ClassVar[frozenset[str]]
    patterns: ClassVar[tuple[Pattern, ...]]

    def accepts(self, entry: FileEntry) -> bool:
        return PurePosixPath(entry.logical_path).suffix.lower() in self.extensions

    def scan(self, entry: FileEntry) -> Iterator[Reference]:
        text = read_text(entry)
        if text is None:
            return
        yield from self.scan_text(text, entry.logical_path)

    def scan_text(self, text: str, source: str) -> Iterator[Reference]:
        yield from emit(self.patterns, text, source, self.ecosystem)


def emit(
    patterns: tuple[Pattern, ...], text: str, source: str, ecosystem: str, offset: int = 0
) -> Iterator[Reference]:
    """Apply patterns to ``text`` and yield one Reference per distinct (name, line)."""
    seen: set[tuple[str, int]] = set()
    for pattern in patterns:
        for match in pattern.regex.finditer(text):
            name = pattern.name(match).strip()
            if not name:
                continue
            line = line_of(text, match.start()) + offset
            if (name, line) in seen:
                continue
            seen.add((name, line))
            yield Reference(name, pattern.kind, ecosystem, source, line, Confidence.HIGH)
