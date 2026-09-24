"""Data model shared across the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from fontbom.fonts.detect import FontFormat


class Status(StrEnum):
    """License status. The default is UNKNOWN; OPEN needs positive evidence."""

    OPEN = "open"
    COMMERCIAL = "commercial"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class Embedding(StrEnum):
    """OS/2 fsType embedding permission, decoded."""

    INSTALLABLE = "installable"
    RESTRICTED = "restricted"
    PREVIEW_PRINT = "preview-print"
    EDITABLE = "editable"
    UNKNOWN = "unknown"


@dataclass
class FontFace:
    """Metadata for one face. A collection produces one FontFace per member."""

    index: int
    format: FontFormat
    names: dict[int, str] = field(default_factory=dict)
    fs_type: int | None = None
    embedding: Embedding = Embedding.UNKNOWN
    no_subsetting: bool = False
    bitmap_only: bool = False
    vendor_id: str | None = None
    version: str | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def family(self) -> str | None:
        return self.names.get(1)

    @property
    def full_name(self) -> str | None:
        return self.names.get(4)

    @property
    def postscript_name(self) -> str | None:
        return self.names.get(6)

    @property
    def typographic_family(self) -> str | None:
        return self.names.get(16)


class Confidence(StrEnum):
    HIGH = "high"  # a source-code pattern
    LOW = "low"  # a string found inside a compiled binary


@dataclass(frozen=True)
class Reference:
    """A place where code names a font, by family, PostScript name or file name."""

    name: str
    kind: str
    ecosystem: str
    source: str
    line: int | None
    confidence: Confidence


@dataclass(frozen=True)
class Evidence:
    """Where a classification signal came from and what it said."""

    source: str  # "name_id_13", "name_id_14", "adjacent:<path>", "fs_type"
    excerpt: str


@dataclass
class LicenseResult:
    status: Status = Status.UNKNOWN
    spdx: str | None = None
    embedding: Embedding = Embedding.UNKNOWN
    evidence: list[Evidence] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class FontRecord:
    """One distinct font file (by sha256) and every place it was found."""

    sha256: str
    size: int
    format: FontFormat
    paths: list[str]
    faces: list[FontFace]
    license: LicenseResult = field(default_factory=LicenseResult)
    references: list[Reference] = field(default_factory=list)

    @property
    def primary(self) -> FontFace:
        return self.faces[0]

    @property
    def referenced(self) -> bool:
        return bool(self.references)


@dataclass
class ScanResult:
    """Everything one scan produced. Reporters render this."""

    tool: str
    scanned_at: str
    input: str
    fonts: list[FontRecord]
    unbundled_references: list[Reference]

    @property
    def summary(self) -> dict[str, int]:
        counts = {status.value: 0 for status in Status}
        for record in self.fonts:
            counts[record.license.status.value] += 1
        referenced = sum(1 for record in self.fonts if record.referenced)
        return {
            "fonts": len(self.fonts),
            **counts,
            "referenced": referenced,
            "unreferenced": len(self.fonts) - referenced,
            "unbundled_references": len(self.unbundled_references),
        }
