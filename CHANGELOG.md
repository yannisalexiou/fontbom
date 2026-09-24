# Changelog

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
