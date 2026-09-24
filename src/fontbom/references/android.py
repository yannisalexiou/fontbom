"""Android references: font resources, XML attributes, Typeface and Compose APIs."""

from __future__ import annotations

import re

from fontbom.references.base import FONT_EXTENSION_GROUP, Pattern, RegexScanner


class AndroidScanner(RegexScanner):
    ecosystem = "android"
    extensions = frozenset({".kt", ".java", ".xml"})
    patterns = (
        Pattern("font-resource", re.compile(r"@font/([A-Za-z0-9_.]+)")),
        Pattern("font-resource", re.compile(r"\bR\.font\.([A-Za-z0-9_]+)")),
        Pattern("font-family-attr", re.compile(r"(?:android|app):fontFamily=\"([^\"@][^\"]*)\"")),
        Pattern("typeface-asset", re.compile(r"createFromAsset\([^,()]+,\s*\"([^\"]+)\"")),
        Pattern(
            "font-file-literal",
            re.compile(rf"\"([^\"\s]+\.{FONT_EXTENSION_GROUP})\"", re.IGNORECASE),
        ),
    )
