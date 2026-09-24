from __future__ import annotations

import hashlib
from pathlib import Path

from fontbom.discovery import discover_fonts
from fontbom.fonts.detect import FontFormat
from fontbom.inputs.limits import Limits
from fontbom.inputs.walker import walk
from tests.conftest import make_collection, make_font, write_tree, write_zip


def test_same_font_in_two_places_is_one_record_with_both_paths(tmp_path: Path) -> None:
    font = make_font(family="Shared")
    write_zip(
        tmp_path / "App.ipa",
        {
            "Payload/App.app/Shared.ttf": font,
            "Payload/App.app/Frameworks/VendorSDK.framework/Shared.ttf": font,
        },
    )
    records = discover_fonts(walk(tmp_path / "App.ipa", Limits(), tmp_path / "work"))
    assert len(records) == 1
    record = records[0]
    assert record.sha256 == hashlib.sha256(font).hexdigest()
    assert record.size == len(font)
    assert record.format == FontFormat.TRUETYPE
    assert record.paths == [
        "App.ipa!/Payload/App.app/Frameworks/VendorSDK.framework/Shared.ttf",
        "App.ipa!/Payload/App.app/Shared.ttf",
    ]
    assert record.faces[0].family == "Shared"


def test_non_font_files_are_ignored(tmp_path: Path) -> None:
    root = write_tree(
        tmp_path / "repo", {"README.md": "# hi", "img.png": b"\x89PNG\r\n", "a.ttf": make_font()}
    )
    records = discover_fonts(walk(root, Limits(), tmp_path / "work"))
    assert [r.paths for r in records] == [["a.ttf"]]


def test_renamed_font_is_discovered_by_magic_bytes(tmp_path: Path) -> None:
    root = write_tree(tmp_path / "repo", {"assets/blob.dat": make_font(family="Hidden")})
    (record,) = discover_fonts(walk(root, Limits(), tmp_path / "work"))
    assert record.paths == ["assets/blob.dat"]
    assert record.faces[0].family == "Hidden"


def test_corrupt_font_file_is_recorded_with_error(tmp_path: Path) -> None:
    root = write_tree(tmp_path / "repo", {"Broken.ttf": b"\x00\x01\x00\x00junk"})
    (record,) = discover_fonts(walk(root, Limits(), tmp_path / "work"))
    assert record.paths == ["Broken.ttf"]
    assert record.faces[0].errors


def test_collection_record_carries_all_faces(tmp_path: Path) -> None:
    ttc = make_collection([make_font(family="One"), make_font(family="Two")])
    root = write_tree(tmp_path / "repo", {"Pack.ttc": ttc})
    (record,) = discover_fonts(walk(root, Limits(), tmp_path / "work"))
    assert record.format == FontFormat.COLLECTION
    assert [f.family for f in record.faces] == ["One", "Two"]


def test_records_are_sorted_by_first_path(tmp_path: Path) -> None:
    root = write_tree(
        tmp_path / "repo",
        {"z/last.ttf": make_font(family="Z"), "a/first.ttf": make_font(family="A")},
    )
    records = discover_fonts(walk(root, Limits(), tmp_path / "work"))
    assert [r.paths[0] for r in records] == ["a/first.ttf", "z/last.ttf"]


def test_woff2_is_discovered(tmp_path: Path) -> None:
    root = write_tree(tmp_path / "repo", {"web/f.woff2": make_font(family="Web", flavor="woff2")})
    (record,) = discover_fonts(walk(root, Limits(), tmp_path / "work"))
    assert record.format == FontFormat.WOFF2
    assert record.faces[0].family == "Web"
