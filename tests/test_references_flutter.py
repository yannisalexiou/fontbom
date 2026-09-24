from __future__ import annotations

from pathlib import Path

from fontbom.references.flutter import FlutterScanner
from tests.conftest import entry

PUBSPEC = """
name: demo
flutter:
  uses-material-design: true
  assets:
    - assets/images/
    - assets/fonts/Extra-Regular.otf
  fonts:
    - family: Raleway
      fonts:
        - asset: fonts/Raleway-Regular.ttf
        - asset: "fonts/Raleway-Italic.ttf"
          style: italic
    - family: 'Roboto Mono'
      fonts:
        - asset: fonts/RobotoMono-Regular.ttf
"""

DART = """
const style = TextStyle(fontFamily: 'Raleway', fontSize: 14);
final other = TextStyle(fontFamily: "Roboto Mono");
"""


def names(refs: list) -> list[str]:  # type: ignore[type-arg]
    return sorted(r.name for r in refs)


def test_pubspec_fonts_section(tmp_path: Path) -> None:
    refs = list(FlutterScanner().scan(entry(tmp_path, "pubspec.yaml", PUBSPEC)))
    assert names(refs) == [
        "Raleway",
        "Roboto Mono",
        "assets/fonts/Extra-Regular.otf",
        "fonts/Raleway-Italic.ttf",
        "fonts/Raleway-Regular.ttf",
        "fonts/RobotoMono-Regular.ttf",
    ]
    family = next(r for r in refs if r.name == "Raleway")
    assert family.kind == "pubspec-family"
    assert family.ecosystem == "flutter"
    assert family.line == 9
    assert next(r for r in refs if r.name.endswith("Italic.ttf")).kind == "pubspec-asset"


def test_dart_font_family(tmp_path: Path) -> None:
    refs = list(FlutterScanner().scan(entry(tmp_path, "lib/main.dart", DART)))
    assert names(refs) == ["Raleway", "Roboto Mono"]
    assert {r.kind for r in refs} == {"dart-fontfamily"}


def test_accepts_only_pubspec_and_dart(tmp_path: Path) -> None:
    scanner = FlutterScanner()
    assert scanner.accepts(entry(tmp_path, "pubspec.yaml", ""))
    assert scanner.accepts(entry(tmp_path, "lib/a.dart", ""))
    assert not scanner.accepts(entry(tmp_path, "pubspec.lock", ""))
    assert not scanner.accepts(entry(tmp_path, "other.yaml", ""))
