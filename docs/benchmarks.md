# Benchmarks

Before its first announcement, fontbom 0.1.0 was run on nine production mobile codebases, five
iOS and four Android, and on two apps built from them. This page reports how long each scan took
and how its findings compared with an independent check.

The codebases are private. They are named A to I, counts are rounded, and no font, file, module
or company names appear. Readers cannot reproduce these exact numbers; the
[last section](#measuring-your-own-code) shows how to take the same measurements on your own code.

## Summary

- Clean checkouts of up to 11,000 files scan in under 5 seconds. The largest working tree, 1.5
  million files and 113 GB including SwiftPM build caches, scans in 9 minutes 39 seconds with
  1.6 GB of memory.
- No font file was missed in 21 checked scans covering 750 font paths. In two Android codebases
  the only fonts were inside a vendored `.aar`, which a search by file extension does not open.
  Three kinds of file that are not fonts, at 14 paths, were reported as fonts.
- In the clean checkouts, every font marked as referenced was confirmed, 57 of 57. Six font files
  in a codebase more than ten years old are referenced nowhere, and fontbom reported all six as
  unreferenced.
- fontbom found real problems: storyboards set in a font family that the app never ships, a font
  requested from Swift that is not bundled, a storyboard weight missing from an otherwise bundled
  family, and web-view HTML that points at font files which are not bundled.
- The test also exposed gaps. They are listed under [Limitations found](#limitations-found), and
  each one is tracked for a fix.

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
- Python 3.12.14, fontbom 0.1.0 (commit `4bc77e2`), fontTools 4.65.0.
- Command: `fontbom scan <target> --format json --output report.json --no-progress`, timed with
  `/usr/bin/time -l`, default `--jobs` (10).
- Each target ran four times. The first run warmed the file cache; the tables show the median of
  the other three. The two largest working trees ran once. They are larger than RAM, so those
  runs read from disk.

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
| A | 11,400 | 330 MB | 4.3 s | 122 MB | 8 (12) |
| B | 750 | 14 MB | 0.13 s | 35 MB | 20 |
| C | 1,300 | 24 MB | 0.19 s | 32 MB | none |
| D | 9,500 | 490 MB | 0.95 s | 44 MB | none |
| E | 1,100 | 8 MB | 0.15 s | 31 MB | none |
| F | 11,000 | 170 MB | 1.5 s | 66 MB | 16 (24), plus a non-font (1 path) |
| G | 1,100 | 13 MB | 0.17 s | 35 MB | 20 |
| H | 10,300 | 77 MB | 1.7 s | 55 MB | 4, inside a vendored `.aar` |
| I | 3,700 | 32 MB | 0.75 s | 45 MB | 4, inside a vendored `.aar` |

Codebases C, D and E contain no font files. D and E get their fonts from Swift packages, which
appear in their working trees' SwiftPM caches and in the built app below. C's source names no
custom font.

### Working trees

The working trees of B, C, F and G hold no build output and scan in the same time as their clean
checkouts.

| Codebase | Files | Size | Time | Peak memory | Fonts (paths) | Binaries searched |
| -------- | ----: | ---: | ---: | ----------: | ------------- | ----------------: |
| A | 18,600 | 1.2 GB | 5.4 s | 179 MB | 8 (12) | 815 MB |
| D | 1,470,000 | 113 GB | 9 min 39 s | 1.6 GB | 24 (315), plus a non-font (7 paths) | 30 GB |
| E | 827,000 | 79 GB | 5 min 10 s | 1.2 GB | 10 (249) | 19.7 GB |
| H | 18,300 | 125 MB | 2.4 s | 65 MB | 4, plus a non-font (2 paths) | 26 MB |
| I | 33,300 | 450 MB | 5.3 s | 117 MB | 4 (8), plus a non-font (4 paths) | 233 MB |

In D and E, SwiftPM caches (`.build/checkouts`, `.build/index-build`, `.build/repositories`,
`.build/artifacts`) held 95% of the bytes. Every font in those two trees sits in the caches, in 7
to 25 copies. Deduplication by content reduced 315 paths to 24 fonts in D, and 249 paths to 10
fonts in E.

### Built apps

| App | Files | Size | Time | Peak memory | Fonts |
| --- | ----: | ---: | ---: | ----------: | ----: |
| iOS `.app` from codebase E | 260 | 154 MB | 0.22 s | 62 MB | 5 |
| The same app as `.ipa` (117 MB packed) | 260 | 154 MB | 0.45 s | 67 MB | 5 |
| Android debug `.apk` from codebase I (42 MB packed) | 2,750 | 86 MB | 0.87 s | 64 MB | 4 |

### Where the time goes

A separate instrumented run timed each phase of the two largest scans:

| Phase | D working tree | E working tree |
| ----- | -------------: | -------------: |
| Walk the tree and read file headers | 182 s | 103 s |
| Scan text files for references | 290 s (903,000 files) | 149 s (468,000 files) |
| Search binaries for font names | 98 s (7,800 files, 30 GB) | 53 s (3,400 files, 19.7 GB) |
| Detect, parse and classify fonts | 6 s | 4 s |
| Total | 583 s | 312 s |

The text scan, not the binary search, was the slowest phase. In D, 99% of the files it read came
from the SwiftPM caches. Three quarters were C and Objective-C headers, most of them from index
builds and binary frameworks. The project's own Swift files were 7,600 of the 903,000.

Only the binary search runs in parallel. With `--jobs 1` the E working tree took 6 minutes 41
seconds instead of 5 minutes 10 seconds, with identical results. The 91-second difference is all
in the binary search: 53 seconds with 10 workers, roughly 144 seconds with one.

In codebase A, linking 15,000 references to 8 fonts took 2.2 seconds, about half of the scan,
because duplicates are removed with a list lookup. See [Limitations found](#limitations-found).

## Accuracy

The check is independent of fontbom's code.

- Font files: every file with a font extension, plus every file that starts with font magic
  bytes, kept only if fontTools can open it as a font. Archives are opened as fontbom opens them.
- References: every place a discovered font's family, full, PostScript or file name appears as a
  quoted string, an XML attribute or text value, or an `@font/` or `R.font.` resource, in source
  and resource files of the clean checkouts. The check ignores which API receives the name, so it
  also finds names kept in constants.

### Font files

| | Result |
| - | ------ |
| Scans checked | 21: nine clean checkouts, nine working trees, three built apps |
| Font paths found by the check | 750 |
| Missed by fontbom | 0 |
| Fonts that failed to parse | 0 |
| Files reported as fonts that are not fonts | 14 paths of three kinds: an Android gesture library in `res/raw`, Kotlin incremental-compile caches, and a Core ML model's weights |

### Referenced or unreferenced

The 72 fonts in the clean checkouts:

| fontbom's verdict | Fonts | What the check found |
| ----------------- | ----: | -------------------- |
| Referenced | 57 | All 57 confirmed |
| Unreferenced | 6 | Confirmed: nothing refers to them |
| Unreferenced | 8 | Used only through a precompiled design-system library. The app's source never names them, so no text search can see the use |
| Unreferenced | 1 | Wrong: an Android style item names it as text |

### Reference styles

Each line of source that names a bundled font, counted once, across the nine clean checkouts:

| Reference style | Lines | Found by fontbom |
| --------------- | ----: | ---------------: |
| Interface Builder `fontDescription` | 3,045 | 3,045 |
| Android `@font/` and `R.font.` | 957 | 957 |
| `UIFont(name:)`, `fontWithName:` or SwiftUI `.custom` with a string literal | 680 | 680 |
| `UIAppFonts` in Info.plist | 14 | 14 |
| Interface Builder user-defined runtime attribute `fontName` | 144 | 0 |
| Android XML attribute holding a font file path | 134 | 6 |
| Swift and Objective-C string constants | 50 | 31 |
| Java and Kotlin string constants | 24 | 21 |
| Android style item holding a font file path as text | 19 | 0 |
| Other files: bundled JavaScript, inline CSS in XML strings | 23 | 8 |
| Total | 5,090 | 4,762 (94%) |

Interface Builder also writes a `customFonts` list at the end of each storyboard and XIB (1,298
lines). It repeats the fonts that the file's `fontDescription` elements already name, so it is
left out of the table.

### Referenced but not bundled

Four clean checkouts produced 23 names that code references and the checkout does not contain:

| What it was | Names |
| ----------- | ----: |
| A font family used in storyboards (16 references) that the app never ships | 2 |
| A font requested from Swift that is not bundled | 1 |
| A storyboard weight missing from an otherwise bundled family | 1 |
| Web-view HTML and CSS that point at font files which are not bundled | 13 |
| A font supplied by a Swift package that the checkout does not contain; the built app has it | 1 |
| iOS built-in fonts reported as missing (false positives) | 4 |
| A CSS family list read as a single name (false positive) | 1 |

In the working trees of D and E, the not-bundled list grew to 444 and 223 entries. All but 8 came
from package sources and index builds inside the SwiftPM caches.

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

## Limitations found

Each item is tracked for a fix before promotion.

1. **Files that only look like fonts.** An Android gesture library, Kotlin incremental-compile
   caches and a Core ML model's weights, 14 paths in all, were reported as fonts. They start with
   the TrueType magic bytes, parse as an empty font, and are reported with no names and no error.
   A file found only by its magic bytes should count as a font only when it has the tables every
   font needs.
2. **Font file names with spaces.** A quoted path such as `"fonts/Example Sans Bold.ttf"` never
   matches, because the file-name pattern stops at whitespace. This caused 128 of the 134 missed
   Android attribute lines.
3. **Names kept in constants.** A font name assigned to a constant and passed to `UIFont(name:)`
   or `Typeface` later is linked only when the string is a font file name. 22 of 74 such lines
   were missed. Scans of built apps find these names inside the compiled binary, at low
   confidence.
4. **Interface Builder runtime attributes.** Storyboards that set `fontName` through a
   user-defined runtime attribute on a custom view are not read (144 lines).
5. **Android style items with text values.** `<item name="…">fonts/….ttf</item>`, the style form
   used by the Calligraphy library, is not read. One font was reported unreferenced because of it.
6. **iOS built-in fonts.** Weight-specific names of built-in families, other built-in families and
   Apple's dot-prefixed private system names are reported as missing from the bundle.
7. **CSS family lists.** A comma-separated list inside `@font-face` is read as one name.
8. **Build caches in working trees.** In D and E, SwiftPM caches supplied 99% of the text files
   scanned and all but 8 of the not-bundled entries. An `--exclude` option would let users skip
   them. Index builds (`.build/index-build`) and repository mirrors (`.build/repositories`) never
   hold anything that ships and could be skipped by default. `.build/checkouts` and
   `.build/artifacts` have to stay, because shipped dependency fonts and binaries live there.
9. **Text scan cost.** In the working trees the text scan, not the binary search, is the slowest
   phase. In D, three quarters of the files it read were headers. A cheap check for font-related
   text before running the patterns could skip most of them.
10. **Reference linking.** Removing duplicate references with a list lookup is quadratic in the
    number of references per font. A set makes it linear.
11. **Fonts used only through a precompiled library.** They show as unreferenced in source scans.
    In Android binaries resources are referenced by numeric ID, so an `.apk` scan cannot confirm
    use either. Reporting these as "use not determinable" would be more accurate than
    "unreferenced".

## Measuring your own code

```
# A clean checkout, as a CI job sees it
mkdir -p /tmp/fontbom-clean && git archive HEAD | tar -x -C /tmp/fontbom-clean
/usr/bin/time -l fontbom scan /tmp/fontbom-clean --format json --output clean.json --no-progress

# The working tree as it is
/usr/bin/time -l fontbom scan . --format json --output worktree.json --no-progress
```

`/usr/bin/time -l` is the macOS form; on Linux use `/usr/bin/time -v`. The summary line on stderr
gives the font counts, and the JSON report lists every path and reference behind them.
