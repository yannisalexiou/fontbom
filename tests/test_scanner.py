from __future__ import annotations

from pathlib import Path

from fontbom.inputs.limits import Limits
from fontbom.models import Confidence, Status
from fontbom.scanner import ScanOptions, scan
from tests.conftest import make_font, write_tree, write_zip

MACHO = b"\xcf\xfa\xed\xfe" + b"\x00" * 28


def test_adjacent_license_files_are_wired_from_the_walked_tree(tmp_path: Path) -> None:
    ofl = (Path(__file__).parent / "fixtures/fonts/pressstart2p/OFL.txt").read_text()
    write_zip(
        tmp_path / "App.ipa",
        {
            "Payload/App.app/Fonts/Plain.ttf": make_font(family="Plain", copyright=None),
            "Payload/App.app/Fonts/OFL.txt": ofl.encode(),
            "OFL.txt": ofl.encode(),  # outside the .app: must not be used for anything
        },
    )
    result = scan(tmp_path / "App.ipa", ScanOptions())
    (record,) = result.fonts
    assert record.license.status == Status.OPEN
    assert record.license.evidence[0].source == "adjacent:App.ipa!/Payload/App.app/Fonts/OFL.txt"
    assert result.input == str(tmp_path / "App.ipa")
    assert result.tool.startswith("fontbom ")
    assert result.scanned_at.endswith("Z")


def test_binary_strings_reference_bundled_fonts_at_low_confidence(tmp_path: Path) -> None:
    write_zip(
        tmp_path / "App.ipa",
        {
            "Payload/App.app/App": MACHO + b"\x00Used-Regular\x00",
            "Payload/App.app/Used.ttf": make_font(family="Used", postscript="Used-Regular"),
            "Payload/App.app/Idle.ttf": make_font(family="Idle", postscript="Idle-Regular"),
        },
    )
    result = scan(tmp_path / "App.ipa", ScanOptions())
    by_family = {r.primary.family: r for r in result.fonts}
    assert by_family["Used"].referenced is True
    assert by_family["Used"].references[0].confidence == Confidence.LOW
    assert by_family["Used"].references[0].source == "App.ipa!/Payload/App.app/App"
    assert by_family["Idle"].referenced is False
    assert result.unbundled_references == []


def test_source_references_and_unbundled_names_in_a_repo(tmp_path: Path) -> None:
    root = write_tree(
        tmp_path / "repo",
        {
            "app/src/main/res/font/inter_bold.ttf": make_font(family="Inter", style="Bold"),
            "app/src/main/res/layout/main.xml": '<TextView android:fontFamily="@font/inter_bold" />',
            "app/src/main/Main.kt": 'val t = Typeface.createFromAsset(a, "fonts/Missing-Regular.ttf")',
            "web/index.html": '<link href="https://fonts.googleapis.com/css2?family=Lato" rel="stylesheet">',
        },
    )
    result = scan(root, ScanOptions())
    (record,) = result.fonts
    assert [r.kind for r in record.references] == ["font-resource"]
    assert [r.name for r in result.unbundled_references] == ["Lato", "fonts/Missing-Regular.ttf"]


def test_references_can_be_disabled(tmp_path: Path) -> None:
    root = write_tree(
        tmp_path / "repo",
        {"f.ttf": make_font(family="F"), "a.swift": 'UIFont(name: "F", size: 1); "Nope"'},
    )
    result = scan(root, ScanOptions(references=False))
    assert result.fonts[0].referenced is False
    assert result.unbundled_references == []


def test_limits_are_passed_through(tmp_path: Path) -> None:
    import pytest

    from fontbom.inputs.limits import LimitExceeded

    inner = write_zip(tmp_path / "inner.zip", {"a.ttf": make_font()})
    outer = write_zip(tmp_path / "outer.zip", {"inner.zip": inner.read_bytes()})
    with pytest.raises(LimitExceeded):
        scan(outer, ScanOptions(limits=Limits(max_depth=1)))


def test_progress_callback_receives_phases_and_counts(tmp_path: Path) -> None:
    from fontbom.scanner import Progress

    root = write_tree(
        tmp_path / "repo",
        {"a.ttf": make_font(family="A"), "b.txt": "x", "c.swift": 'UIFont(name: "A", size: 1)'},
    )
    events: list[Progress] = []
    scan(root, ScanOptions(), on_progress=events.append)
    phases = [e.phase for e in events]
    assert phases[0] == "walking"
    assert "classifying" in phases
    assert "referencing" in phases
    assert phases[-1] == "done"
    walking = [e for e in events if e.phase == "walking"]
    assert [e.files for e in walking] == [1, 2, 3]
    assert walking[-1].current == "c.swift"
    assert events[-1].files == 3
    assert events[-1].fonts == 1


def test_jobs_option_is_accepted_and_results_are_unchanged(tmp_path: Path) -> None:
    write_zip(
        tmp_path / "App.ipa",
        {
            "Payload/App.app/App": MACHO + b"\x00Used-Regular\x00",
            "Payload/App.app/Used.ttf": make_font(family="Used", postscript="Used-Regular"),
        },
    )
    serial = scan(tmp_path / "App.ipa", ScanOptions(jobs=1))
    parallel = scan(tmp_path / "App.ipa", ScanOptions(jobs=4))
    assert serial.fonts[0].references == parallel.fonts[0].references
