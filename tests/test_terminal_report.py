from __future__ import annotations

from fontbom.models import Confidence, Reference, ScanResult
from fontbom.report import render
from fontbom.report.disclaimer import TEXT as DISCLAIMER
from fontbom.report.terminal_report import render_terminal
from tests.test_reports import fixed_result


def lines(width: int = 100, **kwargs: object) -> list[str]:
    return render_terminal(fixed_result(), width=width, color=False, **kwargs).splitlines()  # type: ignore[arg-type]


def test_header_names_tool_input_and_time() -> None:
    assert lines()[0] == "fontbom 0.1.0 · App.ipa · 2026-09-22T12:00:00Z"


def test_summary_counts_are_spelled_out() -> None:
    text = "\n".join(lines())
    assert "2 fonts: 1 open, 0 commercial, 1 restricted, 0 unknown" in text
    assert "1 referenced, 1 unreferenced, 1 name referenced but not bundled" in text


def test_font_table_is_aligned_and_flags_problem_statuses() -> None:
    out = lines()
    header = next(line for line in out if line.strip().startswith("STATUS"))
    rows = [line for line in out if line.strip().startswith(("open", "restricted"))]
    assert [c for c in header.split() if c] == [
        "STATUS", "FAMILY", "STYLE", "SPDX", "EMBEDDING", "REFS", "PATH",
    ]  # fmt: skip
    assert len(rows) == 2
    family_column = header.index("FAMILY")
    assert rows[0][family_column:].startswith("Libre Test")
    assert rows[1][family_column:].startswith("Secret Sans")
    assert "OFL-1.1" in rows[0]
    assert "—" in rows[1]  # no SPDX
    assert rows[1].rstrip().endswith("(+1)")  # a second path exists


def test_lines_fit_the_width_and_long_paths_are_truncated_from_the_left() -> None:
    out = lines(width=72)
    assert all(len(line) <= 72 for line in out), [line for line in out if len(line) > 72]
    row = next(line for line in out if line.strip().startswith("restricted"))
    assert "…" in row
    assert "Secret.otf (+1)" in row


def test_unreferenced_section_lists_fonts() -> None:
    out = lines()
    start = out.index("Bundled but unreferenced (1)")
    assert "Secret Sans Bold" in out[start + 1]
    assert "Secret.otf" in out[start + 1]


def test_unbundled_names_are_grouped_and_counted() -> None:
    result = fixed_result()
    result.unbundled_references = [
        Reference("Open Sans", "google-fonts-url", "web", "www/index.html", 1, Confidence.HIGH),
        Reference("Open Sans", "font-face", "web", "www/app.css", 9, Confidence.HIGH),
        Reference("Open Sans", "fontfamily-style", "react-native", "src/A.tsx", 4, Confidence.HIGH),
        Reference("Lato", "uifont", "ios", "App/V.swift", 2, Confidence.HIGH),
    ]
    out = render_terminal(result, width=120, color=False).splitlines()
    start = out.index("Referenced but not bundled (2 names)")
    header, first, second = out[start + 1], out[start + 2], out[start + 3]
    assert header.split() == ["NAME", "REFS", "ECOSYSTEMS", "SOURCE"]
    assert first.split()[:2] == ["Open", "Sans"] and "3" in first
    assert "react-native, web" in first
    assert "www/index.html:1" in first
    assert second.split()[0] == "Lato"


def test_unbundled_list_is_capped_with_a_hint() -> None:
    result = fixed_result()
    result.unbundled_references = [
        Reference(f"Name {i:03d}", "uifont", "ios", "a.swift", i, Confidence.HIGH)
        for i in range(30)
    ]
    out = render_terminal(result, width=100, color=False)
    assert "Name 019" in out
    assert "Name 020" not in out
    assert "and 10 more" in out
    assert "--format json" in out


def test_disclaimer_is_present_in_full() -> None:
    out = render_terminal(fixed_result(), width=100, color=False)
    assert " ".join(out.split()).endswith(DISCLAIMER)


def test_color_adds_ansi_only_when_asked() -> None:
    assert "\x1b[" in render_terminal(fixed_result(), width=100, color=True)
    assert "\x1b[" not in render_terminal(fixed_result(), width=100, color=False)


def test_empty_result_says_so() -> None:
    result = ScanResult("fontbom 0.1.0", "2026-09-22T12:00:00Z", "empty", [], [])
    out = render_terminal(result, width=100, color=False)
    assert "No fonts found." in out
    assert "not legal advice" in out


def test_render_registry_knows_terminal() -> None:
    assert "Fonts" in render(fixed_result(), "terminal")
