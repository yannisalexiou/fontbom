# Contributing to fontbom

Bug reports, wrong-status reports, new code-reference patterns and new license rules are the most
useful contributions. The design, pipeline and package map are in [docs/design.md](docs/design.md).

## Ground rules

People use fontbom to make compliance decisions, so these rules hold for every change:

- **Offline.** No network calls anywhere in `src/`. Google Fonts URLs found in code are parsed
  for family names, never fetched.
- **Conservative classification.** The default status is `unknown`. `open` needs license text or
  a license URL in name ID 13 or 14, or an adjacent license file. It is never inferred from a
  family, file or vendor name. `commercial` needs explicit EULA wording or a known commercial
  vendor's license URL. Every status records the evidence that produced it.
- **Disclaimer.** Every report format carries the text in `src/fontbom/report/disclaimer.py`.
  Don't remove or shorten it.
- **Clean stdout.** stdout carries only the report. Progress, the summary line and errors go to
  stderr.
- **Bad fonts don't crash a scan.** A font that fails to parse becomes a record with status
  `unknown` and an `errors` entry.
- **Two runtime dependencies.** `fonttools[woff]` and `click`. Adding another is a design
  decision, so open an issue before writing code that needs one.

Exit codes: 0 clean, 1 a `--fail-on` status matched, 2 usage or input error.

## Setup

Python 3.11 or newer.

```
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

On Windows, use `.venv\Scripts\` wherever these instructions say `.venv/bin/`.

## Checks

CI runs these four commands, and a pull request needs all of them to pass:

```
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
.venv/bin/pytest
```

mypy runs in strict mode on `src/`. pytest turns warnings into errors.

## Tests and fixtures

Write the test first. Tests for a module go in `tests/test_<module>.py`.

**Never commit proprietary or commercial fonts, app binaries (`.ipa`, `.apk`, `.aab`, `.app`) or
code you don't have the right to share, not even in a test.** Build what a test needs at runtime
with the helpers in `tests/conftest.py`:

| Helper | Builds |
| --- | --- |
| `make_font(...)` | A valid TTF, OTF, WOFF or WOFF2 with any name IDs, `fsType` and vendor ID |
| `make_collection(fonts)` | A `.ttc` from several fonts |
| `write_zip(path, members)` | A zip-family archive such as `.ipa`, `.apk`, `.aab`, `.aar` or `.jar` |
| `write_tree(root, files)` | A directory tree such as an `.app`, an `.xcframework` or a source repository |

To reproduce a problem from a real app, copy only the name-table strings and directory layout
that trigger it into a synthetic test. When a test needs license wording, quote only the words
the rule has to match.

The only committed fonts are in `tests/fixtures/fonts/`. Each is open-licensed and sits next to
its license file. Adding one needs a reason a synthetic font can't cover.

Reporters have golden files in `tests/golden/`. If you change a report format on purpose,
regenerate them from `render(fixed_result(), <format>)` in `tests/test_reports.py`, review the
diff, and explain the change in the pull request.

## Common changes

### A license rule

Rules live in `src/fontbom/licenses/rules.py`: `OPEN_RULES`, `COMMERCIAL_TEXT_RULE` and
`COMMERCIAL_VENDOR_DOMAINS`. Patterns are case-insensitive regular expressions.

- Link the public license text or page the rule is based on.
- Match license wording or license URLs, never family or vendor names.
- Add tests to `tests/test_classify.py`, including text that looks close but must not match.

### A code-reference pattern or ecosystem

Source scanners live in `src/fontbom/references/`, one module per ecosystem. Each subclasses
`RegexScanner` from `references/base.py` and sets `ecosystem`, `extensions` and `patterns`.
A `Pattern` has a `kind`, a regex whose first group captures the font name, and an optional
`build` function for names that need assembling.

A new ecosystem also needs an entry in `source_scanners()` in `src/fontbom/scanner.py` and a
`tests/test_references_<ecosystem>.py`.

Binary string matching in `references/binary.py` is the expensive step. Only names that contain
no other name are searched across a whole file; longer names are checked at the hit offsets.
Don't add a full pass per name, and include before-and-after timings with any change there.

### Paths

Logical paths inside archives use `!/` between the archive and its member:
`App.ipa!/Payload/App.app/Frameworks/Vendor.framework/Font.ttf`.

## Pull requests

- One change per pull request, with its tests.
- Add a line to [CHANGELOG.md](CHANGELOG.md) for anything a user would notice, under an
  `## Unreleased` heading at the top. Add that heading if the newest section is a release.
- Open an issue first for anything bigger than a fix, such as a new input format, report format
  or dependency, so the design is agreed before you write the code.

## Issues and security

Use the issue templates. Issues are public, so never attach font files or app binaries. Paste
the JSON report instead: it holds the font's metadata, not the font. Report security problems
privately, as described in [SECURITY.md](SECURITY.md).

## License

fontbom is licensed under Apache-2.0. Contributions are accepted under the same license, as
section 5 of [LICENSE](LICENSE) describes.
