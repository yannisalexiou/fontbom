"""Web references: @font-face blocks and Google Fonts stylesheet URLs (parsed, never fetched)."""

from __future__ import annotations

import re
from collections.abc import Iterator
from urllib.parse import parse_qs, urlsplit

from fontbom.inputs.walker import FileEntry
from fontbom.models import Confidence, Reference
from fontbom.references.base import Pattern, RegexScanner, emit, line_of, read_text

FONT_FACE_BLOCK = re.compile(r"@font-face\s*\{([^}]*)\}", re.IGNORECASE)
GOOGLE_FONTS_URL = re.compile(r"https?://fonts\.googleapis\.com/[^\s\"'<>)]+", re.IGNORECASE)

FONT_FACE_PATTERNS: tuple[Pattern, ...] = (
    Pattern(
        "font-face",
        re.compile(r"font-family\s*:\s*(['\"]?)([^;'\"}]+?)\1\s*(?:;|$)", re.IGNORECASE | re.M),
        build=lambda m: m.group(2),
    ),
    Pattern(
        "font-face-src",
        re.compile(r"url\(\s*['\"]?((?!data:)[^'\")]+?)['\"]?\s*\)", re.IGNORECASE),
    ),
)


class WebScanner(RegexScanner):
    ecosystem = "web"
    extensions = frozenset({".css", ".scss", ".sass", ".less", ".html", ".htm"})
    patterns = ()

    def scan(self, entry: FileEntry) -> Iterator[Reference]:
        text = read_text(entry)
        if text is None:
            return
        source = entry.logical_path
        for block in FONT_FACE_BLOCK.finditer(text):
            offset = line_of(text, block.start(1)) - 1
            yield from emit(FONT_FACE_PATTERNS, block.group(1), source, "web", offset=offset)
        for url in GOOGLE_FONTS_URL.finditer(text):
            line = line_of(text, url.start())
            for family in google_fonts_families(url.group(0)):
                yield Reference(family, "google-fonts-url", "web", source, line, Confidence.HIGH)


def google_fonts_families(url: str) -> list[str]:
    """Extract family names from a Google Fonts CSS URL without any network access."""
    query = parse_qs(urlsplit(url.replace("&amp;", "&")).query, keep_blank_values=False)
    families: list[str] = []
    for value in query.get("family", []):
        for part in value.split("|"):
            name = part.split(":", 1)[0].strip()
            if name and name not in families:
                families.append(name)
    return families
