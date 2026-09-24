# fontbom

Font bill of materials for mobile apps and codebases.

`fontbom` scans `.ipa`, `.apk`, `.aab`, `.app`, `.xcframework`, `.zip` files and source
repositories for bundled fonts, extracts their license metadata, and reports which fonts are
open-licensed, commercial, embedding-restricted, or unknown. It also cross-references fonts
against code so you can see fonts that are bundled but never used, and fonts that code
references but the bundle does not contain.

Existing font license scanners cover websites and PDFs. Nothing covered app binaries.

Fully offline. Nothing is uploaded.

> fontbom reports metadata found inside font files and adjacent license files. It is not legal
> advice. Verify license terms with the font vendor or your legal team.

## Install

```
pip install fontbom
```

Requires Python 3.11 or newer.

## Usage

```
fontbom scan App.ipa
fontbom scan app-release.aab --format markdown --output fonts.md
fontbom scan . --format csv
fontbom scan App.ipa --fail-on unknown,commercial,restricted
```

Inputs: a directory, `.ipa`, `.app`, `.apk`, `.aab`, `.xcframework`, `.zip`, or a single font
file. Nested archives and bundles (`.framework`, `.bundle`, `.aar`, `.jar`, zip inside zip) are
expanded, with limits on depth, total size and member count.

Exit codes:

| Code | Meaning |
| ---- | ------- |
| 0    | Scan completed and no `--fail-on` status matched |
| 1    | At least one font matched a `--fail-on` status |
| 2    | Usage error, unreadable input, unsafe archive member, or a limit was exceeded |

`--fail-on` accepts `open`, `commercial`, `restricted`, `unknown` and `unreferenced`.

`--jobs N` sets the worker processes used to search large binaries; the default is the number
of CPUs. Small scans stay single-process because starting workers costs more than it saves.

When stdout is a terminal the default format is `terminal`: a color-coded, aligned summary
fitted to the window, with unbundled names grouped and counted. When stdout is piped or
`--output` is used the default is `json`. `--format` overrides either.

The report goes to stdout, or to the file named by `--output`. Everything else goes to stderr:
a live status line while the scan runs (on by default in a terminal, forced with `--progress`,
disabled with `--no-progress` or `--quiet`) and a one-line summary at the end. Piping stdout
therefore always yields a clean report.

## What it reports

For every distinct font (by sha256):

- every path where it appears, including inside vendored frameworks and SDKs, written as
  `App.ipa!/Payload/App.app/Frameworks/Vendor.framework/Font.ttf`
- name table IDs 0, 1, 2, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 16, 17
- OS/2 `fsType` decoded into an embedding permission, plus `achVendID` and the font revision
- a license status with the evidence that produced it
- the code references that name it, by family, full name, PostScript name or file name

Plus two gap lists: fonts bundled but unreferenced, and names referenced but not bundled.

### License statuses

| Status       | Meaning |
| ------------ | ------- |
| `open`       | License text or URL in the font, or an adjacent license file, matched an open license (OFL-1.1, Apache-2.0, UFL-1.0, MIT, Bitstream Vera, CC0, GPL/LGPL with a copyleft note). SPDX id included. |
| `commercial` | The font's license text or URL contains explicit EULA wording or points at a known commercial vendor's license page. |
| `restricted` | `fsType` says restricted license embedding. Overrides the other statuses; license evidence is still reported. |
| `unknown`    | Everything else. This is the default. fontbom never guesses `open`. |

Adjacent license files are searched in the font's directory and up to three parent directories,
stopping at the enclosing archive or bundle. Generic files (`LICENSE`, `COPYING`) count only when
they sit in the font's own directory, because a repository license describes the code, not the
fonts. Font-specific files (`OFL.txt`, `UFL.txt`, or any file that mentions fonts) count up to
the distance limit.

### Code references

| Ecosystem    | What is scanned |
| ------------ | --------------- |
| iOS          | `UIFont(name:)`, `fontWithName:`, SwiftUI `Font.custom`, `UIAppFonts` in Info.plist (XML or binary), `Bundle.url(forResource:withExtension:)` for Core Text registration, font file literals, storyboard and xib `fontDescription` |
| Android      | `@font/x`, `R.font.x`, `android:fontFamily`, `app:fontFamily`, `Typeface.createFromAsset`, font file literals |
| Flutter      | `pubspec.yaml` `fonts:` families and assets, Dart `fontFamily:` |
| React Native | `require('…ttf')`, `import … from '…ttf'`, `fontFamily:` in styles |
| Web          | `@font-face` families and `src` URLs, Google Fonts stylesheet URLs (parsed, never fetched) |
| Binaries     | Family, full and PostScript names of discovered fonts searched as ASCII and UTF-16 strings in Mach-O executables, `classes.dex`, `resources.arsc`, `resources.pb`, `.so`, `.dylib` and compiled nibs. Reported at low confidence. |

Compiled Swift, Kotlin and Android binary XML are not decompiled. A font that is loaded by a
name built at runtime can appear as unreferenced.

## Output formats

- `terminal`: for humans at a terminal. Summary, aligned font table, unreferenced fonts,
  and the top referenced-but-unbundled names grouped by name with counts.
- `json`: stable, sorted, with a `schema_version` field. Suitable for diffing and for feeding
  other tools.
- `csv`: one row per font, disclaimer as a leading `#` comment.
- `markdown`: summary, font table, gap lists. Suitable for pull-request comments.

## Roadmap

Not in this release: SARIF output, CycloneDX and SPDX output, a license-evidence file linking
fonts to purchase records, a curated font-license knowledge base, glyph fingerprinting for
renamed fonts.

## Development

```
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy && .venv/bin/pytest
```

Tests build fonts at runtime with fontTools' FontBuilder and build app bundles with `zipfile`.
The only committed fonts are two small open-licensed fonts from Google Fonts, with their
license files, under `tests/fixtures/fonts/`. Never commit proprietary fonts or real app
binaries.

## License

Apache-2.0. Fixture fonts keep their own licenses: Press Start 2P (OFL-1.1) and Chewy
(Apache-2.0).
