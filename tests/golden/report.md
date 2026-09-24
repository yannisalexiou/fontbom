# fontbom report

- Input: `App.ipa`
- Scanned: 2026-09-22T12:00:00Z
- Tool: fontbom 0.1.0

## Summary

| Status | Fonts |
| --- | ---: |
| open | 1 |
| commercial | 0 |
| restricted | 1 |
| unknown | 0 |
| **total** | **2** |

Referenced: 1. Unreferenced: 1. Referenced but not bundled: 1.

## Fonts

| Family | PostScript name | Status | SPDX | Embedding | Referenced | Evidence | Paths |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Libre Test | `LibreTest-Regular` | open | OFL-1.1 | installable | yes (1) | name_id_14 | `App.ipa!/Payload/App.app/Libre-Regular.ttf` |
| Secret Sans | `SecretSans-Bold` | **restricted** | — | restricted | no | fs_type | `App.ipa!/Payload/App.app/Frameworks/Vendor.framework/Secret.otf`<br>`App.ipa!/Payload/App.app/Secret.otf` |

## Bundled but unreferenced

These fonts ship in the bundle but no scanned code names them. Binary string matches count as references at low confidence, so a font listed here may still be loaded dynamically.

- Secret Sans (`SecretSans-Bold`), sha256 `bbbbbbbbbbbb…`

## Referenced but not bundled

| Name | Ecosystem | Kind | Source |
| --- | --- | --- | --- |
| Open Sans | web | google-fonts-url | `www/index.html:1` |

---

fontbom reports metadata found inside font files and adjacent license files. It is not legal advice. Verify license terms with the font vendor or your legal team.
