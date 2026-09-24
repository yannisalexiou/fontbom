"""CSV output: one row per distinct font, disclaimer as a leading comment line."""

from __future__ import annotations

import csv
import io

from fontbom.models import ScanResult
from fontbom.report.disclaimer import TEXT as DISCLAIMER

COLUMNS = (
    "sha256",
    "status",
    "spdx",
    "embedding",
    "family",
    "full_name",
    "postscript_name",
    "vendor_id",
    "version",
    "format",
    "referenced",
    "reference_count",
    "path_count",
    "paths",
)


def render_csv(result: ScanResult) -> str:
    buffer = io.StringIO()
    buffer.write(f"# {DISCLAIMER}\n")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS)
    for record in result.fonts:
        face = record.primary
        writer.writerow(
            [
                record.sha256,
                record.license.status.value,
                record.license.spdx or "",
                record.license.embedding.value,
                face.family or "",
                face.full_name or "",
                face.postscript_name or "",
                face.vendor_id or "",
                face.version or "",
                record.format.value,
                "true" if record.referenced else "false",
                len(record.references),
                len(record.paths),
                ";".join(record.paths),
            ]
        )
    return buffer.getvalue()
