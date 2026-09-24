from __future__ import annotations

import csv
import io
import json

import pytest

from fontbom.fonts.detect import FontFormat
from fontbom.models import (
    Confidence,
    Embedding,
    Evidence,
    FontFace,
    FontRecord,
    LicenseResult,
    Reference,
    ScanResult,
    Status,
)
from fontbom.report import render
from fontbom.report.disclaimer import TEXT as DISCLAIMER
from tests.conftest import FIXTURES

GOLDEN = FIXTURES.parent / "golden"


def fixed_result() -> ScanResult:
    libre = FontRecord(
        sha256="a" * 64,
        size=1000,
        format=FontFormat.TRUETYPE,
        paths=["App.ipa!/Payload/App.app/Libre-Regular.ttf"],
        faces=[
            FontFace(
                index=0,
                format=FontFormat.TRUETYPE,
                names={
                    0: "Copyright 2026 Test Foundry",
                    1: "Libre Test",
                    2: "Regular",
                    4: "Libre Test Regular",
                    6: "LibreTest-Regular",
                    13: "This Font Software is licensed under the SIL Open Font License, Version 1.1.",
                    14: "https://openfontlicense.org",
                },
                fs_type=0,
                embedding=Embedding.INSTALLABLE,
                vendor_id="TEST",
                version="1.000",
            )
        ],
        license=LicenseResult(
            status=Status.OPEN,
            spdx="OFL-1.1",
            embedding=Embedding.INSTALLABLE,
            evidence=[Evidence("name_id_14", "https://openfontlicense.org")],
        ),
        references=[
            Reference("LibreTest-Regular", "uifont", "ios", "App/Views.swift", 3, Confidence.HIGH)
        ],
    )
    secret = FontRecord(
        sha256="b" * 64,
        size=2000,
        format=FontFormat.OPENTYPE_CFF,
        paths=[
            "App.ipa!/Payload/App.app/Frameworks/Vendor.framework/Secret.otf",
            "App.ipa!/Payload/App.app/Secret.otf",
        ],
        faces=[
            FontFace(
                index=0,
                format=FontFormat.OPENTYPE_CFF,
                names={1: "Secret Sans", 4: "Secret Sans Bold", 6: "SecretSans-Bold"},
                fs_type=2,
                embedding=Embedding.RESTRICTED,
                vendor_id="SCRT",
                version="2.000",
            )
        ],
        license=LicenseResult(
            status=Status.RESTRICTED,
            spdx=None,
            embedding=Embedding.RESTRICTED,
            evidence=[Evidence("fs_type", "restricted license embedding: 0x2")],
        ),
    )
    return ScanResult(
        tool="fontbom 0.1.0",
        scanned_at="2026-09-22T12:00:00Z",
        input="App.ipa",
        fonts=[libre, secret],
        unbundled_references=[
            Reference("Open Sans", "google-fonts-url", "web", "www/index.html", 1, Confidence.HIGH)
        ],
    )


def test_summary_counts() -> None:
    assert fixed_result().summary == {
        "fonts": 2,
        "open": 1,
        "commercial": 0,
        "restricted": 1,
        "unknown": 0,
        "referenced": 1,
        "unreferenced": 1,
        "unbundled_references": 1,
    }


def test_disclaimer_text_is_the_not_legal_advice_line() -> None:
    assert "not legal advice" in DISCLAIMER


@pytest.mark.parametrize("fmt", ["json", "csv", "markdown"])
def test_every_format_carries_the_disclaimer(fmt: str) -> None:
    assert DISCLAIMER in render(fixed_result(), fmt)


def test_json_matches_golden() -> None:
    expected = json.loads((GOLDEN / "report.json").read_text())
    assert json.loads(render(fixed_result(), "json")) == expected


def test_json_is_stable_and_pretty_printed() -> None:
    out = render(fixed_result(), "json")
    assert out == json.dumps(json.loads(out), indent=2, sort_keys=True) + "\n"


def test_csv_matches_golden() -> None:
    assert render(fixed_result(), "csv") == (GOLDEN / "report.csv").read_text()


def test_csv_rows_parse() -> None:
    out = render(fixed_result(), "csv")
    body = "\n".join(line for line in out.splitlines() if not line.startswith("#"))
    rows = list(csv.DictReader(io.StringIO(body)))
    assert [r["family"] for r in rows] == ["Libre Test", "Secret Sans"]
    assert rows[1]["paths"].count(";") == 1


def test_markdown_matches_golden() -> None:
    assert render(fixed_result(), "markdown") == (GOLDEN / "report.md").read_text()


def test_unknown_format_is_rejected() -> None:
    with pytest.raises(ValueError, match="format"):
        render(fixed_result(), "xml")
