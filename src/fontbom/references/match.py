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
# Font families built into iOS, normalised. They count as system fonts for iOS and web
# references, alone or followed by style words ("HelveticaNeue-Bold", "Arial-BoldMT").
IOS_SYSTEM_FAMILIES = frozenset(
    {
        "academyengravedlet", "alnile", "americantypewriter", "applesdgothicneo", "applesymbols",
        "arialhebrew", "arialroundedmtbold", "avenir", "avenirnext", "avenirnextcondensed",
        "baskerville", "bodoni72", "bodoni72oldstyle", "bodoni72smallcaps", "bodoniornaments",
        "bradleyhand", "chalkboardse", "chalkduster", "charter", "cochin", "copperplate",
        "damascus", "devanagarisangammn", "didot", "dinalternate", "dincondensed", "euphemiaucas",
        "farah", "futura", "galvji", "geezapro", "gillsans", "granthasangammn",
        "hiraginomarugothicpron", "hiraginominchopron", "hiraginosans", "hoeflertext", "kailasa",
        "kefa", "khmersangammn", "kohinoorbangla", "kohinoordevanagari", "kohinoorgujarati",
        "kohinoortelugu", "laosangammn", "malayalamsangammn", "markerfelt", "mishafi",
        "muktamahee", "myanmarsangammn", "newyork", "noteworthy", "notonastaliqurdu",
        "notosanskannada", "notosansmyanmar", "notosansoriya", "optima", "palatino", "papyrus",
        "partylet", "pingfanghk", "pingfangsc", "pingfangtc", "rockwell", "savoyelet",
        "sfcompact", "sfcompactdisplay", "sfcompactrounded", "sfcompacttext", "sfprorounded",
        "sinhalasangammn", "snellroundhand", "stixtwomath", "stixtwotext", "symbol",
        "tamilsangammn", "telugusangammn", "thonburi", "trebuchetms", "zapfdingbats", "zapfino",
    }
)  # fmt: skip
APPLE_AND_WEB_SYSTEM_FAMILIES = SYSTEM_NAMES | IOS_SYSTEM_FAMILIES
STYLE_WORDS = re.compile(
    r"(?:regular|book|roman|normal|plain|medium|semi|demi|extra|ultra|bold|heavy|black|light"
    r"|thin|hairline|italic|oblique|condensed|compressed|expanded|extended|narrow|wide|ps|mt)*"
)
MATCH_ONLY_WHEN_SPACED = frozenset({"font-file-literal", "font-file-text"})


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
    if reference.ecosystem in ("ios", "web"):
        if key.startswith("."):  # Apple's private system names: .AppleSystemUIFont, .SFUI-Bold
            return True
        return any(
            key.startswith(family) and STYLE_WORDS.fullmatch(key[len(family) :])
            for family in APPLE_AND_WEB_SYSTEM_FAMILIES
        )
    return False


def may_be_missing(reference: Reference) -> bool:
    """Whether an unmatched reference belongs in the not-bundled list.

    A quoted string that ends in a font extension and contains whitespace is often a message
    ("Could not load X.ttf"), so it links to a bundled font but is never reported as missing.
    """
    if is_system_name(reference):
        return False
    spaced = any(c.isspace() for c in reference.name)
    return not (spaced and reference.kind in MATCH_ONLY_WHEN_SPACED)


def link(records: Sequence[FontRecord], references: Iterable[Reference]) -> list[Reference]:
    """Attach matching references to records; return the references that matched nothing."""
    index: dict[str, list[FontRecord]] = {}
    for record in records:
        for key in record_keys(record):
            index.setdefault(key, []).append(record)

    # A set per record keeps duplicate removal linear; fonts can collect thousands of references.
    attached: dict[int, set[Reference]] = {}
    unbundled: set[Reference] = set()
    for reference in references:
        matches = index.get(normalize(reference.name))
        if matches:
            for record in matches:
                seen = attached.get(id(record))
                if seen is None:
                    seen = attached[id(record)] = set(record.references)
                if reference not in seen:
                    seen.add(reference)
                    record.references.append(reference)
        elif may_be_missing(reference):
            unbundled.add(reference)
    return sorted(unbundled, key=lambda r: (r.name, r.ecosystem, r.source, r.line or 0))
