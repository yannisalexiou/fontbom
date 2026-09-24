"""React Native references: font file imports and fontFamily style values."""

from __future__ import annotations

import re

from fontbom.references.base import FONT_EXTENSION_GROUP, Pattern, RegexScanner


class ReactNativeScanner(RegexScanner):
    ecosystem = "react-native"
    extensions = frozenset({".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"})
    patterns = (
        Pattern(
            "font-file-import",
            re.compile(
                rf"require\(\s*['\"]([^'\"]+\.{FONT_EXTENSION_GROUP})['\"]\s*\)", re.IGNORECASE
            ),
        ),
        Pattern(
            "font-file-import",
            re.compile(rf"\bfrom\s+['\"]([^'\"]+\.{FONT_EXTENSION_GROUP})['\"]", re.IGNORECASE),
        ),
        Pattern("fontfamily-style", re.compile(r"fontFamily:\s*['\"]([^'\"]+)['\"]")),
    )
