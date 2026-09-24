"""Integration checks against real open-licensed fonts from google/fonts."""

from __future__ import annotations

import hashlib
from pathlib import Path

from fontbom.fonts.detect import FontFormat, detect
from fontbom.fonts.metadata import read_faces
from fontbom.licenses.adjacent import AdjacentFile
from fontbom.licenses.classify import classify
from fontbom.models import Embedding, FontRecord, Status
from tests.conftest import FIXTURES

PRESS_START = FIXTURES / "fonts" / "pressstart2p"
CHEWY = FIXTURES / "fonts" / "chewy"


def load(path: Path, *, strip_license_names: bool = False) -> FontRecord:
    data = path.read_bytes()
    fmt = detect(path.name, data[:4])
    assert fmt is not None
    faces = read_faces(data, fmt)
    if strip_license_names:
        for face in faces:
            face.names.pop(13, None)
            face.names.pop(14, None)
    return FontRecord(hashlib.sha256(data).hexdigest(), len(data), fmt, [path.name], faces)


def test_press_start_2p_metadata() -> None:
    record = load(PRESS_START / "PressStart2P-Regular.ttf")
    face = record.primary
    assert record.format == FontFormat.TRUETYPE
    assert face.family == "Press Start 2P"
    assert face.postscript_name == "PressStart2P-Regular"
    assert face.embedding == Embedding.INSTALLABLE
    assert face.errors == []


def test_press_start_2p_is_open_from_its_own_metadata() -> None:
    result = classify(load(PRESS_START / "PressStart2P-Regular.ttf"), [])
    assert result.status == Status.OPEN
    assert result.spdx == "OFL-1.1"


def test_chewy_is_open_from_its_own_metadata() -> None:
    record = load(CHEWY / "Chewy-Regular.ttf")
    assert record.primary.family == "Chewy"
    result = classify(record, [])
    assert result.status == Status.OPEN
    assert result.spdx == "Apache-2.0"


def test_full_ofl_text_next_to_a_font_classifies_open_without_false_commercial_match() -> None:
    record = load(PRESS_START / "PressStart2P-Regular.ttf", strip_license_names=True)
    assert classify(record, []).status == Status.UNKNOWN
    adjacent = [AdjacentFile("OFL.txt", 0, (PRESS_START / "OFL.txt").read_text())]
    result = classify(record, adjacent)
    assert result.status == Status.OPEN
    assert result.spdx == "OFL-1.1"
    assert result.evidence[0].source == "adjacent:OFL.txt"


def test_full_apache_text_next_to_a_font_classifies_open_without_false_commercial_match() -> None:
    record = load(CHEWY / "Chewy-Regular.ttf", strip_license_names=True)
    adjacent = [AdjacentFile("LICENSE.txt", 0, (CHEWY / "LICENSE.txt").read_text())]
    result = classify(record, adjacent)
    assert result.status == Status.OPEN
    assert result.spdx == "Apache-2.0"
