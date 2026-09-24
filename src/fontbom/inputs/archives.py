"""Safe extraction of zip-family archives (.ipa .apk .aab .aar .jar .zip)."""

from __future__ import annotations

import zipfile
from pathlib import Path, PurePosixPath

from fontbom.inputs.limits import Budget, UnsafeMember

ARCHIVE_EXTENSIONS: frozenset[str] = frozenset({".ipa", ".apk", ".aab", ".zip", ".aar", ".jar"})

CHUNK = 1024 * 1024


def is_archive(path: Path) -> bool:
    """True for a zip-family extension whose content really is a zip."""
    return path.suffix.lower() in ARCHIVE_EXTENSIONS and zipfile.is_zipfile(path)


def safe_member_path(name: str) -> PurePosixPath:
    """Normalise a member name and reject anything that could escape the target directory."""
    normalised = name.replace("\\", "/")
    if normalised.startswith("/"):
        raise UnsafeMember(f"absolute member path: {name!r}")
    parts = PurePosixPath(normalised).parts
    if ".." in parts or any(part == "" for part in parts):
        raise UnsafeMember(f"member path escapes archive: {name!r}")
    return PurePosixPath(*parts)


def extract(archive: Path, dest: Path, budget: Budget) -> None:
    """Extract every regular member of ``archive`` into ``dest`` within the budget."""
    dest.mkdir(parents=True, exist_ok=True)
    resolved_dest = dest.resolve()
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            budget.add_entry()
            target = dest / safe_member_path(info.filename)
            if not target.resolve().is_relative_to(resolved_dest):
                raise UnsafeMember(f"member path escapes archive: {info.filename!r}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                while chunk := src.read(CHUNK):
                    budget.add_bytes(len(chunk))
                    dst.write(chunk)
