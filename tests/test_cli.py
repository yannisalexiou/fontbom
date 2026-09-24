from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from fontbom import __version__
from fontbom.cli import main
from tests.conftest import FIXTURES, make_font, write_tree, write_zip

MACHO = b"\xcf\xfa\xed\xfe" + b"\x00" * 28
OFL = "This Font Software is licensed under the SIL Open Font License, Version 1.1."


def ipa(tmp_path: Path) -> Path:
    return write_zip(
        tmp_path / "App.ipa",
        {
            "Payload/App.app/App": MACHO + b"\x00Good-Regular\x00",
            "Payload/App.app/Good.ttf": make_font(
                family="Good", postscript="Good-Regular", license_text=OFL
            ),
            "Payload/App.app/Mystery.ttf": make_font(family="Mystery", copyright=None),
        },
    )


def test_version() -> None:
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_scan_defaults_to_json_on_stdout(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["scan", str(ipa(tmp_path))])
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["schema_version"] == 1
    assert report["summary"] == {
        "fonts": 2,
        "open": 1,
        "commercial": 0,
        "restricted": 0,
        "unknown": 1,
        "referenced": 1,
        "unreferenced": 1,
        "unbundled_references": 0,
    }
    assert "not legal advice" in report["disclaimer"]


def test_markdown_and_csv_formats(tmp_path: Path) -> None:
    path = str(ipa(tmp_path))
    md = CliRunner().invoke(main, ["scan", path, "--format", "markdown"])
    assert md.exit_code == 0
    assert md.stdout.startswith("# fontbom report")
    csv_out = CliRunner().invoke(main, ["scan", path, "-f", "csv"])
    assert csv_out.exit_code == 0
    assert csv_out.stdout.splitlines()[1].startswith("sha256,status,")


def test_output_file_and_summary_on_stderr(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    result = CliRunner().invoke(main, ["scan", str(ipa(tmp_path)), "-o", str(out)])
    assert result.exit_code == 0
    assert result.stdout == ""
    assert "2 fonts" in result.stderr
    assert "1 unknown" in result.stderr
    assert json.loads(out.read_text())["summary"]["fonts"] == 2


def test_quiet_suppresses_the_summary(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    result = CliRunner().invoke(main, ["scan", str(ipa(tmp_path)), "-o", str(out), "--quiet"])
    assert result.exit_code == 0
    assert result.stderr == ""


def test_fail_on_unknown_exits_one_when_an_unknown_font_exists(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["scan", str(ipa(tmp_path)), "--fail-on", "unknown"])
    assert result.exit_code == 1
    assert "Mystery" in result.stderr
    assert "unknown" in result.stderr


def test_fail_on_passes_when_nothing_matches(tmp_path: Path) -> None:
    args = ["scan", str(ipa(tmp_path)), "--fail-on", "commercial,restricted"]
    assert CliRunner().invoke(main, args).exit_code == 0


def test_fail_on_unreferenced(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["scan", str(ipa(tmp_path)), "--fail-on", "unreferenced"])
    assert result.exit_code == 1


def test_fail_on_unreferenced_with_no_references_is_a_usage_error(tmp_path: Path) -> None:
    args = ["scan", str(ipa(tmp_path)), "--fail-on", "unreferenced", "--no-references"]
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 2
    assert "--no-references" in result.stderr


def test_fail_on_rejects_unknown_values(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["scan", str(ipa(tmp_path)), "--fail-on", "bogus"])
    assert result.exit_code == 2
    assert "bogus" in result.stderr


def test_missing_input_is_a_usage_error(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["scan", str(tmp_path / "nope.ipa")])
    assert result.exit_code == 2


def test_unsafe_archive_exits_two_with_message(tmp_path: Path) -> None:
    archive = write_zip(tmp_path / "evil.zip", {"../escape.ttf": make_font()})
    result = CliRunner().invoke(main, ["scan", str(archive)])
    assert result.exit_code == 2
    assert "escape" in result.stderr


def test_depth_limit_exits_two(tmp_path: Path) -> None:
    inner = write_zip(tmp_path / "inner.zip", {"a.ttf": make_font()})
    outer = write_zip(tmp_path / "outer.zip", {"inner.zip": inner.read_bytes()})
    result = CliRunner().invoke(main, ["scan", str(outer), "--max-depth", "1"])
    assert result.exit_code == 2
    assert "depth" in result.stderr


def test_real_fixture_directory_is_clean_under_strict_policy() -> None:
    args = ["scan", str(FIXTURES / "fonts"), "--fail-on", "unknown,commercial,restricted"]
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.stderr
    report = json.loads(result.stdout)
    assert {f["license"]["spdx"] for f in report["fonts"]} == {"OFL-1.1", "Apache-2.0"}


def test_android_repo_end_to_end(tmp_path: Path) -> None:
    root = write_tree(
        tmp_path / "repo",
        {
            "app/src/main/res/font/inter_bold.ttf": make_font(
                family="Inter", style="Bold", license_text=OFL
            ),
            "app/src/main/res/layout/main.xml": '<TextView android:fontFamily="@font/inter_bold" />',
            "app/src/main/Main.kt": 'Typeface.createFromAsset(a, "fonts/Missing-Regular.ttf")',
        },
    )
    result = CliRunner().invoke(main, ["scan", str(root), "-f", "markdown"])
    assert result.exit_code == 0
    assert "| Inter |" in result.stdout
    assert "fonts/Missing-Regular.ttf" in result.stdout


def test_progress_is_off_by_default_when_stderr_is_not_a_terminal(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["scan", str(ipa(tmp_path)), "-o", str(tmp_path / "r.json")])
    assert result.exit_code == 0
    assert "\r" not in result.stderr
    assert result.stderr.startswith("fontbom: ")


def test_forced_progress_renders_a_status_line_on_stderr(tmp_path: Path) -> None:
    args = ["scan", str(ipa(tmp_path)), "-o", str(tmp_path / "r.json"), "--progress"]
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0
    assert "\r" in result.stderr
    assert "files" in result.stderr
    assert "fonts" in result.stderr
    assert result.stderr.rstrip().endswith(
        "1 unreferenced, report written to " + str(tmp_path / "r.json")
    )


def test_quiet_disables_progress_even_when_forced(tmp_path: Path) -> None:
    args = ["scan", str(ipa(tmp_path)), "-o", str(tmp_path / "r.json"), "--progress", "--quiet"]
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0
    assert result.stderr == ""


def test_progress_goes_to_stderr_so_stdout_stays_valid_json(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["scan", str(ipa(tmp_path)), "--progress"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["summary"]["fonts"] == 2


def test_jobs_flag(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["scan", str(ipa(tmp_path)), "--jobs", "2"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["summary"]["referenced"] == 1
    bad = CliRunner().invoke(main, ["scan", str(ipa(tmp_path)), "--jobs", "0"])
    assert bad.exit_code == 2


def test_terminal_format_on_stdout_has_no_ansi_and_no_duplicate_summary(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["scan", str(ipa(tmp_path)), "-f", "terminal"])
    assert result.exit_code == 0
    assert result.stdout.startswith("fontbom ")
    assert "Fonts" in result.stdout
    assert "\x1b[" not in result.stdout
    assert "fontbom:" not in result.stderr


def test_terminal_format_to_file_has_no_ansi(tmp_path: Path) -> None:
    out = tmp_path / "r.txt"
    result = CliRunner().invoke(
        main, ["scan", str(ipa(tmp_path)), "-f", "terminal", "-o", str(out)]
    )
    assert result.exit_code == 0
    assert "\x1b[" not in out.read_text()
    assert "fontbom:" in result.stderr


def test_default_format_is_json_when_stdout_is_not_a_terminal(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["scan", str(ipa(tmp_path))])
    assert json.loads(result.stdout)["schema_version"] == 1
