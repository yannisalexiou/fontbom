"""Report renderers. Every format includes the disclaimer."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fontbom.models import ScanResult
from fontbom.report.csv_report import render_csv
from fontbom.report.json_report import render_json
from fontbom.report.markdown_report import render_markdown
from fontbom.report.terminal_report import render_terminal

RENDERERS: dict[str, Callable[[ScanResult], str]] = {
    "terminal": render_terminal,
    "json": render_json,
    "csv": render_csv,
    "markdown": render_markdown,
}

FORMATS: tuple[str, ...] = tuple(RENDERERS)


def render(result: ScanResult, fmt: str, **options: Any) -> str:
    """Render ``result``. ``options`` (width, color) apply to the terminal format only."""
    try:
        renderer = RENDERERS[fmt]
    except KeyError:
        raise ValueError(f"unknown report format: {fmt!r}") from None
    if fmt == "terminal":
        return render_terminal(result, **options)
    return renderer(result)
