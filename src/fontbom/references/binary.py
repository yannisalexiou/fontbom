"""Low-confidence references: font names found as strings inside compiled binaries.

Searching a large executable once per name is the expensive part of a scan, so the search is
organised around containment. Most of a font's names contain its family name ("Roboto Bold"
and "Roboto-Bold" both contain "Roboto"). Only the minimal names, those that contain no other
name, are searched across the whole file. Every hit is then checked against the longer names
that contain it, at the exact offset where they would have to start. The result is identical
to searching every name, with far fewer passes.
"""

from __future__ import annotations

import mmap
from collections.abc import Callable, Iterable, Iterator, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path, PurePosixPath

from fontbom.fonts.detect import detect
from fontbom.inputs.walker import FileEntry
from fontbom.models import Confidence, Reference

MIN_NAME_LENGTH = 3
MMAP_THRESHOLD = 1024 * 1024
# Serial search runs at roughly 1 GB/s per name. A process pool costs a few hundred
# milliseconds to start, so it is only used when bytes x names exceeds this.
PARALLEL_THRESHOLD = 2 * 10**9
ENCODINGS: tuple[tuple[str, int], ...] = (("utf-8", 1), ("utf-16-le", 2))

BINARY_MAGIC: tuple[bytes, ...] = (
    b"\xfe\xed\xfa\xce",  # Mach-O 32-bit big-endian
    b"\xfe\xed\xfa\xcf",  # Mach-O 64-bit big-endian
    b"\xce\xfa\xed\xfe",  # Mach-O 32-bit little-endian
    b"\xcf\xfa\xed\xfe",  # Mach-O 64-bit little-endian
    b"\xca\xfe\xba\xbe",  # Mach-O universal
    b"dex\n",  # Dalvik executable
    b"\x7fELF",  # shared objects
    b"bplist",  # binary property lists, including compiled nibs
)
BINARY_NAMES = frozenset({"resources.arsc", "resources.pb"})
BINARY_EXTENSIONS = frozenset({".so", ".dylib", ".nib", ".dex", ".arsc"})


def is_binary_candidate(entry: FileEntry) -> bool:
    path = PurePosixPath(entry.logical_path)
    header = entry.read_header(8)
    if detect(entry.logical_path, header) is not None:
        return False
    if path.name.lower() in BINARY_NAMES or path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    return any(header.startswith(magic) for magic in BINARY_MAGIC)


class BinaryScanner:
    """Search binaries for the names of fonts that were already discovered."""

    ecosystem = "binary"

    def __init__(self, names: Iterable[str]) -> None:
        unique = sorted({n.strip() for n in names if len(n.strip()) >= MIN_NAME_LENGTH})
        self.minimal = [n for n in unique if not any(o != n and o in n for o in unique)]
        # For each minimal name: the longer names containing it and where it sits inside them.
        self.expansions: dict[str, list[tuple[str, int]]] = {
            m: [(n, n.index(m)) for n in unique if n != m and m in n] for m in self.minimal
        }

    def accepts(self, entry: FileEntry) -> bool:
        return bool(self.minimal) and is_binary_candidate(entry)

    def scan(self, entry: FileEntry) -> Iterator[Reference]:
        found = self.search_file(entry.real_path, entry.size)
        yield from _references(entry.logical_path, found)

    def search_file(self, path: Path, size: int, minimal: Sequence[str] | None = None) -> set[str]:
        """Return the names found in the file at ``path``, restricted to ``minimal`` needles."""
        if size == 0:
            return set()
        if size < MMAP_THRESHOLD:
            return self._search(path.read_bytes(), minimal)
        with path.open("rb") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as view:
            return self._search(view, minimal)

    def _search(self, data: bytes | mmap.mmap, minimal: Sequence[str] | None = None) -> set[str]:
        found: set[str] = set()
        for minimal_name in self.minimal if minimal is None else minimal:
            for encoding, width in ENCODINGS:
                needle = minimal_name.encode(encoding)
                position = data.find(needle)
                if position == -1:
                    continue
                found.add(minimal_name)
                pending = [
                    (longer.encode(encoding), longer, offset * width)
                    for longer, offset in self.expansions[minimal_name]
                    if longer not in found
                ]
                while position != -1 and pending:
                    remaining = []
                    for encoded, longer, offset in pending:
                        start = position - offset
                        if start >= 0 and data[start : start + len(encoded)] == encoded:
                            found.add(longer)
                        else:
                            remaining.append((encoded, longer, offset))
                    pending = remaining
                    position = data.find(needle, position + 1)
        return found


def _references(source: str, found: set[str]) -> Iterator[Reference]:
    for name in sorted(found):
        yield Reference(name, "binary-string", "binary", source, None, Confidence.LOW)


def _search_task(path: str, size: int, names: list[str], minimal: list[str]) -> set[str]:
    """Process-pool worker: rebuild the scanner and search one file for a subset of needles."""
    return BinaryScanner(names).search_file(Path(path), size, minimal)


def scan_binaries(
    entries: Iterable[FileEntry],
    names: Iterable[str],
    jobs: int = 1,
    parallel_threshold: int = PARALLEL_THRESHOLD,
    on_file: Callable[[str], None] | None = None,
) -> list[Reference]:
    """Scan every binary candidate among ``entries``, in parallel when the work is large.

    Work is split by file and, for large files, by needle subset, so a single big executable
    still uses every worker. Results are identical to the serial scan.
    """
    scanner = BinaryScanner(names)
    report = on_file or (lambda _: None)
    candidates = [e for e in entries if scanner.accepts(e)]
    if not candidates:
        return []
    names_list = sorted({n.strip() for n in names})
    work = sum(e.size for e in candidates) * len(scanner.minimal)

    references: list[Reference] = []
    if jobs <= 1 or work < parallel_threshold:
        for entry in candidates:
            report(entry.logical_path)
            references.extend(scanner.scan(entry))
        return references

    tasks: list[tuple[FileEntry, list[str]]] = []
    for entry in candidates:
        chunks = _split(scanner.minimal, jobs if entry.size >= MMAP_THRESHOLD else 1)
        tasks.extend((entry, chunk) for chunk in chunks)
    remaining = {entry.logical_path: 0 for entry in candidates}
    for entry, _ in tasks:
        remaining[entry.logical_path] += 1
    found: dict[str, set[str]] = {entry.logical_path: set() for entry in candidates}

    with ProcessPoolExecutor(max_workers=jobs) as pool:
        futures = {
            pool.submit(_search_task, str(entry.real_path), entry.size, names_list, chunk): entry
            for entry, chunk in tasks
        }
        for future in as_completed(futures):
            entry = futures[future]
            found[entry.logical_path] |= future.result()
            remaining[entry.logical_path] -= 1
            if remaining[entry.logical_path] == 0:
                report(entry.logical_path)

    for entry in candidates:
        references.extend(_references(entry.logical_path, found[entry.logical_path]))
    return references


def _split(items: Sequence[str], parts: int) -> list[list[str]]:
    parts = max(1, min(parts, len(items)))
    return [list(items[i::parts]) for i in range(parts)]
