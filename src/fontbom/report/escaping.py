"""Neutralise untrusted text before it enters a report.

Font names, paths and reference names come from the scanned files, so a crafted font can put
anything in them. JSON needs nothing: json.dumps escapes control characters. The other formats
each have their own hazard: formulas in CSV, HTML, links and code-span breakouts in Markdown,
and escape sequences on a terminal.
"""

from __future__ import annotations

import re
from dataclasses import fields, is_dataclass, replace
from enum import Enum
from typing import Any, TypeVar

T = TypeVar("T")

# C0 controls, DEL and C1 controls. ESC starts terminal sequences; 0x9b is the one-byte CSI.
CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
LINE_BREAK = re.compile(r"\r\n|[\r\n]")
# Cells a spreadsheet would evaluate as a formula (OWASP CSV injection guidance). Tab and carriage
# return are on that list too; csv_cell shows them as \x09 and \x0d first, so they never lead.
FORMULA_START = ("=", "+", "-", "@")
MARKDOWN_ESCAPES = re.compile(r"([\\`\[\]|])")
BACKTICK_RUN = re.compile(r"`+")


def visible_controls(text: str) -> str:
    """Show control characters as \\xNN instead of letting a terminal act on them."""
    return CONTROL.sub(lambda m: f"\\x{ord(m.group()):02x}", text)


def csv_cell(text: str) -> str:
    text = visible_controls(text)
    return "'" + text if text.startswith(FORMULA_START) else text


def markdown_text(text: str) -> str:
    """Plain text for a Markdown table cell or list item: no HTML, links, code or new blocks."""
    text = visible_controls(LINE_BREAK.sub(" ", text))
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return MARKDOWN_ESCAPES.sub(r"\\\1", text)


def markdown_code(text: str, in_table: bool = True) -> str:
    """A code span whose fence is longer than any backtick run inside it (CommonMark)."""
    text = visible_controls(LINE_BREAK.sub(" ", text))
    longest = max((len(run) for run in BACKTICK_RUN.findall(text)), default=0)
    fence = "`" * (longest + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    if in_table:
        text = text.replace("|", "\\|")
    return f"{fence}{pad}{text}{pad}{fence}"


def for_terminal(value: T) -> T:
    """Return a copy of a report dataclass tree with every string made safe for a terminal."""
    return _clean(value)  # type: ignore[no-any-return]


def _clean(value: Any) -> Any:
    if isinstance(value, Enum):
        return value
    if isinstance(value, str):
        return visible_controls(value)
    if isinstance(value, list):
        return [_clean(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean(item) for key, item in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        changes = {f.name: _clean(getattr(value, f.name)) for f in fields(value) if f.init}
        return replace(value, **changes)
    return value
