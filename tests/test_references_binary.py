from __future__ import annotations

from pathlib import Path

from fontbom.references.binary import BinaryScanner, is_binary_candidate
from tests.conftest import entry

MACHO_64 = b"\xcf\xfa\xed\xfe" + b"\x00" * 28


def test_finds_ascii_and_utf16_names_in_macho(tmp_path: Path) -> None:
    blob = MACHO_64 + b"junk\x00Roboto-Bold\x00more\x00" + "Lato".encode("utf-16-le") + b"\x00\x00"
    e = entry(tmp_path, "Payload/App.app/App", blob)
    refs = list(BinaryScanner(["Roboto-Bold", "Lato", "Missing"]).scan(e))
    assert sorted(r.name for r in refs) == ["Lato", "Roboto-Bold"]
    assert {r.kind for r in refs} == {"binary-string"}
    assert {r.confidence for r in refs} == {"low"}
    assert refs[0].ecosystem == "binary"
    assert refs[0].line is None


def test_dex_and_arsc_are_candidates(tmp_path: Path) -> None:
    assert is_binary_candidate(entry(tmp_path, "classes.dex", b"dex\n035\x00" + b"\x00" * 64))
    assert is_binary_candidate(entry(tmp_path, "resources.arsc", b"\x02\x00\x0c\x00" + b"\x00" * 8))
    assert is_binary_candidate(entry(tmp_path, "base/resources.pb", b"\n\x05hello"))
    assert is_binary_candidate(entry(tmp_path, "lib/arm64-v8a/libapp.so", b"\x7fELF" + b"\x00" * 8))
    assert is_binary_candidate(entry(tmp_path, "Frameworks/X.framework/X", MACHO_64))
    assert is_binary_candidate(
        entry(tmp_path, "Main.storyboardc/View.nib", b"bplist00" + b"\x00" * 8)
    )


def test_non_binary_files_are_not_candidates(tmp_path: Path) -> None:
    assert not is_binary_candidate(entry(tmp_path, "a.swift", "let x = 1"))
    assert not is_binary_candidate(entry(tmp_path, "a.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 8))
    assert not is_binary_candidate(entry(tmp_path, "a.ttf", b"\x00\x01\x00\x00" + b"\x00" * 8))


def test_short_or_empty_names_are_never_searched(tmp_path: Path) -> None:
    e = entry(tmp_path, "App", MACHO_64 + b"A B AB")
    assert list(BinaryScanner(["A", "", "AB"]).scan(e)) == []


def found(names: list[str], blob: bytes, tmp_path: Path) -> set[str]:
    e = entry(tmp_path, "App", MACHO_64 + blob)
    return {r.name for r in BinaryScanner(names).scan(e)}


def test_longer_names_are_verified_at_each_hit_of_the_shorter_name(tmp_path: Path) -> None:
    names = ["Inter", "Inter Display", "InterDisplay-Regular"]
    blob = b"\x00Interface\x00 Inter Display \x00internal\x00"
    assert found(names, blob, tmp_path) == {"Inter", "Inter Display"}


def test_longer_name_without_the_shorter_one_as_substring_is_still_found(tmp_path: Path) -> None:
    names = ["Source Sans Pro", "SourceSansPro-Regular"]
    assert found(names, b"\x00SourceSansPro-Regular\x00", tmp_path) == {"SourceSansPro-Regular"}


def test_longer_name_is_found_in_utf16(tmp_path: Path) -> None:
    names = ["Inter", "Inter Display"]
    blob = b"\x00\x00" + "Inter Display".encode("utf-16-le") + b"\x00\x00"
    assert found(names, blob, tmp_path) == {"Inter", "Inter Display"}


def test_chained_containment_is_resolved(tmp_path: Path) -> None:
    names = ["Inter", "Inter Display", "Inter Display Bold"]
    assert found(names, b"\x00Inter Display Bold\x00", tmp_path) == set(names)
    assert found(names, b"\x00Inter Display\x00", tmp_path) == {"Inter", "Inter Display"}


def test_shorter_name_is_not_reported_when_only_unrelated_text_is_present(tmp_path: Path) -> None:
    assert found(["Inter", "Inter Display"], b"\x00Display\x00", tmp_path) == set()


def test_large_files_are_searched_to_the_end(tmp_path: Path) -> None:
    blob = b"\x00" * (3 * 1024 * 1024) + b"Lato-Regular\x00"
    assert found(["Lato-Regular", "Lato"], blob, tmp_path) == {"Lato", "Lato-Regular"}


def test_parallel_search_matches_serial_results(tmp_path: Path) -> None:
    from fontbom.references.binary import scan_binaries

    names = ["Inter", "Inter Display", "Lato-Regular", "Lato", "Roboto", "Missing"]
    entries = [
        entry(tmp_path, "App", MACHO_64 + b"\x00Inter Display\x00" + "Lato".encode("utf-16-le")),
        entry(tmp_path, "Frameworks/V.framework/V", MACHO_64 + b"\x00Roboto\x00Lato-Regular\x00"),
        entry(tmp_path, "empty", b""),
        entry(tmp_path, "readme.txt", b"Roboto is not scanned here"),
    ]
    serial = sorted(scan_binaries(entries, names, jobs=1), key=lambda r: (r.source, r.name))
    parallel = sorted(
        scan_binaries(entries, names, jobs=3, parallel_threshold=0),
        key=lambda r: (r.source, r.name),
    )
    assert [(r.source, r.name) for r in serial] == [
        ("App", "Inter"),
        ("App", "Inter Display"),
        ("App", "Lato"),
        ("Frameworks/V.framework/V", "Lato"),
        ("Frameworks/V.framework/V", "Lato-Regular"),
        ("Frameworks/V.framework/V", "Roboto"),
    ]
    assert parallel == serial


def test_parallel_search_reports_progress_per_file(tmp_path: Path) -> None:
    from fontbom.references.binary import scan_binaries

    entries = [entry(tmp_path, f"bin{i}", MACHO_64 + b"\x00Lato\x00") for i in range(3)]
    seen: list[str] = []
    list(scan_binaries(entries, ["Lato"], jobs=2, parallel_threshold=0, on_file=seen.append))
    assert sorted(seen) == ["bin0", "bin1", "bin2"]
