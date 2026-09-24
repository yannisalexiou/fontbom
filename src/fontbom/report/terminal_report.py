"""Human-readable terminal output: aligned columns, optional color, fitted to the width."""

from __future__ import annotations

import shutil
import textwrap
from collections import Counter
from collections.abc import Sequence

import click

from fontbom.models import FontRecord, Reference, ScanResult, Status
from fontbom.report.disclaimer import TEXT as DISCLAIMER

INDENT = "  "
GAP = "  "
MAX_UNBUNDLED_ROWS = 20
STATUS_COLORS: dict[Status, str] = {
    Status.OPEN: "green",
    Status.COMMERCIAL: "red",
    Status.RESTRICTED: "red",
    Status.UNKNOWN: "yellow",
}


def render_terminal(result: ScanResult, width: int | None = None, color: bool = False) -> str:
    width = width or shutil.get_terminal_size((100, 24)).columns
    paint = _Painter(color)
    summary = result.summary
    out: list[str] = []

    out.append(paint.bold(result.tool) + f" · {result.input} · {result.scanned_at}")
    out.append("")
    if not result.fonts:
        out.append("No fonts found.")
    else:
        out.append(paint.bold("Summary"))
        statuses = ", ".join(
            paint.status(status, f"{summary[status.value]} {status.value}") for status in Status
        )
        out.append(f"{INDENT}{summary['fonts']} fonts: {statuses}")
        names = len({_group_key(r) for r in result.unbundled_references})
        out.append(
            f"{INDENT}{summary['referenced']} referenced, {summary['unreferenced']} unreferenced, "
            f"{names} name{'s' if names != 1 else ''} referenced but not bundled"
        )
        out.append("")
        out.append(paint.bold("Fonts"))
        out.extend(_font_table(result.fonts, width, paint))

        unreferenced = [r for r in result.fonts if not r.referenced]
        if unreferenced:
            out.append("")
            out.append(paint.bold(f"Bundled but unreferenced ({len(unreferenced)})"))
            out.extend(_unreferenced_rows(unreferenced, width))

    if result.unbundled_references:
        out.append("")
        out.extend(_unbundled_section(result.unbundled_references, width, paint))

    out.append("")
    out.extend(paint.dim(line) for line in textwrap.wrap(DISCLAIMER, width=max(width, 20)))
    return "\n".join(out) + "\n"


class _Painter:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def bold(self, text: str) -> str:
        return click.style(text, bold=True) if self.enabled else text

    def dim(self, text: str) -> str:
        return click.style(text, dim=True) if self.enabled else text

    def status(self, status: Status, text: str) -> str:
        return click.style(text, fg=STATUS_COLORS[status]) if self.enabled else text


MIN_PATH_WIDTH = 24
MAX_FAMILY_WIDTH = 24


def _font_table(records: Sequence[FontRecord], width: int, paint: _Painter) -> list[str]:
    """Aligned table. Optional columns are dropped, narrowest last, until paths get room."""
    columns: list[tuple[str, list[str], bool]] = [
        ("STATUS", [r.license.status.value for r in records], False),
        (
            "FAMILY",
            [_clip(r.primary.family or r.primary.postscript_name or "?") for r in records],
            False,
        ),
        (
            "STYLE",
            [r.primary.names.get(17) or r.primary.names.get(2) or "" for r in records],
            False,
        ),
        ("SPDX", [r.license.spdx or "—" for r in records], False),
        ("EMBEDDING", [r.license.embedding.value for r in records], False),
        ("REFS", [str(len(r.references)) for r in records], True),
    ]
    for optional in ("EMBEDDING", "STYLE", "SPDX"):
        if _prefix_width(columns) + MIN_PATH_WIDTH <= width:
            break
        columns = [c for c in columns if c[0] != optional]

    widths = [max(len(header), *(len(v) for v in values)) for header, values, _ in columns]
    right = {i for i, (_, _, is_right) in enumerate(columns) if is_right}
    header = tuple(h for h, _, _ in columns)
    lines = [_row((*header, "PATH"), widths, right, width)]
    for index, record in enumerate(records):
        row = tuple(values[index] for _, values, _ in columns)
        line = _row((*row, _paths_cell(record.paths)), widths, right, width)
        plain = row[0].ljust(widths[0])
        lines.append(line.replace(plain, paint.status(record.license.status, plain), 1))
    return lines


def _prefix_width(columns: list[tuple[str, list[str], bool]]) -> int:
    widths = [max(len(header), *(len(v) for v in values)) for header, values, _ in columns]
    return len(INDENT) + sum(widths) + len(GAP) * len(columns)


def _clip(text: str, limit: int = MAX_FAMILY_WIDTH) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _row(cells: tuple[str, ...], widths: list[int], right: set[int], width: int) -> str:
    fixed = [
        cell.rjust(widths[i]) if i in right else cell.ljust(widths[i])
        for i, cell in enumerate(cells[:-1])
    ]
    prefix = INDENT + GAP.join(fixed) + GAP
    return prefix + _fit(cells[-1], width - len(prefix))


def _paths_cell(paths: Sequence[str]) -> str:
    extra = f" (+{len(paths) - 1})" if len(paths) > 1 else ""
    return paths[0] + extra


def _fit(text: str, budget: int) -> str:
    """Left-truncate ``text`` to ``budget`` characters, keeping any trailing ' (+N)' marker."""
    if len(text) <= budget:
        return text
    if budget < 8:
        return text[-budget:] if budget > 0 else ""
    suffix = ""
    if text.endswith(")") and " (+" in text:
        text, _, tail = text.rpartition(" (+")
        suffix = " (+" + tail
    keep = budget - len(suffix) - 1
    return "…" + text[-keep:] + suffix if keep > 0 else suffix.strip()


def _unreferenced_rows(records: Sequence[FontRecord], width: int) -> list[str]:
    labels = [
        r.primary.full_name or r.primary.family or r.primary.postscript_name or r.paths[0]
        for r in records
    ]
    label_width = max(len(label) for label in labels)
    lines = []
    for label, record in zip(labels, records, strict=True):
        prefix = INDENT + label.ljust(label_width) + GAP
        lines.append(prefix + _fit(_paths_cell(record.paths), width - len(prefix)))
    return lines


def _group_key(reference: Reference) -> str:
    return reference.name.casefold()


def _unbundled_section(references: Sequence[Reference], width: int, paint: _Painter) -> list[str]:
    groups: dict[str, list[Reference]] = {}
    for reference in references:
        groups.setdefault(_group_key(reference), []).append(reference)
    ordered = sorted(groups.values(), key=lambda g: (-len(g), g[0].name.casefold()))
    total = len(ordered)
    title = f"Referenced but not bundled ({total} name{'s' if total != 1 else ''})"
    lines = [paint.bold(title)]
    shown = ordered[:MAX_UNBUNDLED_ROWS]

    header = ("NAME", "REFS", "ECOSYSTEMS")
    rows = []
    for group in shown:
        ecosystems = ", ".join(sorted(Counter(r.ecosystem for r in group)))
        rows.append((group[0].name, str(len(group)), ecosystems))
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(header)]
    lines.append(_row((*header, "SOURCE"), widths, {1}, width))
    for group, row in zip(shown, rows, strict=True):
        first = group[0]
        location = f"{first.source}:{first.line}" if first.line is not None else first.source
        lines.append(_row((*row, location), widths, {1}, width))
    if total > len(shown):
        lines.append(
            f"{INDENT}… and {total - len(shown)} more. Use --format json for the full list."
        )
    return lines
