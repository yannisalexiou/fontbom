# fontbom design

Approved 2026-09-22. This document describes the MVP. Later phases are listed at the end and are
out of scope until the MVP ships.

## Purpose

Find every font bundled in a mobile app or its source repository, extract the license metadata
the font carries, classify it conservatively, and cross-reference it against code. Existing font
license scanners cover websites and PDFs. Nothing covers `.ipa`, `.apk` and `.aab`.

## Non-goals for the MVP

- Fetching anything from the network.
- Deciding whether a license is legally sufficient. The tool reports evidence.
- Decompiling Swift, Kotlin, Dalvik or Android binary XML.
- Identifying renamed fonts by glyph shape.

## Pipeline

```
input path
  └─ inputs.walker      yields FileEntry(logical_path, open(), size)
       └─ fonts.detect       extension or magic bytes -> candidate
            └─ fonts.metadata   fontTools -> FontFace records (one per face in a collection)
                 └─ scanner      dedupe by sha256, aggregate paths
                      └─ licenses.classify   status, spdx, evidence
                           └─ references.*   scan sources and binaries, match names
                                └─ report.*  JSON / CSV / Markdown, disclaimer, --fail-on
```

## Inputs

`inputs.walker.walk(path, limits)` yields `FileEntry` objects for every regular file reachable
from `path`.

- A directory is walked recursively. Symlinks are not followed.
- Directory bundles (`.app`, `.xcframework`, `.framework`, `.bundle`) are plain directories.
- Zip-family archives (`.ipa`, `.apk`, `.aab`, `.aar`, `.jar`, `.zip`) are opened with
  `zipfile`. Members are extracted to a scan-scoped temporary directory that is deleted when the
  scan finishes. Nested archives inside archives are extracted and walked in turn.
- Logical paths use `!/` between an archive and its member:
  `App.ipa!/Payload/App.app/Frameworks/Vendor.framework/Font.ttf`.
- Limits, all configurable and all with defaults: maximum nesting depth 5, maximum total
  extracted bytes 2 GiB, maximum member count 200 000, and a compression-ratio check per member.
  Exceeding a limit raises `LimitExceeded`, which the CLI reports as exit code 2.
- Zip member names are sanitised: absolute paths and `..` components are rejected.

## Detection

`fonts.detect.detect(entry)` returns a `FontFormat` or `None`.

1. Extension match: `.ttf .otf .ttc .otc .woff .woff2`.
2. Otherwise read the first 4 bytes and compare with the known magic values:

| bytes         | format          |
|---------------|-----------------|
| `00 01 00 00` | TrueType        |
| `OTTO`        | OpenType/CFF    |
| `true`        | TrueType (Mac)  |
| `ttcf`        | Collection      |
| `wOFF`        | WOFF            |
| `wOF2`        | WOFF2           |

Files with a font extension whose magic does not match are still passed to metadata extraction
and fail there with a recorded error. Files with no font extension and no magic are skipped.

## Metadata

`fonts.metadata.read_faces(bytes, logical_path)` returns a list of `FontFace`. A collection
yields one face per member font; every face shares the container's sha256 and path.

Per face:

- `names`: name IDs 0, 1, 2, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 16, 17. The English Windows record is
  preferred, then any Windows record, then any Mac record. Decoding errors leave the ID absent.
- `fs_type`: raw OS/2 `fsType` integer, plus a decoded `embedding` value:
  `installable` (0), `restricted` (bit 0x0002 with neither 0x0004 nor 0x0008 set),
  `preview_print` (0x0004), `editable` (0x0008). The least restrictive set bit wins, following
  the OpenType specification. `no_subsetting` (0x0100) and `bitmap_only` (0x0200) are recorded
  as flags.
- `vendor_id`: OS/2 `achVendID`, stripped.
- `version`: `head.fontRevision` formatted to three decimals, and name ID 5 when present.
- `format`: from detection.
- `errors`: list of strings. A face that fails to parse still produces a record with the
  sha256, path, format and the error.

fontTools is opened lazily (`lazy=True`) and only the `name`, `OS/2` and `head` tables are read.

## Records

```python
@dataclass
class FontRecord:
    sha256: str
    size: int
    format: FontFormat
    paths: list[str]  # every logical path, sorted
    faces: list[FontFace]  # one for a single font, several for a collection
    license: LicenseResult
    references: list[Reference]
    referenced: bool


@dataclass
class LicenseResult:
    status: Literal["open", "commercial", "restricted", "unknown"]
    spdx: str | None
    embedding: Embedding
    evidence: list[Evidence]  # (source, excerpt); source is "name_id_13", "name_id_14",
    # "adjacent:<path>", "fs_type", "vendor_hint"
    notes: list[str]  # e.g. "copyleft", "parse error"


@dataclass
class ScanResult:
    tool: str  # "fontbom 0.1.0"
    scanned_at: str  # ISO 8601 UTC
    input: str
    fonts: list[FontRecord]
    unbundled_references: list[Reference]
    summary: dict[str, int]  # counts per status, referenced/unreferenced
    disclaimer: str
```

Dedupe key is the sha256 of the file bytes. The same font under two paths yields one record
with two paths.

## License classification

`licenses.classify.classify(record, adjacent_files)` evaluates sources in order and stops at
the first source that matches any rule. Within one source, commercial wording beats open wording,
so a field that mentions both is `commercial`.

1. Name ID 14 (license URL) against the URL rules.
2. Name ID 13 (license description) against the text rules.
3. Adjacent license files: `OFL.txt`, `OFL-FAQ.txt`, `LICENSE*`, `LICENCE*`, `COPYING*`,
   `UFL.txt`, `EULA*`, in the font's own directory, then parent directories up to three levels
   or the nearest archive or bundle boundary, whichever comes first. Generic names (`LICENSE`,
   `COPYING`) only count from the font's own directory, because a repository license describes
   the code; `OFL*`, `UFL*` and any file whose text mentions fonts count up to the distance
   limit. Nearest file first. The file used is named in the evidence.
4. Vendor and copyright hints. These never produce `open`. They can produce `commercial` when
   name ID 13 or 0 contains explicit commercial EULA language.
5. Otherwise `unknown`.

Rules are a table in `licenses.rules`. Initial rows:

| SPDX                           | status | matched on                                             |
|--------------------------------|--------|--------------------------------------------------------|
| OFL-1.1                        | open   | "SIL Open Font License", "OFL", `scripts.sil.org/OFL`, `openfontlicense.org` |
| Apache-2.0                     | open   | "Apache License, Version 2.0", `apache.org/licenses/LICENSE-2.0` |
| UFL-1.0                        | open   | "Ubuntu Font Licence", `font.ubuntu.com/ufl`            |
| MIT                            | open   | "MIT License", "Permission is hereby granted, free of charge" |
| Bitstream-Vera                 | open   | "Bitstream Vera Fonts Copyright"                        |
| GPL-2.0-or-later / GPL-3.0     | open   | "GNU General Public License"; note `copyleft`; SPDX gets `-with-font-exception` only when "font exception" appears |
| CC0-1.0                        | open   | "CC0", `creativecommons.org/publicdomain/zero`          |
| (none)                         | commercial | "End User License Agreement", "licensed to", "purchase", "number of users", "commercial license", "All rights reserved" combined with any of the previous |

"All rights reserved" alone is `unknown`, not `commercial`.

`fsType` is evaluated independently. If embedding is `restricted`, status becomes `restricted`
regardless of license text, because the tool must flag it and `--fail-on restricted` must work.
The license evidence is still recorded so the report shows both facts.

## References

Each scanner in `references/` takes a `FileEntry` and yields `Reference(name, kind, source,
line, confidence)`. `confidence` is `high` for a source-code pattern and `low` for a binary
string match.

| module          | files                          | patterns                                                                 |
|-----------------|--------------------------------|--------------------------------------------------------------------------|
| ios.py          | `.swift .m .mm .h .plist .storyboard .xib` | `UIFont(name: "X"`, `UIFont.init(name:`, `fontWithName:@"X"`, `Font.custom("X"`, `UIAppFonts` array entries, `CTFontManagerRegister*` file names, `customFontName="X"` in storyboards |
| android.py      | `.kt .java .xml`               | `res/font/*.ttf` file names, `@font/x`, `android:fontFamily="x"`, `app:fontFamily`, `Typeface.createFromAsset(…, "fonts/X.ttf")`, `ResourcesCompat.getFont`, `FontFamily(Font(R.font.x))` |
| flutter.py      | `pubspec.yaml`                 | `fonts:` block: `family:` and `asset:` entries                            |
| react_native.py | `.js .jsx .ts .tsx react-native.config.js package.json` | `require('…/X.ttf')`, `fontFamily: 'X'`, `assets: ['./assets/fonts']` |
| web.py          | `.css .scss .html`             | `@font-face { font-family: "X"; src: url(…) }`, `fonts.googleapis.com/css?family=X` and `css2?family=X` (parsed only) |
| binary.py       | Mach-O executables, `.dex`, `resources.arsc`, `.so` | presence of each bundled font's family, full and PostScript name as ASCII or UTF-16LE bytes |

`references.match.link(fonts, references)` normalises names (lowercase, strip spaces, hyphens
and underscores, drop a trailing file extension) and matches against family (1), full name (4),
PostScript name (6) and typographic family (16). Results:

- `record.references` and `record.referenced` for bundled fonts.
- `ScanResult.unbundled_references`: references whose name matched no bundled font. Generic
  system font names (`System`, `Helvetica`, `Roboto`, `sans-serif`, `monospace`, and the CSS
  generics) are filtered out with a small allowlist so they do not appear as missing fonts.

Binary scanning only runs for fonts already discovered, so it can never introduce a reference
to an unbundled font.

Binary search cost is passes x bytes, at about 1 GB/s per pass. Two measures keep it small:

- Containment. Only names that contain no other name are searched over the whole file. At
  every hit, the longer names that contain the found name are checked at the offset where they
  would have to start. This is exact and typically turns four names per weight and many weights
  per family into one or two passes per family.
- A process pool, `--jobs` (default CPU count), splits work by file and, for files over 1 MiB,
  by needle subset, so one large executable uses every worker. The pool is only started when
  bytes x names exceeds a threshold (about two seconds of serial work) because worker start-up
  costs a few hundred milliseconds. Results are identical to the serial path.

Rejected after measurement: a single regex alternation of all names (no faster than
sequential passes when first letters differ), and collapsing binaries to printable runs before
searching (the collapse pass costs more than it saves on real binaries).

## Reports

Every reporter takes a `ScanResult` and returns a string. Every output includes
`disclaimer.TEXT`:

> fontbom reports metadata found inside font files and adjacent license files. It is not legal
> advice. Verify license terms with the font vendor or your legal team.

- Terminal: default when stdout is a TTY. Header, summary counts, an aligned font table that
  drops optional columns on narrow windows and left-truncates paths, unreferenced fonts, and
  referenced-but-unbundled names grouped case-insensitively with counts, capped at twenty rows
  with a pointer to JSON. Color via click only when writing to a TTY.
- JSON: the `ScanResult` as a stable, sorted structure with a `schema_version` field.
- CSV: one row per font record with `sha256, status, spdx, embedding, family, postscript_name,
  vendor_id, version, referenced, path_count, paths` (paths joined with `;`). The disclaimer is a
  leading `#` comment line.
- Markdown: summary table, one table of fonts, a section for unreferenced bundled fonts, a
  section for referenced-but-unbundled names, and the disclaimer at the end.

## CLI

```
fontbom scan PATH [--format terminal|json|csv|markdown] [--output FILE]
                  [--fail-on STATUS[,STATUS...]] [--max-depth N] [--max-bytes N]
                  [--max-entries N] [--no-references] [--jobs N]
                  [--progress|--no-progress] [--quiet]
fontbom --version
```

Exit codes: 0 clean, 1 at least one font matched a `--fail-on` status, 2 usage error, unreadable
input or a limit exceeded. `--fail-on` accepts `open`, `commercial`, `restricted`, `unknown`,
and `unreferenced`.

## Testing

- `tests/conftest.py` provides `make_font(...)` which builds a valid TTF, OTF, WOFF, WOFF2 or
  TTC in memory with fontTools' FontBuilder, with full control over name IDs and `fsType`.
- `tests/conftest.py` provides bundle builders that write synthetic `.ipa`, `.apk`, `.aab`,
  `.aar`, `.xcframework` layouts with `zipfile`, including nested archives.
- `tests/fixtures/fonts/` contains two small real OFL fonts from Google Fonts with their
  `OFL.txt` for integration realism.
- Reporters have golden-file tests.
- The suite runs with `filterwarnings = error`.

## Later phases

SARIF output. CycloneDX and SPDX output. A license-evidence file that links font sha256 values to
purchase records. A curated knowledge base of font families and their licenses. Glyph
fingerprinting to identify renamed fonts.
