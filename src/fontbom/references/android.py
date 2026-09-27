"""Android references: font resources, XML attributes, Typeface and Compose APIs."""

from __future__ import annotations

import re

from fontbom.references.base import FONT_EXTENSION_GROUP, FONT_FILE_LITERAL, Pattern, RegexScanner


class AndroidScanner(RegexScanner):
    ecosystem = "android"
    extensions = frozenset({".kt", ".java", ".xml"})
    patterns = (
        Pattern("font-resource", re.compile(r"@font/([A-Za-z0-9_.]+)")),
        Pattern("font-resource", re.compile(r"\bR\.font\.([A-Za-z0-9_]+)")),
        Pattern("font-family-attr", re.compile(r"(?:android|app):fontFamily=\"([^\"@][^\"]*)\"")),
        Pattern("typeface-asset", re.compile(r"createFromAsset\([^,()]+,\s*\"([^\"]+)\"")),
        FONT_FILE_LITERAL,
        # A font file path as an XML text value, the Calligraphy library's style form:
        # <item name="fontPath">fonts/X.ttf</item>
        Pattern(
            "font-file-text",
            re.compile(rf">\s*([^<>\"\n]+\.{FONT_EXTENSION_GROUP})\s*<", re.IGNORECASE),
        ),
    )
