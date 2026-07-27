import shutil

import pytest

from p4rs3lt0ngv3_mcp import bridge

pytestmark = pytest.mark.skipif(
    not (shutil.which("node") and bridge.is_available()),
    reason="needs Node.js and the vendored P4RS3LT0NGV3 (run `wallbreaker parsel update`)",
)


def test_catalog_is_complete():
    transforms = bridge.list_transforms()
    assert len(transforms) >= 200
    keys = {t["key"] for t in transforms}
    assert {"caesar", "base64", "rot13", "morse"} <= keys


def test_categories_cover_eleven_buckets():
    cats = bridge.categories()
    assert len(cats) == 11
    assert sum(cats.values()) == len(bridge.list_transforms())


def test_caesar_roundtrip():
    enc = bridge.run_transform("encode", "caesar", "Attack at dawn", {"shift": 5})["output"]
    assert enc == "Fyyfhp fy ifbs"
    dec = bridge.run_transform("decode", "caesar", enc, {"shift": 5})["output"]
    assert dec.lower() == "attack at dawn"


def test_base64_roundtrip():
    enc = bridge.run_transform("encode", "base64", "hello", {})["output"]
    dec = bridge.run_transform("decode", "base64", enc, {})["output"]
    assert dec == "hello"


def test_fuzzy_key_resolution():
    assert bridge.resolve_key("rot 13") == "rot13"
    assert bridge.resolve_key("Pig Latin") == "pigLatin"
    assert bridge.resolve_key("caesar cipher") == "caesar"


def test_unknown_transform_resolves_to_none():
    assert bridge.resolve_key("definitely-not-a-real-transform-xyz") is None
