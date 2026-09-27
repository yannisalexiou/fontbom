# Changelog

## 0.1.1 - 2026-09-27

### Security

- Reports neutralise font metadata, paths and reference names, which come from the scanned files.
  CSV cells that would start a formula get a leading `'`. Markdown escapes HTML, links, table pipes
  and code-span backticks. The terminal report and CSV show control characters as `\xNN` instead
  of passing escape sequences through.

### Added

- `--exclude PATTERN`, repeatable. A pattern without `/` matches a name at any depth, one with
  `/` matches the path under the scanned directory.
- Font names kept in constants: quoted strings that equal a discovered font's family, full,
  PostScript or file name count as references (`string-literal`).
- Storyboard and xib user-defined runtime attributes whose key path ends in `fontName` or
  `fontFamily` (`ib-runtime-attribute`).
- Android font file paths as XML text, the Calligraphy style form (`font-file-text`).

### Changed

- Directory scans skip the SwiftPM caches `.build/index-build` and `.build/repositories`.
- Files without a font extension count as fonts only if they parse with `head` and `name` tables.
- Source files are checked for a font-related marker before they are decoded and matched, which
  makes scans of large working trees faster.

### Fixed

- Kotlin compile caches, Android gesture files, Core ML weights and other files that start with
  font magic bytes were reported as fonts with no names and no error.
- Quoted font file names containing spaces were never matched. Such names now link to bundled
  fonts; when nothing matches they are not reported as missing, since they are often messages.
- iOS built-in fonts named by weight (`HelveticaNeue-Bold`), other built-in families such as
  Avenir Next, and dot-prefixed Apple system names were reported as referenced but not bundled.
- A comma-separated `font-family` list inside `@font-face` was read as one name.
- Linking references to fonts was quadratic in the number of references per font.

## 0.1.0 - 2026-09-24

### Added

- `fontbom scan` for directories, `.ipa`, `.app`, `.apk`, `.aab`, `.xcframework`, `.zip` and
  nested archives, with depth, size and entry-count limits and zip-slip protection.
- Font discovery by extension and magic bytes, deduplicated by sha256 with every path kept.
- Metadata extraction: name IDs 0, 1, 2, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 16, 17, OS/2 `fsType`
  and `achVendID`, font revision. Collections yield one face per member.
- Conservative license classification: `open` with SPDX id, `commercial`, `restricted`,
  `unknown`, with evidence and adjacent license file lookup.
- Code reference scanners for iOS, Android, Flutter, React Native, web, and low-confidence
  string matching in compiled binaries. Reports bundled-but-unreferenced and
  referenced-but-unbundled fonts.
- Terminal, JSON, CSV and Markdown reports, each carrying the "not legal advice" disclaimer.
  Terminal is the default on a TTY, JSON when piped.
- `--fail-on` with a non-zero exit code for CI.
- Live status line on stderr while scanning, with `--progress/--no-progress`.
- `--jobs` to search large binaries with a process pool; containment-based name search that
  avoids one full pass per name.
