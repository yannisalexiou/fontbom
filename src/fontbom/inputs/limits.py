"""Resource limits for archive expansion, and the errors raised when they are hit."""

from __future__ import annotations

from dataclasses import dataclass


class ArchiveError(Exception):
    """Base class for input problems that should stop the scan."""


class LimitExceeded(ArchiveError):
    """A configured limit was exceeded while expanding archives."""


class UnsafeMember(ArchiveError):
    """An archive member would escape its extraction directory."""


@dataclass(frozen=True)
class Limits:
    max_depth: int = 5
    max_total_bytes: int = 2 * 1024**3
    max_entries: int = 200_000


class Budget:
    """Mutable counters checked against a Limits instance during one scan."""

    def __init__(self, limits: Limits) -> None:
        self.limits = limits
        self.total_bytes = 0
        self.entries = 0

    def add_entry(self) -> None:
        self.entries += 1
        if self.entries > self.limits.max_entries:
            raise LimitExceeded(f"more than {self.limits.max_entries} archive entries")

    def add_bytes(self, count: int) -> None:
        self.total_bytes += count
        if self.total_bytes > self.limits.max_total_bytes:
            raise LimitExceeded(f"more than {self.limits.max_total_bytes} extracted bytes")

    def check_depth(self, depth: int) -> None:
        if depth > self.limits.max_depth:
            raise LimitExceeded(f"archive nesting depth exceeds {self.limits.max_depth}")
