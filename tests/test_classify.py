from __future__ import annotations

import hashlib
from typing import Any

import pytest

from fontbom.fonts.detect import FontFormat
from fontbom.fonts.metadata import read_faces
from fontbom.licenses.adjacent import AdjacentFile
from fontbom.licenses.classify import classify
from fontbom.models import Embedding, FontRecord, Status
from tests.conftest import make_font

OFL_TEXT = (
    "Copyright 2026 Test Foundry. This Font Software is licensed under the SIL Open Font "
    "License, Version 1.1. This license is copied below, and is also available with a FAQ at: "
    "https://openfontlicense.org"
)
APACHE_TEXT = 'Licensed under the Apache License, Version 2.0 (the "License")'
EULA_TEXT = (
    "This font software is licensed to you under the Test Foundry End User License "
    "Agreement for use on up to 5 workstations."
)


def record(path: str = "fonts/Test.ttf", **kwargs: Any) -> FontRecord:
    data = make_font(**kwargs)
    return FontRecord(
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
        format=FontFormat.TRUETYPE,
        paths=[path],
        faces=read_faces(data, FontFormat.TRUETYPE),
    )


def test_no_license_information_is_unknown_with_no_evidence() -> None:
    result = classify(record(copyright=None), [])
    assert result.status == Status.UNKNOWN
    assert result.spdx is None
    assert result.evidence == []


def test_all_rights_reserved_alone_is_unknown_not_commercial() -> None:
    result = classify(record(copyright="Copyright 2026 Foundry. All rights reserved."), [])
    assert result.status == Status.UNKNOWN


def test_family_name_never_implies_open() -> None:
    result = classify(record(family="Roboto", copyright=None), [])
    assert result.status == Status.UNKNOWN


@pytest.mark.parametrize(
    ("text", "spdx"),
    [
        (OFL_TEXT, "OFL-1.1"),
        ("Licensed under the OFL 1.1", "OFL-1.1"),
        (APACHE_TEXT, "Apache-2.0"),
        ("This Font Software is licensed under the Ubuntu Font Licence, Version 1.0.", "UFL-1.0"),
        ("Permission is hereby granted, free of charge, to any person obtaining a copy", "MIT"),
        ("Released under the MIT License.", "MIT"),
        ("Bitstream Vera Fonts Copyright", "Bitstream-Vera"),
        ("Released under CC0 1.0 Universal", "CC0-1.0"),
    ],
)
def test_open_license_text_in_name_id_13(text: str, spdx: str) -> None:
    result = classify(record(license_text=text), [])
    assert result.status == Status.OPEN
    assert result.spdx == spdx
    assert result.evidence[0].source == "name_id_13"


@pytest.mark.parametrize(
    ("url", "spdx"),
    [
        ("https://openfontlicense.org", "OFL-1.1"),
        ("http://scripts.sil.org/OFL", "OFL-1.1"),
        ("http://www.apache.org/licenses/LICENSE-2.0", "Apache-2.0"),
        ("https://ubuntu.com/legal/font-licence", "UFL-1.0"),
        ("https://opensource.org/licenses/MIT", "MIT"),
        ("https://creativecommons.org/publicdomain/zero/1.0/", "CC0-1.0"),
    ],
)
def test_open_license_url_in_name_id_14(url: str, spdx: str) -> None:
    result = classify(record(license_url=url), [])
    assert result.status == Status.OPEN
    assert result.spdx == spdx
    assert result.evidence[0].source == "name_id_14"


def test_gpl_is_open_with_copyleft_note() -> None:
    result = classify(record(license_text="GNU General Public License version 2"), [])
    assert result.status == Status.OPEN
    assert result.spdx == "GPL-2.0-or-later"
    assert "copyleft" in result.notes


def test_gpl_with_font_exception_gets_spdx_exception() -> None:
    text = "GNU General Public License version 3 with the GPL font exception"
    result = classify(record(license_text=text), [])
    assert result.spdx == "GPL-3.0-or-later WITH Font-exception-2.0"


def test_commercial_eula_text_in_name_id_13() -> None:
    result = classify(record(license_text=EULA_TEXT), [])
    assert result.status == Status.COMMERCIAL
    assert result.spdx is None
    assert result.evidence[0].source == "name_id_13"


@pytest.mark.parametrize(
    "url", ["https://www.myfonts.com/viewlicense", "https://www.fonts.com/eula", "https://typography.com/license"]
)  # fmt: skip
def test_commercial_vendor_license_url_in_name_id_14(url: str) -> None:
    result = classify(record(license_url=url), [])
    assert result.status == Status.COMMERCIAL
    assert result.evidence[0].source == "name_id_14"


def test_commercial_wording_beats_open_wording_in_the_same_field() -> None:
    text = OFL_TEXT + " This font is licensed to ACME Corp under an End User License Agreement."
    result = classify(record(license_text=text), [])
    assert result.status == Status.COMMERCIAL


def test_font_metadata_beats_adjacent_files() -> None:
    adjacent = [AdjacentFile("fonts/OFL.txt", 0, OFL_TEXT)]
    result = classify(record(license_text=EULA_TEXT), adjacent)
    assert result.status == Status.COMMERCIAL


def test_adjacent_ofl_file_in_same_directory_classifies_open() -> None:
    result = classify(record(copyright=None), [AdjacentFile("fonts/OFL.txt", 0, OFL_TEXT)])
    assert result.status == Status.OPEN
    assert result.spdx == "OFL-1.1"
    assert result.evidence[0].source == "adjacent:fonts/OFL.txt"


def test_generic_license_file_in_same_directory_is_accepted() -> None:
    result = classify(record(copyright=None), [AdjacentFile("fonts/LICENSE.txt", 0, APACHE_TEXT)])
    assert result.status == Status.OPEN
    assert result.spdx == "Apache-2.0"


def test_generic_license_file_in_parent_directory_is_ignored() -> None:
    # A repo-level Apache LICENSE describes the code, not necessarily the font.
    result = classify(record(copyright=None), [AdjacentFile("LICENSE", 1, APACHE_TEXT)])
    assert result.status == Status.UNKNOWN
    assert result.evidence == []


def test_font_specific_license_file_in_parent_directory_is_accepted() -> None:
    result = classify(record(copyright=None), [AdjacentFile("OFL.txt", 2, OFL_TEXT)])
    assert result.status == Status.OPEN


def test_nearest_adjacent_file_wins() -> None:
    adjacent = [
        AdjacentFile("fonts/x/EULA.txt", 0, EULA_TEXT),
        AdjacentFile("fonts/OFL.txt", 1, OFL_TEXT),
    ]
    result = classify(record(path="fonts/x/T.ttf", copyright=None), adjacent)
    assert result.status == Status.COMMERCIAL


def test_restricted_fs_type_overrides_status_but_keeps_license_evidence() -> None:
    result = classify(record(license_text=OFL_TEXT, fs_type=0x0002), [])
    assert result.status == Status.RESTRICTED
    assert result.spdx == "OFL-1.1"
    assert result.embedding == Embedding.RESTRICTED
    assert any(e.source == "fs_type" for e in result.evidence)


def test_preview_print_embedding_is_noted_but_not_restricted() -> None:
    result = classify(record(license_text=OFL_TEXT, fs_type=0x0004), [])
    assert result.status == Status.OPEN
    assert result.embedding == Embedding.PREVIEW_PRINT
    assert "embedding: preview-print" in result.notes


def test_parse_error_yields_unknown_with_note() -> None:
    broken = FontRecord(
        sha256="0" * 64,
        size=8,
        format=FontFormat.TRUETYPE,
        paths=["Broken.ttf"],
        faces=read_faces(b"\x00\x01\x00\x00junk", FontFormat.TRUETYPE),
    )
    result = classify(broken, [])
    assert result.status == Status.UNKNOWN
    assert result.embedding == Embedding.UNKNOWN
    assert any("parse" in n for n in result.notes)


def test_evidence_excerpts_are_truncated() -> None:
    result = classify(record(license_text=OFL_TEXT + " x" * 400), [])
    assert len(result.evidence[0].excerpt) <= 240
