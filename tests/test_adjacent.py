from __future__ import annotations

import pytest

from fontbom.licenses.adjacent import find_adjacent, is_license_filename


@pytest.mark.parametrize(
    "name",
    ["OFL.txt", "ofl.txt", "OFL-FAQ.txt", "LICENSE", "LICENSE.txt", "LICENSE.md", "LICENCE",
     "COPYING", "COPYING.LESSER", "UFL.txt", "License.txt", "EULA.txt", "EULA.pdf"],
)  # fmt: skip
def test_license_filenames(name: str) -> None:
    assert is_license_filename(name)


@pytest.mark.parametrize("name", ["README.md", "Info.plist", "font.ttf", "licenses.json", "x.py"])
def test_non_license_filenames(name: str) -> None:
    assert not is_license_filename(name)


def test_same_directory_is_distance_zero_and_comes_first() -> None:
    found = find_adjacent(
        "fonts/roboto/Roboto-Regular.ttf",
        ["fonts/roboto/LICENSE.txt", "fonts/OFL.txt", "LICENSE"],
    )
    assert found == [("fonts/roboto/LICENSE.txt", 0), ("fonts/OFL.txt", 1), ("LICENSE", 2)]


def test_distance_limit_defaults_to_three_levels() -> None:
    assert find_adjacent("a/b/c/d/f.ttf", ["a/OFL.txt", "OFL.txt"]) == [("a/OFL.txt", 3)]


def test_does_not_cross_archive_boundary() -> None:
    found = find_adjacent(
        "App.ipa!/Payload/App.app/Fonts/X.ttf",
        ["App.ipa!/Payload/App.app/OFL.txt", "OFL.txt", "Other.ipa!/Payload/OFL.txt"],
    )
    assert found == [("App.ipa!/Payload/App.app/OFL.txt", 1)]


def test_does_not_look_above_a_bundle_boundary() -> None:
    found = find_adjacent(
        "Payload/App.app/Frameworks/Vendor.framework/Fonts/X.ttf",
        [
            "Payload/App.app/Frameworks/Vendor.framework/LICENSE",
            "Payload/App.app/OFL.txt",
            "Payload/App.app/Frameworks/OFL.txt",
        ],
    )
    assert found == [("Payload/App.app/Frameworks/Vendor.framework/LICENSE", 1)]


def test_non_license_files_are_never_returned() -> None:
    assert find_adjacent("fonts/X.ttf", ["fonts/README.md", "fonts/Y.ttf"]) == []
