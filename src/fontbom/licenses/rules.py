"""Pattern table mapping license wording and URLs to SPDX identifiers and statuses.

Every pattern is a case-insensitive regular expression. Open rules need positive wording;
commercial rules need explicit EULA wording or a known commercial vendor license URL.
Nothing here matches on family names or vendor names alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from fontbom.models import Status


@dataclass(frozen=True)
class Rule:
    spdx: str | None
    status: Status
    patterns: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def search(self, text: str) -> re.Match[str] | None:
        for pattern in self.patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match
        return None


OPEN_RULES: tuple[Rule, ...] = (
    Rule(
        "OFL-1.1",
        Status.OPEN,
        (
            r"SIL\s+Open\s+Font\s+License",
            r"\bOpen\s+Font\s+License\b",
            r"scripts\.sil\.org/OFL",
            r"openfontlicense\.org",
            r"\bOFL(?:[-\s]?1\.1)?\b",
        ),
    ),
    Rule(
        "Apache-2.0",
        Status.OPEN,
        (
            r"Apache\s+License,?\s+Version\s+2\.0",
            r"apache\.org/licenses/LICENSE-2\.0",
            r"\bApache[-\s]2\.0\b",
        ),
    ),
    Rule(
        "UFL-1.0",
        Status.OPEN,
        (
            r"Ubuntu\s+Font\s+Licen[cs]e",
            r"font\.ubuntu\.com/(?:ufl|licen[cs]e)",
            r"ubuntu\.com/legal/font-licen[cs]e",
        ),
    ),
    Rule(
        "MIT",
        Status.OPEN,
        (
            r"\bMIT\s+Licen[cs]e\b",
            r"Permission\s+is\s+hereby\s+granted,\s+free\s+of\s+charge",
            r"opensource\.org/licenses/MIT",
        ),
    ),
    Rule("Bitstream-Vera", Status.OPEN, (r"Bitstream\s+Vera\s+Fonts?\s+Copyright",)),
    Rule(
        "CC0-1.0",
        Status.OPEN,
        (r"\bCC0\b", r"creativecommons\.org/publicdomain/zero"),
    ),
    Rule(
        "LGPL-2.1-or-later",
        Status.OPEN,
        (r"GNU\s+Lesser\s+General\s+Public\s+License", r"\bLGPL\b"),
        notes=("copyleft",),
    ),
    Rule(
        "GPL",
        Status.OPEN,
        (r"GNU\s+General\s+Public\s+License", r"\bGPL\b"),
        notes=("copyleft",),
    ),
)

COMMERCIAL_TEXT_RULE = Rule(
    None,
    Status.COMMERCIAL,
    (
        r"End[-\s]User\s+Licen[cs]e\s+Agreement",
        r"\bEULA\b",
        r"\blicensed\s+to\b",
        r"\bpurchas(?:e|ed|ing)\b",
        r"number\s+of\s+(?:users|workstations|computers|devices|CPUs)",
        r"\bcommercial\s+licen[cs]e\b",
    ),
)

COMMERCIAL_VENDOR_DOMAINS: tuple[str, ...] = (
    "myfonts.com",
    "fonts.com",
    "monotype.com",
    "linotype.com",
    "typography.com",
    "fontshop.com",
    "fontspring.com",
    "commercialtype.com",
    "typenetwork.com",
    "klim.co.nz",
    "processtypefoundry.com",
    "fontfont.com",
)

COMMERCIAL_URL_RULE = Rule(
    None,
    Status.COMMERCIAL,
    tuple(
        rf"(?:^|[^a-z0-9-]){re.escape(domain)}(?:[/:?#]|$)" for domain in COMMERCIAL_VENDOR_DOMAINS
    ),
)


def gpl_spdx(text: str) -> str:
    """Resolve the GPL placeholder into a version-specific identifier."""
    version = "3.0" if re.search(r"version\s*3|GPLv3|GPL-3", text, re.IGNORECASE) else "2.0"
    spdx = f"GPL-{version}-or-later"
    if re.search(r"font\s+exception", text, re.IGNORECASE):
        spdx += " WITH Font-exception-2.0"
    return spdx
