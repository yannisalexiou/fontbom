from __future__ import annotations

from pathlib import Path

from fontbom.references.react_native import ReactNativeScanner
from tests.conftest import entry

TSX = """
import bold from '../assets/fonts/Inter-Bold.ttf';
const regular = require("./assets/fonts/Inter-Regular.otf");
const styles = StyleSheet.create({ title: { fontFamily: 'Inter-Bold', fontSize: 20 } });
const other = { fontFamily: "Lato" };
"""


def names(refs: list) -> list[str]:  # type: ignore[type-arg]
    return sorted(r.name for r in refs)


def test_javascript_patterns(tmp_path: Path) -> None:
    refs = list(ReactNativeScanner().scan(entry(tmp_path, "src/App.tsx", TSX)))
    assert names(refs) == [
        "../assets/fonts/Inter-Bold.ttf",
        "./assets/fonts/Inter-Regular.otf",
        "Inter-Bold",
        "Lato",
    ]
    assert next(r for r in refs if r.name == "Lato").kind == "fontfamily-style"
    assert next(r for r in refs if r.name.endswith("Regular.otf")).kind == "font-file-import"
    assert refs[0].ecosystem == "react-native"


def test_accepts_js_family(tmp_path: Path) -> None:
    scanner = ReactNativeScanner()
    for name in ["a.js", "a.jsx", "a.ts", "a.tsx", "a.mjs"]:
        assert scanner.accepts(entry(tmp_path, name, "")), name
    assert not scanner.accepts(entry(tmp_path, "a.json", ""))
