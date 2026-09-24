from __future__ import annotations

import pytest

from fontbom.fonts.detect import FontFormat
from fontbom.fonts.metadata import read_faces
from fontbom.models import Embedding
from tests.conftest import make_collection, make_font


def test_reads_requested_name_ids() -> None:
    data = make_font(
        family="Libre Test",
        style="Bold",
        postscript="LibreTest-Bold",
        copyright="Copyright 2026 Test Foundry",
        trademark="Libre Test is a trademark",
        manufacturer="Test Foundry",
        designer="A. Designer",
        vendor_url="https://testfoundry.example",
        designer_url="https://designer.example",
        license_text="SIL Open Font License 1.1",
        license_url="https://openfontlicense.org",
        typographic_family="Libre Test Display",
        typographic_style="Bold",
    )
    (face,) = read_faces(data, FontFormat.TRUETYPE)
    assert face.names == {
        0: "Copyright 2026 Test Foundry",
        1: "Libre Test",
        2: "Bold",
        4: "Libre Test Bold",
        5: "Version 1.000",
        6: "LibreTest-Bold",
        7: "Libre Test is a trademark",
        8: "Test Foundry",
        9: "A. Designer",
        11: "https://testfoundry.example",
        12: "https://designer.example",
        13: "SIL Open Font License 1.1",
        14: "https://openfontlicense.org",
        16: "Libre Test Display",
        17: "Bold",
    }
    assert face.family == "Libre Test"
    assert face.postscript_name == "LibreTest-Bold"
    assert face.errors == []


def test_absent_name_ids_are_omitted() -> None:
    data = make_font(copyright=None)
    (face,) = read_faces(data, FontFormat.TRUETYPE)
    assert 0 not in face.names
    assert 13 not in face.names


@pytest.mark.parametrize(
    ("fs_type", "embedding", "no_subsetting", "bitmap_only"),
    [
        (0x0000, Embedding.INSTALLABLE, False, False),
        (0x0002, Embedding.RESTRICTED, False, False),
        (0x0004, Embedding.PREVIEW_PRINT, False, False),
        (0x0008, Embedding.EDITABLE, False, False),
        # Least restrictive bit wins when several are set, per the OpenType spec.
        (0x0006, Embedding.PREVIEW_PRINT, False, False),
        (0x000E, Embedding.EDITABLE, False, False),
        (0x0102, Embedding.RESTRICTED, True, False),
        (0x0200, Embedding.INSTALLABLE, False, True),
    ],
)
def test_decodes_fs_type(
    fs_type: int, embedding: Embedding, no_subsetting: bool, bitmap_only: bool
) -> None:
    (face,) = read_faces(make_font(fs_type=fs_type), FontFormat.TRUETYPE)
    assert face.fs_type == fs_type
    assert face.embedding == embedding
    assert face.no_subsetting is no_subsetting
    assert face.bitmap_only is bitmap_only


def test_reads_vendor_id_and_version() -> None:
    (face,) = read_faces(make_font(vendor_id="GOOG", version=2.5), FontFormat.TRUETYPE)
    assert face.vendor_id == "GOOG"
    assert face.version == "2.500"
    assert face.names[5] == "Version 2.500"


def test_vendor_id_is_stripped_of_padding() -> None:
    (face,) = read_faces(make_font(vendor_id="AB"), FontFormat.TRUETYPE)
    assert face.vendor_id == "AB"


@pytest.mark.parametrize("flavor", ["otf", "woff", "woff2"])
def test_reads_other_flavors(flavor: str) -> None:
    fmt = {"otf": FontFormat.OPENTYPE_CFF, "woff": FontFormat.WOFF, "woff2": FontFormat.WOFF2}
    (face,) = read_faces(make_font(family="Flavor Test", flavor=flavor), fmt[flavor])
    assert face.family == "Flavor Test"
    assert face.errors == []


def test_collection_yields_one_face_per_member() -> None:
    data = make_collection([make_font(family="Alpha"), make_font(family="Beta", fs_type=2)])
    faces = read_faces(data, FontFormat.COLLECTION)
    assert [f.family for f in faces] == ["Alpha", "Beta"]
    assert [f.index for f in faces] == [0, 1]
    assert faces[1].embedding == Embedding.RESTRICTED


def test_corrupt_font_yields_error_face_instead_of_raising() -> None:
    (face,) = read_faces(b"\x00\x01\x00\x00garbage", FontFormat.TRUETYPE)
    assert face.names == {}
    assert face.family is None
    assert face.embedding == Embedding.UNKNOWN
    assert len(face.errors) == 1
    assert "parse" in face.errors[0].lower()
