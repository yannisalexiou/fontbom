# Benchmarks

Before its first announcement, fontbom was run on nine production mobile codebases, five iOS and
four Android, and on two apps built from them. The first run, on 0.1.0, found bugs; 0.1.1 fixes
them, and this page reports 0.1.1. [Changes since 0.1.0](#changes-since-010) compares the two.

The codebases are private. They are named A to I, counts are rounded, and no font, file, module
or company names appear. Readers cannot reproduce these exact numbers; the
[last section](#measuring-your-own-code) shows how to take the same measurements on your own code.

## Summary

- Clean checkouts of up to 11,000 files scan in under 2 seconds. The largest working tree, 1.6
  million files including SwiftPM build caches, scans in 3 minutes 34 seconds with 0.9 GB of
  memory; 0.1.0 needed 9 minutes 39 seconds and 1.6 GB.
- No font file was missed in 21 checked scans covering 451 font paths, and nothing that is not a
  font was reported. In two Android codebases the only fonts were inside a vendored `.aar`, which a
  search by file extension does not open.
- fontbom found 5,087 of the 5,090 source lines that name a bundled font. In the clean checkouts
  every font marked as referenced was confirmed, 58 of 58. Six font files in a codebase more than
  ten years old are referenced nowhere, and fontbom reported all six as unreferenced.
- fontbom found real problems: storyboards set in a font family that the app never ships, a font
  requested from Swift that is not bundled, a storyboard weight missing from an otherwise bundled
  family, and web-view HTML that points at font files which are not bundled.

## The codebases

| Codebase | Platform | Age | Languages | UI | Source files |
| -------- | -------- | --- | --------- | -- | -----------: |
| A | iOS | 10+ years | Objective-C, Swift | Storyboards and XIBs (about 600 files), UIKit in code, SwiftUI in about 300 files | 5,200 |
| B | iOS | 5 to 10 years | Swift, a little Objective-C | UIKit with XIBs (about 60 files) | 160 |
| C | iOS | 2 to 3 years | Swift | SwiftUI in 45% of files, no Interface Builder | 1,000 |
| D | iOS | 2 to 3 years | Swift | SwiftUI (about 2,100 files) and UIKit, in 20+ local Swift packages | 7,600 |
| E | iOS | under 1 year | Swift | SwiftUI and UIKit, in local Swift packages | 700 |
| F | Android | 10+ years | Java, Kotlin | XML layouts (about 1,200), some Compose | 5,300 |
| G | Android | 5 to 10 years | Java, Kotlin | XML layouts (about 100) | 300 |
| H | Android | 2 to 3 years | Kotlin | Compose only | 6,800 |
| I | Android | under 1 year | Kotlin | Compose only | 950 |

Source files are Swift and Objective-C, or Kotlin and Java, files outside build folders and
dependencies.

## Setup

- Apple M5 (4 performance and 6 efficiency cores), 24 GB RAM, internal SSD, macOS 26.6.
- Python 3.12.14, fontbom 0.1.1 (code at commit `d3112f4`), fontTools 4.65.0.
- Command: `fontbom scan <target> --format json --output report.json --no-progress`, timed with
  `/usr/bin/time -l`, default `--jobs` (10).
- Each target ran four times. The first run warmed the file cache; the tables show the median of
  the other three. The two largest working trees ran once.
- 0.1.0 was measured the same way on 2026-09-24, and 0.1.1 on 2026-09-27, with the same clean
  checkout commits and the same built apps.

Three kinds of target:

| Target | What it is | What it stands for |
| ------ | ---------- | ------------------ |
| Clean checkout | The tracked files at `HEAD`, exported with `git archive` | A CI job before the build |
| Working tree | The repository folder as it was on a developer machine, with build caches and outputs | `fontbom scan .` on a laptop |
| Built app | An iOS `.app` from codebase E, the same app packed as an `.ipa`, and an Android debug `.apk` from codebase I | What ships |

## Speed

Files counts every file fontbom read, including members of the archives it opened. Peak memory
is the maximum resident set size of the main process.

### Clean checkouts

| Codebase | Files | Size | Time | Peak memory | Fonts (paths) |
| -------- | ----: | ---: | ---: | ----------: | ------------- |
| A | 11,400 | 330 MB | 1.9 s | 128 MB | 8 (12) |
| B | 750 | 14 MB | 0.12 s | 35 MB | 20 |
| C | 1,300 | 24 MB | 0.15 s | 32 MB | none |
| D | 9,500 | 490 MB | 0.77 s | 44 MB | none |
| E | 1,100 | 8 MB | 0.13 s | 31 MB | none |
| F | 11,000 | 170 MB | 1.6 s | 66 MB | 16 (24) |
| G | 1,100 | 13 MB | 0.15 s | 35 MB | 20 |
| H | 10,300 | 77 MB | 1.6 s | 55 MB | 4, inside a vendored `.aar` |
| I | 3,700 | 32 MB | 0.77 s | 45 MB | 4, inside a vendored `.aar` |

Codebases C, D and E contain no font files. D and E get their fonts from Swift packages, which
appear in their working trees' SwiftPM caches and in the built app below. C's source names no
custom font.

### Working trees

The working trees of B, C, F and G hold no build output and scan in the same time as their clean
checkouts.

| Codebase | Files | Size | Time | Peak memory | Fonts (paths) | Binaries searched |
| -------- | ----: | ---: | ---: | ----------: | ------------- | ----------------: |
| A | 18,600 | 1.2 GB | 2.8 s | 179 MB | 8 (12) | 815 MB |
| D | 626,000 | 27 GB | 3 min 34 s | 0.9 GB | 24 (155) | 14.5 GB |
| E | 220,000 | 13 GB | 1 min 8 s | 0.33 GB | 10 (110) | 7.1 GB |
| H | 18,300 | 125 MB | 2.5 s | 64 MB | 4 | 26 MB |
| I | 33,300 | 450 MB | 5.3 s | 119 MB | 4 (8) | 233 MB |

D's working tree holds 1.62 million files and E's 838,000. fontbom 0.1.1 skips the SwiftPM index
builds and repository mirrors, which hold 983,000 and 617,000 of them and never contain anything
that ships. Every font in those two trees sits in `.build/checkouts`, where SwiftPM keeps
dependency sources, in several copies; deduplication by content reduced 155 paths to 24 fonts in
D, and 110 paths to 10 fonts in E.

### Built apps

| App | Files | Size | Time | Peak memory | Fonts |
| --- | ----: | ---: | ---: | ----------: | ----: |
| iOS `.app` from codebase E | 260 | 154 MB | 0.21 s | 62 MB | 5 |
| The same app as `.ipa` (117 MB packed) | 260 | 154 MB | 0.45 s | 67 MB | 5 |
| Android debug `.apk` from codebase I (42 MB packed) | 2,750 | 86 MB | 0.86 s | 60 MB | 4 |

### Where the time goes

A separate instrumented run timed each phase of the two largest scans:

| Phase | D working tree | E working tree |
| ----- | -------------: | -------------: |
| Walk the tree and read file headers | 78 s | 28 s |
| Scan text files for references | 95 s (415,000 files) | 20 s (96,000 files) |
| Search binaries for font names | 46 s (3,700 files, 14.5 GB) | 16 s (890 files, 7.1 GB) |
| Detect, parse and classify fonts | 2 s | 1 s |
| Total | 224 s | 66 s |

Most text files cannot name a font. A byte check skips them before the patterns run, so in D the
patterns took 23 of the 95 seconds; reading the files and matching names kept in constants took
the rest.

Only the binary search runs in parallel. With `--jobs 1` the E working tree took 95 seconds
instead of 68, with identical results. The difference is all in the binary search: 16 seconds with
10 workers, roughly 44 with one.

## Accuracy

The check is independent of fontbom's code.

- Font files: every file with a font extension, plus every file that starts with font magic
  bytes, kept only if fontTools can open it as a font. Archives are opened as fontbom opens them,
  and the same folders are skipped.
- References: every place a discovered font's family, full, PostScript or file name appears as a
  quoted string, an XML attribute or text value, or an `@font/` or `R.font.` resource, in source
  and resource files of the clean checkouts. The check ignores which API receives the name, so it
  also finds names kept in constants.

### Font files

| | Result |
| - | ------ |
| Scans checked | 21: nine clean checkouts, nine working trees, three built apps |
| Font paths found by the check | 451 |
| Missed by fontbom | 0 |
| Fonts that failed to parse | 0 |
| Files reported as fonts that are not fonts | 0 |

### Referenced or unreferenced

The 72 fonts in the clean checkouts:

| fontbom's verdict | Fonts | What the check found |
| ----------------- | ----: | -------------------- |
| Referenced | 58 | All 58 confirmed |
| Unreferenced | 6 | Confirmed: nothing refers to them |
| Unreferenced | 8 | Used only through a precompiled design-system library. The app's source never names them, so no text search can see the use |

### Reference styles

Each line of source that names a bundled font, counted once, across the nine clean checkouts:

| Reference style | Lines | Found by 0.1.1 | Found by 0.1.0 |
| --------------- | ----: | -------------: | -------------: |
| Interface Builder `fontDescription` | 3,045 | 3,045 | 3,045 |
| Android `@font/` and `R.font.` | 957 | 957 | 957 |
| `UIFont(name:)`, `fontWithName:` or SwiftUI `.custom` with a string literal | 680 | 680 | 680 |
| `UIAppFonts` in Info.plist | 14 | 14 | 14 |
| Interface Builder user-defined runtime attribute `fontName` | 144 | 144 | 0 |
| Android XML attribute holding a font file path | 134 | 134 | 6 |
| Swift and Objective-C string constants | 50 | 49 | 31 |
| Java and Kotlin string constants | 24 | 24 | 21 |
| Android style item holding a font file path as text | 19 | 19 | 0 |
| Other files: bundled JavaScript, inline CSS | 23 | 21 | 8 |
| Total | 5,090 | 5,087 (99.9%) | 4,762 (94%) |

Interface Builder also writes a `customFonts` list at the end of each storyboard and XIB (1,298
lines). It repeats the fonts that the file's `fontDescription` elements already name, so it is
left out of the table. The three lines 0.1.1 misses name a font inside inline CSS, such as a
`style` attribute in HTML.

### Referenced but not bundled

Four clean checkouts produced 19 names that code references and the checkout does not contain:

| What it was | Names |
| ----------- | ----: |
| A font family used in storyboards (16 references) that the app never ships | 2 |
| A font requested from Swift that is not bundled | 1 |
| A storyboard weight missing from an otherwise bundled family | 1 |
| Web-view HTML and CSS that point at font files which are not bundled | 14 |
| A font supplied by a Swift package that the checkout does not contain; the built app has it | 1 |

None of them is a false positive. In the working trees of D and E the list has 0 and 8 entries.
I's working tree lists 61 entries for 11 names: the same web-view assets, found in the project
and again in the copies the Android build keeps in its intermediates and in the `.apk`.

## License status

Across every scan there were 70 distinct fonts, counted once each by content:

| Status | Fonts | Evidence |
| ------ | ----: | -------- |
| `open` | 34 | An Apache-2.0 (26) or OFL-1.1 (8) license URL in the font's name table (ID 14) |
| `commercial` | 7 | EULA wording in the font's license description |
| `unknown` | 29 | No license text or URL in the font, and no license file within the search distance |
| `restricted` | 0 | |

`unknown` is the default. fontbom never infers `open` from a font's name or vendor.

> fontbom reports metadata found inside font files and adjacent license files. It is not legal
> advice. Verify license terms with the font vendor or your legal team.

## Changes since 0.1.0

The 0.1.0 run exposed the problems below. All of them are fixed in 0.1.1.

| | 0.1.0 | 0.1.1 |
| - | ----: | ----: |
| Clean checkout of A (storyboard-heavy) | 4.3 s | 1.9 s |
| Working tree of D | 9 min 39 s, 1.6 GB | 3 min 34 s, 0.9 GB |
| Working tree of E | 5 min 10 s, 1.2 GB | 1 min 8 s, 0.33 GB |
| Reference lines found | 4,762 of 5,090 (94%) | 5,087 of 5,090 (99.9%) |
| Fonts wrongly reported unreferenced | 1 | 0 |
| Files reported as fonts that are not fonts | 14 paths | 0 |
| False not-bundled names in clean checkouts | 5 | 0 |
| Not-bundled entries in the working trees of D and E | 667 | 8 |

D's working tree grew between the runs, from 1.47 to 1.62 million files, so its two numbers
compare the same repository, not identical inputs. The clean checkouts and built apps were
identical. F's clean checkout went from 1.5 to 1.6 seconds, the cost of matching font names kept in
constants.

What changed:

- Files found only by their magic bytes count as fonts only if they parse. 0.1.0 reported an
  Android gesture library, Kotlin incremental-compile caches and a Core ML model's weights as
  fonts.
- Quoted font file names may contain spaces.
- New reference forms: font names kept in constants, Interface Builder runtime attributes such
  as `fontName`, and font file paths as Android XML text, the style form of the Calligraphy
  library.
- iOS built-in fonts are no longer reported as missing, including weight-specific names and
  Apple's dot-prefixed system names. A comma-separated `font-family` list is split.
- Directory scans skip SwiftPM index builds and repository mirrors, and `--exclude PATTERN` skips
  more.
- A byte check skips text files that cannot name a font, each file is read once, and linking
  references to fonts is linear instead of quadratic. Linking codebase A's references took 2.2
  seconds in 0.1.0 and takes 5 milliseconds in 0.1.1.
- Reports neutralise font metadata, which comes from the scanned files: CSV cells that would
  start a formula, HTML and links in Markdown, and escape sequences on a terminal.

## Limitations

1. **Fonts used only through a precompiled library** show as unreferenced in source scans, 8 of
   the 72 fonts here. In Android binaries resources are referenced by numeric ID, so an `.apk`
   scan cannot confirm use either.
2. **Inline CSS.** A font family in a `style` attribute or a CSS rule outside `@font-face` is not
   read (3 lines here).
3. **Names built at runtime**, such as a family name joined with a weight, cannot be matched.
4. **Quoted file names with spaces** link to bundled fonts, but are not reported as missing when
   nothing matches, because such strings are often messages.

## Measuring your own code

```
# A clean checkout, as a CI job sees it
mkdir -p /tmp/fontbom-clean && git archive HEAD | tar -x -C /tmp/fontbom-clean
/usr/bin/time -l fontbom scan /tmp/fontbom-clean --format json --output clean.json --no-progress

# The working tree as it is, skipping test targets, which never ship
/usr/bin/time -l fontbom scan . --exclude '*Tests' --format json --output worktree.json --no-progress
```

`/usr/bin/time -l` is the macOS form; on Linux use `/usr/bin/time -v`. The summary line on stderr
gives the font counts, and the JSON report lists every path and reference behind them.
