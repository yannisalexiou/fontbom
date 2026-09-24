"""JSON output: a stable, sorted, versioned structure."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from fontbom.models import FontFace, FontRecord, Reference, ScanResult
from fontbom.report.disclaimer import TEXT as DISCLAIMER

SCHEMA_VERSION = 1


def to_dict(result: ScanResult) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": result.tool,
        "scanned_at": result.scanned_at,
        "input": result.input,
        "disclaimer": DISCLAIMER,
        "summary": result.summary,
        "fonts": [_record(record) for record in result.fonts],
        "unbundled_references": [_reference(r) for r in result.unbundled_references],
    }


def render_json(result: ScanResult) -> str:
    return json.dumps(to_dict(result), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _record(record: FontRecord) -> dict[str, Any]:
    return {
        "sha256": record.sha256,
        "size": record.size,
        "format": record.format.value,
        "paths": list(record.paths),
        "faces": [_face(face) for face in record.faces],
        "license": {
            "status": record.license.status.value,
            "spdx": record.license.spdx,
            "embedding": record.license.embedding.value,
            "evidence": [asdict(e) for e in record.license.evidence],
            "notes": list(record.license.notes),
        },
        "referenced": record.referenced,
        "references": [_reference(r) for r in record.references],
    }


def _face(face: FontFace) -> dict[str, Any]:
    return {
        "index": face.index,
        "names": {str(k): v for k, v in sorted(face.names.items())},
        "family": face.family,
        "full_name": face.full_name,
        "postscript_name": face.postscript_name,
        "fs_type": face.fs_type,
        "embedding": face.embedding.value,
        "no_subsetting": face.no_subsetting,
        "bitmap_only": face.bitmap_only,
        "vendor_id": face.vendor_id,
        "version": face.version,
        "errors": list(face.errors),
    }


def _reference(reference: Reference) -> dict[str, Any]:
    data = asdict(reference)
    data["confidence"] = reference.confidence.value
    return data
