# fontbom

Open-source CLI that scans mobile app binaries and codebases for bundled fonts and reports their
license status. Python 3.11+, fontTools, click. Apache-2.0. Package and command are both `fontbom`.

The full design is in `docs/design.md`. This file holds the decisions and constraints that must
survive every change.

## Hard constraints

- **Fully offline.** No network calls anywhere in `src/`. Google Fonts URLs found in code are
  parsed for family names, never fetched. Any dependency that phones home is rejected.
- **Conservative classification.** Default license status is `unknown`. Never infer `open` from a
  vendor name, a file name or a font family name. `open` requires license text or URL evidence
  in name ID 13/14 or an adjacent license file within the distance limit. `commercial` requires
  explicit commercial EULA language. Every classification records the evidence that produced it.
- **Not legal advice.** Every report format carries the disclaimer line from
  `fontbom/report/disclaimer.py`. Do not remove or shorten it.
- **Fixtures.** Only open-licensed fonts (OFL fonts from Google Fonts, with their license file)
  and synthetic bundles built in tests. Never commit proprietary fonts or real app binaries.
  Most tests build fonts at runtime with `fontTools.fontBuilder` via `tests/conftest.py`.
- **Runtime dependencies** are `fonttools[woff]` and `click` only. Adding another is a design
  decision, not a convenience.

## Scope

MVP (in progress):

1. Inputs: directory, `.ipa`, `.app`, `.apk`, `.aab`, `.xcframework`, `.zip`, recursing into
   `.framework`, `.bundle`, `.aar`, `.jar` and nested archives, with depth, size and entry-count
   limits.
2. Discovery by extension (`.ttf .otf .ttc .otc .woff .woff2`) and by magic bytes for renamed or
   extensionless files. Dedupe by sha256 of file bytes. Every path where a font appears is kept.
3. Metadata: name IDs 0, 1, 2, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 16, 17; OS/2 `fsType` and
   `achVendID`;
   `head` font revision.
4. Classification: `open` (with SPDX id), `commercial`, `restricted`, `unknown`. `fsType`
   embedding permissions are decoded separately; restricted-license embedding surfaces as
   status `restricted`.
5. Code references: iOS, Android, Flutter, React Native, CSS and Google Fonts URLs in source;
   string presence of family and PostScript names in compiled binaries at lower confidence.
   Reports bundled-but-unreferenced and referenced-but-unbundled fonts.
6. Output: terminal (default on a TTY), JSON (default when piped), CSV, Markdown.
   `--fail-on unknown,commercial,restricted` exits non-zero.

Later, not now: SARIF, CycloneDX/SPDX output, license-evidence file linking fonts to purchase
records, curated font-license knowledge base, glyph fingerprinting for renamed fonts.

## Conventions

- `src/` layout, one responsibility per module. Package map is in `docs/design.md`.
- Test-first. Every module has a `tests/test_<module>.py`. Golden files for reporters.
- Exit codes: 0 clean, 1 policy failure from `--fail-on`, 2 usage or input error.
- stdout carries only the report. Progress, summary and errors go to stderr, so piping stdout
  always yields a clean report.
- Performance: the expensive step is searching compiled binaries for font names. Measured
  facts that drove the design (2026-09-22): one `bytes.find` pass runs at about 1 GB/s on real
  Mach-O data; a Python regex alternation of many names is no faster than sequential passes
  once first letters differ; collapsing a binary to printable runs costs more than it saves.
  So the search minimises passes (only names that contain no other name are searched, longer
  names are verified at hit offsets) and parallelises across processes with `--jobs` when
  bytes x names exceeds `PARALLEL_THRESHOLD`. Do not reintroduce per-name full passes.
- Logical paths inside archives use `!/` as the separator:
  `App.ipa!/Payload/App.app/Frameworks/Vendor.framework/Font.ttf`.
- Font parse failures never crash a scan. They produce a record with status `unknown` and an
  `errors` entry.
- Adjacent generic license files (`LICENSE`, `COPYING`) count only from the font's own
  directory. `OFL*`, `UFL*` and files mentioning fonts count up to three levels, never across an
  archive or bundle boundary.
- `.claude/` and `skills-lock.json` are local agent tooling and stay gitignored.
- Run `ruff check .`, `ruff format --check .`, `mypy` and `pytest` before calling anything done.
- Commit, push or merge only when asked. No AI attribution in commits.

## Local setup

```
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```
