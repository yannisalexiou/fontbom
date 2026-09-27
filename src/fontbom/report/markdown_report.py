"""Markdown output for humans and pull-request comments."""

from __future__ import annotations

from fontbom.models import FontRecord, ScanResult, Status
from fontbom.report.disclaimer import TEXT as DISCLAIMER
from fontbom.report.escaping import markdown_code, markdown_text

FLAGGED = {Status.COMMERCIAL, Status.RESTRICTED, Status.UNKNOWN}


def render_markdown(result: ScanResult) -> str:
    summary = result.summary
    lines = [
        "# fontbom report",
        "",
        f"- Input: {markdown_code(result.input, in_table=False)}",
        f"- Scanned: {result.scanned_at}",
        f"- Tool: {result.tool}",
        "",
        "## Summary",
        "",
        "| Status | Fonts |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {status.value} | {summary[status.value]} |" for status in Status)
    lines.append(f"| **total** | **{summary['fonts']}** |")
    lines.extend(
        [
            "",
            f"Referenced: {summary['referenced']}. Unreferenced: {summary['unreferenced']}. "
            f"Referenced but not bundled: {summary['unbundled_references']}.",
            "",
            "## Fonts",
            "",
            "| Family | PostScript name | Status | SPDX | Embedding | Referenced "
            "| Evidence | Paths |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend(_font_row(record) for record in result.fonts)

    lines.extend(["", "## Bundled but unreferenced", ""])
    unreferenced = [record for record in result.fonts if not record.referenced]
    if unreferenced:
        lines.append(
            "These fonts ship in the bundle but no scanned code names them. Binary string "
            "matches count as references at low confidence, so a font listed here may still "
            "be loaded dynamically."
        )
        lines.append("")
        lines.extend(
            f"- {_family(record)} ({markdown_code(record.primary.postscript_name or '?')}), "
            f"sha256 `{record.sha256[:12]}…`"
            for record in unreferenced
        )
    else:
        lines.append("None.")

    lines.extend(["", "## Referenced but not bundled", ""])
    if result.unbundled_references:
        lines.extend(["| Name | Ecosystem | Kind | Source |", "| --- | --- | --- | --- |"])
        for ref in result.unbundled_references:
            location = f"{ref.source}:{ref.line}" if ref.line is not None else ref.source
            lines.append(
                f"| {markdown_text(ref.name)} | {ref.ecosystem} | {ref.kind} "
                f"| {markdown_code(location)} |"
            )
    else:
        lines.append("None.")

    lines.extend(["", "---", "", DISCLAIMER, ""])
    return "\n".join(lines)


def _font_row(record: FontRecord) -> str:
    face = record.primary
    status = record.license.status
    status_cell = f"**{status.value}**" if status in FLAGGED else status.value
    referenced = f"yes ({len(record.references)})" if record.referenced else "no"
    sources = dict.fromkeys(e.source for e in record.license.evidence)
    evidence = ", ".join(markdown_text(source) for source in sources) or "—"
    paths = "<br>".join(markdown_code(path) for path in record.paths)
    return (
        f"| {_family(record)} | {markdown_code(face.postscript_name or '?')} | {status_cell} | "
        f"{record.license.spdx or '—'} | {record.license.embedding.value} | {referenced} | "
        f"{evidence} | {paths} |"
    )


def _family(record: FontRecord) -> str:
    return markdown_text(record.primary.family or record.paths[0].rsplit("/", 1)[-1])
