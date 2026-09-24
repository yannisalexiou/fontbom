"""Link references to bundled fonts by normalised name."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from fontbom.models import FontRecord, Reference

FONT_EXTENSION = re.compile(r"\.(?:ttf|otf|ttc|otc|woff2?)$", re.IGNORECASE)
SEPARATORS = re.compile(r"[\s\-_]+")
NAME_IDS_FOR_MATCHING = (1, 4, 6, 16)

# Names that mean "a platform font" and should not be reported as missing from the bundle.
SYSTEM_NAMES = frozenset(
    {
        "system",
        "systemfont",
        "systemui",
        "helvetica",
        "helveticaneue",
        "sfpro",
        "sfprotext",
        "sfprodisplay",
        "sfmono",
        "arial",
        "timesnewroman",
        "times",
        "courier",
        "couriernew",
        "georgia",
        "verdana",
        "menlo",
        "monaco",
        "inherit",
        "initial",
        "sansserif",
        "serif",
        "monospace",
        "cursive",
        "fantasy",
        # Names that appear in the default CSS font stacks of Bootstrap, Tailwind and GitHub.
        "applesystem",
        "blinkmacsystemfont",
        "segoeui",
        "uisansserif",
        "uiserif",
        "uimonospace",
        "uirounded",
        "sfmonoregular",
        "consolas",
        "liberationmono",
        "liberationsans",
        "lucidaconsole",
        "dejavusansmono",
        "cantarell",
        "oxygen",
        "applecoloremoji",
        "segoeuiemoji",
        "segoeuisymbol",
        "notocoloremoji",
        "notosans",
        "droidsans",
    }
)
ANDROID_SYSTEM_NAMES = frozenset({"roboto", "casual", "notoserif", "droidsans", "droidsansmono"})
ANDROID_SYSTEM_PREFIXES = ("sansserif", "roboto")


def normalize(name: str) -> str:
    """Lowercase, drop directories, resource prefixes, extensions and separators."""
    value = name.strip()
    if value.startswith("@font/"):
        value = value[len("@font/") :]
    value = value.replace("\\", "/").rsplit("/", 1)[-1]
    value = FONT_EXTENSION.sub("", value)
    return SEPARATORS.sub("", value).lower()


def record_keys(record: FontRecord) -> set[str]:
    keys = {
        normalize(face.names[name_id])
        for face in record.faces
        for name_id in NAME_IDS_FOR_MATCHING
        if name_id in face.names
    }
    keys.update(normalize(path) for path in record.paths)
    keys.discard("")
    return keys


def is_system_name(reference: Reference) -> bool:
    key = normalize(reference.name)
    if key in SYSTEM_NAMES:
        return True
    if reference.ecosystem == "android":
        return key in ANDROID_SYSTEM_NAMES or key.startswith(ANDROID_SYSTEM_PREFIXES)
    return False


def link(records: Sequence[FontRecord], references: Iterable[Reference]) -> list[Reference]:
    """Attach matching references to records; return the references that matched nothing."""
    index: dict[str, list[FontRecord]] = {}
    for record in records:
        for key in record_keys(record):
            index.setdefault(key, []).append(record)

    unbundled: set[Reference] = set()
    for reference in references:
        matches = index.get(normalize(reference.name))
        if matches:
            for record in matches:
                if reference not in record.references:
                    record.references.append(reference)
        elif not is_system_name(reference):
            unbundled.add(reference)
    return sorted(unbundled, key=lambda r: (r.name, r.ecosystem, r.source, r.line or 0))
