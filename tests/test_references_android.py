from __future__ import annotations

from pathlib import Path

from fontbom.references.android import AndroidScanner
from tests.conftest import entry

LAYOUT = """<?xml version="1.0"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto">
  <TextView android:fontFamily="@font/roboto_bold" />
  <TextView app:fontFamily="@font/lato" />
  <TextView android:fontFamily="sans-serif-medium" />
</LinearLayout>"""

FONT_FAMILY_XML = """<font-family xmlns:android="http://schemas.android.com/apk/res/android">
  <font android:fontStyle="normal" android:fontWeight="400" android:font="@font/inter_regular"/>
</font-family>"""

KOTLIN = """
val tf = Typeface.createFromAsset(context.assets, "fonts/Oswald-Light.ttf")
val compat = ResourcesCompat.getFont(context, R.font.merriweather)
val compose = FontFamily(Font(R.font.inter_bold, FontWeight.Bold))
val path = "fonts/Lora-Italic.otf"
"""


def names(refs: list) -> list[str]:  # type: ignore[type-arg]
    return sorted(r.name for r in refs)


def test_layout_xml_font_family_attributes(tmp_path: Path) -> None:
    refs = list(AndroidScanner().scan(entry(tmp_path, "res/layout/main.xml", LAYOUT)))
    assert names(refs) == ["lato", "roboto_bold", "sans-serif-medium"]
    roboto = next(r for r in refs if r.name == "roboto_bold")
    assert roboto.kind == "font-resource"
    assert roboto.ecosystem == "android"
    assert roboto.line == 4
    assert next(r for r in refs if r.name.startswith("sans")).kind == "font-family-attr"


def test_font_family_xml_resource(tmp_path: Path) -> None:
    refs = list(AndroidScanner().scan(entry(tmp_path, "res/font/inter.xml", FONT_FAMILY_XML)))
    assert names(refs) == ["inter_regular"]


def test_kotlin_and_java_patterns(tmp_path: Path) -> None:
    refs = list(AndroidScanner().scan(entry(tmp_path, "src/Main.kt", KOTLIN)))
    assert names(refs) == [
        "fonts/Lora-Italic.otf",
        "fonts/Oswald-Light.ttf",
        "inter_bold",
        "merriweather",
    ]
    assert next(r for r in refs if r.name.endswith("Light.ttf")).kind == "typeface-asset"
    assert next(r for r in refs if r.name == "merriweather").kind == "font-resource"
    assert next(r for r in refs if r.name.endswith(".otf")).kind == "font-file-literal"


def test_accepts_android_source_and_xml(tmp_path: Path) -> None:
    scanner = AndroidScanner()
    for name in ["a.kt", "a.java", "res/layout/a.xml", "AndroidManifest.xml"]:
        assert scanner.accepts(entry(tmp_path, name, "")), name
    for name in ["a.swift", "a.ttf", "a.storyboard"]:
        assert not scanner.accepts(entry(tmp_path, name, "")), name


def test_font_file_names_with_spaces(tmp_path: Path) -> None:
    xml = '<TextView app:fontPath="fonts/Example Sans Bold.ttf" />\n'
    refs = list(AndroidScanner().scan(entry(tmp_path, "res/layout/a.xml", xml)))
    assert names(refs) == ["fonts/Example Sans Bold.ttf"]
    assert refs[0].kind == "font-file-literal"


def test_style_item_with_font_path_as_text(tmp_path: Path) -> None:
    # The Calligraphy library's style form.
    xml = """<resources>
  <style name="Heading">
    <item name="fontPath">fonts/Oswald-Light.ttf</item>
    <item name="fontPath">fonts/Example Sans Bold.ttf</item>
    <item name="android:textSize">14sp</item>
  </style>
</resources>"""
    refs = list(AndroidScanner().scan(entry(tmp_path, "res/values/styles.xml", xml)))
    assert names(refs) == ["fonts/Example Sans Bold.ttf", "fonts/Oswald-Light.ttf"]
    assert {r.kind for r in refs} == {"font-file-text"}
    assert next(r for r in refs if r.name.endswith("Light.ttf")).line == 3
