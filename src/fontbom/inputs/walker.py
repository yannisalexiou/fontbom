"""Walk directories and archives, yielding every regular file with a logical path."""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from fontbom.inputs.archives import extract, is_archive
from fontbom.inputs.limits import Budget, Limits

ARCHIVE_SEPARATOR = "!/"
SKIPPED_DIRECTORIES: frozenset[str] = frozenset({".git"})
# SwiftPM caches that never hold anything that ships: SourceKit-LSP index builds and bare clones
# of dependency repositories. .build/checkouts and .build/artifacts stay, because the fonts and
# binaries that ship with dependencies live there.
SKIPPED_CACHE_DIRECTORIES: frozenset[tuple[str, str]] = frozenset(
    {(".build", "index-build"), (".build", "repositories")}
)
HEADER_LENGTH = 8


@dataclass
class FileEntry:
    """A regular file reachable from the scan input.

    ``logical_path`` is relative to the input and uses ``!/`` between an archive and its
    members, for example ``App.ipa!/Payload/App.app/Fonts/A.ttf``. ``real_path`` is where the
    bytes live on disk, which for archive members is inside the scan's working directory.
    ``header`` holds the first bytes of the file so detection never reopens it.
    """

    logical_path: str
    real_path: Path
    size: int
    depth: int
    header: bytes = field(default=b"", repr=False)
    _held: bytes | None = field(default=None, init=False, repr=False, compare=False)

    def read_header(self, length: int = 4) -> bytes:
        if length <= len(self.header) or length > self.size:
            return self.header[:length]
        with self.real_path.open("rb") as fh:
            return fh.read(length)

    def read(self) -> bytes:
        if self._held is not None:
            return self._held
        return self.real_path.read_bytes()

    @contextmanager
    def held(self) -> Iterator[None]:
        """Keep the bytes in memory for the block, so several readers share one disk read."""
        self._held = self.real_path.read_bytes()
        try:
            yield
        finally:
            self._held = None


def walk(
    path: Path, limits: Limits, workdir: Path, exclude: Sequence[str] = ()
) -> Iterator[FileEntry]:
    """Yield a FileEntry for every regular file under ``path``, expanding archives.

    Archive members are extracted under ``workdir``; the caller owns that directory's lifetime.
    ``exclude`` holds shell-style patterns. A pattern without ``/`` matches a file or directory
    name at any depth; a pattern with ``/`` matches the logical path. Excluded directories are
    not entered and excluded archives are not opened.
    Raises ArchiveError subclasses when a limit is exceeded or a member is unsafe.
    """
    walker = _Walker(Budget(limits), workdir, exclude)
    if path.is_dir():
        yield from walker.walk_dir(str(path), prefix="", depth=0)
    else:
        yield from walker.visit_file(str(path), logical=path.name, depth=0)


class _Walker:
    def __init__(self, budget: Budget, workdir: Path, exclude: Sequence[str] = ()) -> None:
        self.budget = budget
        self.workdir = workdir
        self.extracted = 0
        self.exclude = tuple(p.strip().rstrip("/") for p in exclude if p.strip().strip("/"))

    def excluded(self, logical: str) -> bool:
        name = logical.rsplit("/", 1)[-1]
        return any(
            fnmatch.fnmatchcase(logical if "/" in pattern else name, pattern)
            for pattern in self.exclude
        )

    def walk_dir(self, root: str, prefix: str, depth: int) -> Iterator[FileEntry]:
        """Depth-first, sorted, without following symlinks. Uses scandir to keep syscalls low."""
        stack: list[tuple[str, str]] = [(root, prefix)]
        while stack:
            directory, logical_prefix = stack.pop()
            try:
                with os.scandir(directory) as it:
                    children = sorted(it, key=lambda e: e.name)
            except OSError:
                continue
            subdirs: list[tuple[str, str]] = []
            parent = os.path.basename(directory)
            for child in children:
                logical = f"{logical_prefix}{child.name}"
                if child.is_symlink() or self.excluded(logical):
                    continue
                if child.is_dir(follow_symlinks=False):
                    skipped = child.name in SKIPPED_DIRECTORIES or (
                        (parent, child.name) in SKIPPED_CACHE_DIRECTORIES
                    )
                    if not skipped:
                        subdirs.append((child.path, f"{logical}/"))
                elif child.is_file(follow_symlinks=False):
                    yield from self.visit_file(
                        child.path, logical, depth, size=child.stat(follow_symlinks=False).st_size
                    )
            stack.extend(reversed(subdirs))

    def visit_file(
        self, real: str, logical: str, depth: int, size: int | None = None
    ) -> Iterator[FileEntry]:
        real_path = Path(real)
        if is_archive(real_path):
            self.budget.check_depth(depth + 1)
            self.extracted += 1
            dest = self.workdir / f"{self.extracted:06d}"
            extract(real_path, dest, self.budget)
            yield from self.walk_dir(
                str(dest), prefix=f"{logical}{ARCHIVE_SEPARATOR}", depth=depth + 1
            )
            return
        if size is None:
            size = real_path.stat().st_size
        header = b""
        if size:
            with open(real, "rb") as fh:
                header = fh.read(HEADER_LENGTH)
        yield FileEntry(
            logical_path=logical, real_path=real_path, size=size, depth=depth, header=header
        )
