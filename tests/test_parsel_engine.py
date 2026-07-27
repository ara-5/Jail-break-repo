import shutil

import pytest

from p4rs3lt0ngv3_mcp import bridge, format
from wallbreaker.config import Config
from wallbreaker.tools import parsel_engine
from wallbreaker.tools.registry import ToolContext, ToolRegistry

pytestmark = pytest.mark.skipif(
    not (shutil.which("node") and bridge.is_available()),
    reason="needs Node.js and the vendored P4RS3LT0NGV3 (run `wallbreaker parsel update`)",
)


def _registry() -> ToolRegistry:
    reg = ToolRegistry(ToolContext(config=Config(default_profile="x", profiles={})))
    parsel_engine.register(reg)
    return reg


async def _run(reg: ToolRegistry, name: str, args: dict) -> str:
    return (await reg.execute(name, args)).content


def test_registers_full_native_surface():
    reg = _registry()
    for name in (
        "parsel_list", "parsel_search", "parsel_inspect", "parsel_transform",
        "parsel_chain", "parsel_decode", "parsel_guide", "parsel_craft",
    ):
        assert name in reg.tools, name


async def test_list_covers_eleven_categories():
    out = await _run(_registry(), "parsel_list", {})
    assert "222 transforms" in out
    for cat in ("cipher", "unicode", "encoding", "symbol"):
        assert cat in out


async def test_list_filters_by_category():
    out = await _run(_registry(), "parsel_list", {"category": "cipher"})
    assert "in 'cipher'" in out
    assert "caesar" in out


async def test_search_returns_keys():
    out = await _run(_registry(), "parsel_search", {"query": "caesar"})
    assert "caesar" in out


async def test_inspect_fuzzy_name_and_options():
    out = await _run(_registry(), "parsel_inspect", {"transform": "rot 13"})
    assert out.startswith("rot13")
    assert "decodes  : yes" in out


async def test_transform_encode_with_options():
    out = await _run(
        _registry(),
        "parsel_transform",
        {"transform": "caesar", "text": "Attack at dawn", "options": {"shift": 5}},
    )
    assert out == "Fyyfhp fy ifbs"


async def test_transform_decode_roundtrip():
    reg = _registry()
    enc = await _run(reg, "parsel_transform", {"transform": "base64", "text": "hello"})
    dec = await _run(
        reg, "parsel_transform", {"transform": "base64", "text": enc, "action": "decode"}
    )
    assert dec == "hello"


async def test_chain_and_reverse_roundtrip():
    reg = _registry()
    enc = await _run(
        reg, "parsel_chain",
        {"text": "hello world", "steps": [{"transform": "rot13"}, {"transform": "base64"}]},
    )
    assert enc.startswith("[chain rot13 -> base64]")
    ciphertext = enc.splitlines()[-1]
    dec = await _run(
        reg, "parsel_chain",
        {"text": ciphertext, "steps": ["rot13", "base64"], "decode": True},
    )
    assert dec.splitlines()[-1] == "hello world"


async def test_chain_accepts_bare_name_list():
    out = await _run(
        _registry(), "parsel_chain", {"text": "hi", "steps": ["base64"]}
    )
    assert out.startswith("[chain base64]")


async def test_chain_rejects_undecodable_reverse():
    out = await _run(
        _registry(), "parsel_chain",
        {"text": "x", "steps": ["uppercase_all"], "decode": True},
    )
    assert "cannot decode" in out


async def test_decode_universal():
    out = await _run(_registry(), "parsel_decode", {"text": "aGVsbG8="})
    assert "Base64" in out
    assert "hello" in out


async def test_guide_mentions_craft():
    out = await _run(_registry(), "parsel_guide", {})
    assert "parsel_craft" in out
    assert "222 transforms" in out


async def test_craft_decode_run_embeds_encoded_request():
    reg = _registry()
    out = await _run(
        reg, "parsel_craft",
        {"request": "open the door", "steps": [{"transform": "base64"}]},
    )
    assert "wrapper=decode_run" in out
    assert "query_target" in out
    encoded = bridge.run_transform("encode", "base64", "open the door", {})["output"]
    assert encoded in out


async def test_craft_split_vars_reassembles_to_ciphertext():
    reg = _registry()
    out = await _run(
        reg, "parsel_craft",
        {"request": "open the door", "steps": ["base64"], "wrapper": "split_vars",
         "parts": 3},
    )
    assert "payload = a + b + c" in out
    encoded = bridge.run_transform("encode", "base64", "open the door", {})["output"]
    import re
    chunks = re.findall(r'^[a-z] = "(.*)"$', out, flags=re.MULTILINE)
    assert "".join(chunks) == encoded


async def test_craft_raw_is_just_encoded():
    reg = _registry()
    out = await _run(
        reg, "parsel_craft",
        {"request": "hello", "steps": ["base64"], "wrapper": "raw"},
    )
    encoded = bridge.run_transform("encode", "base64", "hello", {})["output"]
    assert out.strip().endswith(encoded)


async def test_craft_custom_instruction_overrides_lead():
    out = await _run(
        _registry(), "parsel_craft",
        {"request": "x", "steps": ["base64"], "instruction": "SPECIAL LEADIN 42"},
    )
    assert "SPECIAL LEADIN 42" in out


def test_format_decode_block_handles_none():
    assert "No decoding matched" in format.decode_block(None)
