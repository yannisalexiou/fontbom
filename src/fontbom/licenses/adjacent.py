"""Locate license files that sit next to a font, within distance and boundary limits."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath

from fontbom.inputs.walker import ARCHIVE_SEPARATOR

LICENSE_FILENAME = re.compile(
    r"^(?:OFL(?:-FAQ)?|UFL|LICEN[CS]E|COPYING|EULA)(?:[.\-_].*)?$", re.IGNORECASE
)

# Directories that end a bundle. Files above them belong to something else.
BUNDLE_SUFFIXES: frozenset[str] = frozenset(
    {".app", ".appex", ".framework", ".xcframework", ".bundle"}
)

DEFAULT_MAX_DISTANCE = 3


@dataclass(frozen=True)
class AdjacentFile:
    path: str
    distance: int  # 0 = same directory as the font
    text: str


def is_license_filename(name: str) -> bool:
    return LICENSE_FILENAME.match(name) is not None


def find_adjacent(
    font_path: str, candidates: Iterable[str], max_distance: int = DEFAULT_MAX_DISTANCE
) -> list[tuple[str, int]]:
    """Return (path, distance) for license-named files near ``font_path``, nearest first.

    The search walks up from the font's directory. It stops after ``max_distance`` levels,
    at the enclosing archive, or at the enclosing bundle directory, whichever comes first.
    """
    container, inner = _split_container(font_path)
    directories = _search_directories(PurePosixPath(inner).parent, max_distance)
    by_directory = {directory: distance for distance, directory in enumerate(directories)}

    found: list[tuple[str, int]] = []
    for candidate in candidates:
        candidate_container, candidate_inner = _split_container(candidate)
        if candidate_container != container:
            continue
        inner_path = PurePosixPath(candidate_inner)
        if not is_license_filename(inner_path.name):
            continue
        distance = by_directory.get(inner_path.parent)
        if distance is not None:
            found.append((candidate, distance))
    found.sort(key=lambda item: (item[1], item[0]))
    return found


def _split_container(logical_path: str) -> tuple[str, str]:
    """Split ``Outer.ipa!/inner/path`` into (``Outer.ipa!/``, ``inner/path``)."""
    head, sep, tail = logical_path.rpartition(ARCHIVE_SEPARATOR)
    return (head + sep, tail) if sep else ("", logical_path)


def _search_directories(start: PurePosixPath, max_distance: int) -> list[PurePosixPath]:
    directories = [start]
    current = start
    for _ in range(max_distance):
        if current.suffix.lower() in BUNDLE_SUFFIXES:
            break
        parent = current.parent
        if parent == current:
            break
        directories.append(parent)
        current = parent
    return directories
