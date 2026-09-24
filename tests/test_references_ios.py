from __future__ import annotations

import plistlib
from pathlib import Path

from fontbom.references.ios import IOSScanner
from tests.conftest import entry

SWIFT = """
import UIKit
let title = UIFont(name: "Roboto-Bold", size: 17)
let body = UIFont.init(name: "Lato-Regular", size: 14)!
let swiftui = Font.custom("Inter-Medium", size: 12)
let fixed = Font.custom("Inter-Bold", fixedSize: 12)
let url = Bundle.main.url(forResource: "Merriweather-Italic", withExtension: "ttf")
CTFontManagerRegisterFontsForURL(url! as CFURL, .process, nil)
let path = "Fonts/Oswald-Light.otf"
"""

OBJC = """
UIFont *f = [UIFont fontWithName:@"Roboto-Bold" size:17];
NSFont *m = [NSFont fontWithName:@"Menlo-Regular" size:11];
"""


def names(refs: list) -> list[str]:  # type: ignore[type-arg]
    return sorted(r.name for r in refs)


def test_swift_patterns(tmp_path: Path) -> None:
    refs = list(IOSScanner().scan(entry(tmp_path, "App/Views.swift", SWIFT)))
    assert names(refs) == [
        "Fonts/Oswald-Light.otf",
        "Inter-Bold",
        "Inter-Medium",
        "Lato-Regular",
        "Merriweather-Italic.ttf",
        "Roboto-Bold",
    ]
    roboto = next(r for r in refs if r.name == "Roboto-Bold")
    assert roboto.kind == "uifont"
    assert roboto.ecosystem == "ios"
    assert roboto.source == "App/Views.swift"
    assert roboto.line == 3
    assert roboto.confidence == "high"
    assert next(r for r in refs if r.name == "Inter-Medium").kind == "swiftui-font-custom"
    assert next(r for r in refs if r.name.startswith("Merriweather")).kind == "bundle-resource"
    assert next(r for r in refs if r.name.endswith(".otf")).kind == "font-file-literal"


def test_objective_c_patterns(tmp_path: Path) -> None:
    refs = list(IOSScanner().scan(entry(tmp_path, "App/View.m", OBJC)))
    assert names(refs) == ["Menlo-Regular", "Roboto-Bold"]
    assert {r.kind for r in refs} == {"uifont"}


def test_info_plist_uiappfonts_xml(tmp_path: Path) -> None:
    plist = plistlib.dumps({"UIAppFonts": ["Roboto-Bold.ttf", "Lato-Regular.otf"]})
    refs = list(IOSScanner().scan(entry(tmp_path, "App/Info.plist", plist)))
    assert names(refs) == ["Lato-Regular.otf", "Roboto-Bold.ttf"]
    assert {r.kind for r in refs} == {"uiappfonts"}
    assert refs[0].line is None


def test_info_plist_uiappfonts_binary(tmp_path: Path) -> None:
    plist = plistlib.dumps({"UIAppFonts": ["Roboto-Bold.ttf"]}, fmt=plistlib.FMT_BINARY)
    refs = list(IOSScanner().scan(entry(tmp_path, "Payload/App.app/Info.plist", plist)))
    assert names(refs) == ["Roboto-Bold.ttf"]


def test_plist_without_uiappfonts_yields_nothing(tmp_path: Path) -> None:
    plist = plistlib.dumps({"CFBundleName": "App"})
    assert list(IOSScanner().scan(entry(tmp_path, "Info.plist", plist))) == []


def test_malformed_plist_yields_nothing(tmp_path: Path) -> None:
    assert list(IOSScanner().scan(entry(tmp_path, "Info.plist", b"<plist><dict>"))) == []


def test_storyboard_font_descriptions(tmp_path: Path) -> None:
    xml = """<?xml version="1.0"?><document>
<label text="Hi"><fontDescription key="fontDescription" name="Roboto-Bold" family="Roboto" pointSize="17"/></label>
<label text="Sys"><fontDescription key="fontDescription" type="system" pointSize="17"/></label>
</document>"""
    refs = list(IOSScanner().scan(entry(tmp_path, "Base.lproj/Main.storyboard", xml)))
    assert names(refs) == ["Roboto", "Roboto-Bold"]
    assert {r.kind for r in refs} == {"storyboard"}


def test_accepts_only_ios_source_files(tmp_path: Path) -> None:
    scanner = IOSScanner()
    for name in ["a.swift", "a.m", "a.mm", "a.h", "Info.plist", "a.storyboard", "a.xib"]:
        assert scanner.accepts(entry(tmp_path, name, "")), name
    for name in ["a.kt", "a.py", "a.ttf", "README.md"]:
        assert not scanner.accepts(entry(tmp_path, name, "")), name
