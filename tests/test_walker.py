from __future__ import annotations

import os
from pathlib import Path

import pytest

from fontbom.inputs.limits import LimitExceeded, Limits, UnsafeMember
from fontbom.inputs.walker import walk
from tests.conftest import make_font, write_tree, write_zip


def paths(entries: list) -> list[str]:  # type: ignore[type-arg]
    return sorted(e.logical_path for e in entries)


def test_walks_directory_recursively_with_relative_logical_paths(tmp_path: Path) -> None:
    root = write_tree(tmp_path / "repo", {"a.txt": "x", "sub/deep/b.ttf": make_font()})
    entries = list(walk(root, Limits(), tmp_path / "work"))
    assert paths(entries) == ["a.txt", "sub/deep/b.ttf"]
    b = next(e for e in entries if e.logical_path.endswith("b.ttf"))
    assert b.size == len(make_font())
    assert b.read_header(4) == b"\x00\x01\x00\x00"
    assert b.read() == make_font()
    assert b.depth == 0


def test_skips_git_directory_and_symlinks(tmp_path: Path) -> None:
    root = write_tree(tmp_path / "repo", {".git/objects/x": "x", "real.ttf": make_font()})
    os.symlink(root / "real.ttf", root / "link.ttf")
    os.symlink(tmp_path, root / "loop")
    assert paths(list(walk(root, Limits(), tmp_path / "work"))) == ["real.ttf"]


def test_directory_bundles_are_plain_directories(tmp_path: Path) -> None:
    root = write_tree(
        tmp_path / "Lib.xcframework",
        {"ios-arm64/Lib.framework/Fonts/A.ttf": make_font(), "Info.plist": "<plist/>"},
    )
    assert paths(list(walk(root, Limits(), tmp_path / "work"))) == [
        "Info.plist",
        "ios-arm64/Lib.framework/Fonts/A.ttf",
    ]


def test_single_regular_file_input_yields_itself(tmp_path: Path) -> None:
    font = tmp_path / "Solo.ttf"
    font.write_bytes(make_font())
    (entry,) = list(walk(font, Limits(), tmp_path / "work"))
    assert entry.logical_path == "Solo.ttf"


@pytest.mark.parametrize("ext", ["ipa", "apk", "aab", "zip", "aar", "jar"])
def test_zip_family_archives_are_expanded_with_bang_separator(tmp_path: Path, ext: str) -> None:
    archive = write_zip(
        tmp_path / f"App.{ext}",
        {"Payload/App.app/Fonts/A.ttf": make_font(), "Payload/App.app/Info.plist": b"<plist/>"},
    )
    entries = list(walk(archive, Limits(), tmp_path / "work"))
    assert paths(entries) == [
        f"App.{ext}!/Payload/App.app/Fonts/A.ttf",
        f"App.{ext}!/Payload/App.app/Info.plist",
    ]
    font = next(e for e in entries if e.logical_path.endswith(".ttf"))
    assert font.read() == make_font()
    assert font.depth == 1


def test_nested_archives_are_expanded_recursively(tmp_path: Path) -> None:
    inner = write_zip(tmp_path / "inner.jar", {"fonts/Inner.ttf": make_font(family="Inner")})
    outer = write_zip(tmp_path / "App.apk", {"lib/inner.jar": inner.read_bytes()})
    entries = list(walk(outer, Limits(), tmp_path / "work"))
    assert paths(entries) == ["App.apk!/lib/inner.jar!/fonts/Inner.ttf"]
    assert entries[0].depth == 2


def test_archive_inside_directory_is_expanded(tmp_path: Path) -> None:
    write_zip(tmp_path / "repo" / "vendor" / "sdk.aar", {"res/font/x.ttf": make_font()})
    entries = list(walk(tmp_path / "repo", Limits(), tmp_path / "work"))
    assert paths(entries) == ["vendor/sdk.aar!/res/font/x.ttf"]


def test_depth_limit_is_enforced(tmp_path: Path) -> None:
    inner = write_zip(tmp_path / "inner.zip", {"a.ttf": make_font()})
    outer = write_zip(tmp_path / "outer.zip", {"inner.zip": inner.read_bytes()})
    with pytest.raises(LimitExceeded, match="depth"):
        list(walk(outer, Limits(max_depth=1), tmp_path / "work"))


def test_total_bytes_limit_is_enforced(tmp_path: Path) -> None:
    archive = write_zip(tmp_path / "big.zip", {"a.bin": b"\0" * 10_000, "b.bin": b"\0" * 10_000})
    with pytest.raises(LimitExceeded, match="bytes"):
        list(walk(archive, Limits(max_total_bytes=15_000), tmp_path / "work"))


def test_entry_count_limit_is_enforced(tmp_path: Path) -> None:
    archive = write_zip(tmp_path / "many.zip", {f"f{i}.txt": b"x" for i in range(5)})
    with pytest.raises(LimitExceeded, match="entries"):
        list(walk(archive, Limits(max_entries=3), tmp_path / "work"))


@pytest.mark.parametrize("member", ["../escape.ttf", "/abs/escape.ttf", "a/../../escape.ttf"])
def test_zip_slip_members_are_rejected(tmp_path: Path, member: str) -> None:
    archive = write_zip(tmp_path / "evil.zip", {member: make_font()})
    with pytest.raises(UnsafeMember):
        list(walk(archive, Limits(), tmp_path / "work"))


def test_corrupt_nested_archive_is_yielded_as_a_plain_file(tmp_path: Path) -> None:
    root = write_tree(tmp_path / "repo", {"broken.jar": b"not a zip", "ok.ttf": make_font()})
    assert paths(list(walk(root, Limits(), tmp_path / "work"))) == ["broken.jar", "ok.ttf"]


def test_extracted_files_live_under_the_given_workdir(tmp_path: Path) -> None:
    archive = write_zip(tmp_path / "App.ipa", {"Payload/App.app/A.ttf": make_font()})
    work = tmp_path / "work"
    (entry,) = list(walk(archive, Limits(), work))
    assert entry.real_path.is_relative_to(work)


def test_entries_carry_a_cached_header(tmp_path: Path) -> None:
    root = write_tree(tmp_path / "repo", {"a.ttf": make_font(), "empty.bin": b""})
    entries = {e.logical_path: e for e in walk(root, Limits(), tmp_path / "work")}
    assert entries["a.ttf"].header == make_font()[:8]
    assert entries["empty.bin"].header == b""
    (root / "a.ttf").unlink()
    assert entries["a.ttf"].read_header(4) == b"\x00\x01\x00\x00"
