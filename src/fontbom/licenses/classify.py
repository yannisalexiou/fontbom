"""Conservative license classification from font metadata and adjacent license files."""

from __future__ import annotations

from collections.abc import Sequence

from fontbom.licenses.adjacent import AdjacentFile
from fontbom.licenses.rules import (
    COMMERCIAL_TEXT_RULE,
    COMMERCIAL_URL_RULE,
    OPEN_RULES,
    Rule,
    gpl_spdx,
)
from fontbom.models import Embedding, Evidence, FontRecord, LicenseResult, Status

EXCERPT_LENGTH = 240
NAME_ID_LICENSE_TEXT = 13
NAME_ID_LICENSE_URL = 14


def classify(record: FontRecord, adjacent: Sequence[AdjacentFile]) -> LicenseResult:
    """Decide a status for ``record``.

    Sources are consulted in order: name ID 14, name ID 13, then adjacent license files from
    nearest to farthest. The first source that matches any rule decides. Within a source,
    commercial wording beats open wording. Generic license files (LICENSE, COPYING) only count
    from the font's own directory; font-specific ones (OFL.txt, UFL.txt, or any file mentioning
    fonts) count up to the distance limit. A restricted fsType overrides the status.
    """
    result = LicenseResult()

    for face in record.faces:
        url = face.names.get(NAME_ID_LICENSE_URL)
        if url and _decide(result, url, f"name_id_{NAME_ID_LICENSE_URL}", url_rules=True):
            break
        text = face.names.get(NAME_ID_LICENSE_TEXT)
        if text and _decide(result, text, f"name_id_{NAME_ID_LICENSE_TEXT}", url_rules=False):
            break
    else:
        for item in sorted(adjacent, key=lambda a: a.distance):
            if not _adjacent_applies(item) or not _decide(
                result, item.text, f"adjacent:{item.path}", url_rules=False
            ):
                continue
            break

    _apply_embedding(record, result)
    for face in record.faces:
        result.notes.extend(face.errors)
    return result


def _decide(result: LicenseResult, text: str, source: str, *, url_rules: bool) -> bool:
    commercial = COMMERCIAL_URL_RULE if url_rules else COMMERCIAL_TEXT_RULE
    if commercial.search(text):
        result.status = Status.COMMERCIAL
        result.spdx = None
        result.evidence.append(Evidence(source, _excerpt(text)))
        return True
    rule = _first_open_rule(text)
    if rule is None:
        return False
    result.status = Status.OPEN
    result.spdx = gpl_spdx(text) if rule.spdx == "GPL" else rule.spdx
    result.evidence.append(Evidence(source, _excerpt(text)))
    result.notes.extend(n for n in rule.notes if n not in result.notes)
    return True


def _first_open_rule(text: str) -> Rule | None:
    for rule in OPEN_RULES:
        if rule.search(text):
            return rule
    return None


def _adjacent_applies(item: AdjacentFile) -> bool:
    if item.distance == 0:
        return True
    name = item.path.rsplit("/", 1)[-1].upper()
    if name.startswith(("OFL", "UFL")):
        return True
    return "font" in item.text.lower()


def _apply_embedding(record: FontRecord, result: LicenseResult) -> None:
    embeddings = [face.embedding for face in record.faces]
    if Embedding.RESTRICTED in embeddings:
        result.embedding = Embedding.RESTRICTED
    elif Embedding.UNKNOWN in embeddings or not embeddings:
        result.embedding = Embedding.UNKNOWN
    else:
        # Report the most restrictive real permission among the faces.
        order = [Embedding.PREVIEW_PRINT, Embedding.EDITABLE, Embedding.INSTALLABLE]
        result.embedding = next(e for e in order if e in embeddings)

    if result.embedding is Embedding.RESTRICTED:
        result.status = Status.RESTRICTED
        fs_types = sorted({f.fs_type for f in record.faces if f.fs_type is not None})
        result.evidence.append(
            Evidence("fs_type", "restricted license embedding: " + ", ".join(map(hex, fs_types)))
        )
    elif result.embedding in (Embedding.PREVIEW_PRINT, Embedding.EDITABLE):
        result.notes.append(f"embedding: {result.embedding.value}")


def _excerpt(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= EXCERPT_LENGTH else flat[: EXCERPT_LENGTH - 1] + "…"
