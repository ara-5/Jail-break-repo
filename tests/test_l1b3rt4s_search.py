import asyncio

import wallbreaker.tools.l1b3rt4s as lib
from wallbreaker.tools.registry import ToolContext, ToolRegistry
from wallbreaker.config import Config


def _fake_lib(tmp_path):
    (tmp_path / "ACME.mkd").write_text(
        "# GODMODE UNIVERSAL JAILBREAK persona\n"
        "a benign unrelated line\n"
        "developer mode override system prompt\n",
        encoding="utf-8",
    )
    return tmp_path


def test_token_or_matching_ranks_phrase_first(tmp_path, monkeypatch):
    monkeypatch.setattr(lib, "library_dir", lambda: _fake_lib(tmp_path))
    hits = lib.search("universal persona jailbreak")
    assert hits, "token matching should find the godmode line"
    assert "GODMODE" in hits[0][2]


def test_partial_token_match(tmp_path, monkeypatch):
    monkeypatch.setattr(lib, "library_dir", lambda: _fake_lib(tmp_path))
    hits = lib.search("developer console mode")
    assert any("developer mode" in t for _m, _n, t in hits)


def test_no_match_hint(tmp_path, monkeypatch):
    monkeypatch.setattr(lib, "library_dir", lambda: _fake_lib(tmp_path))
    monkeypatch.setattr(lib, "list_models", lambda: ["ACME"])
    monkeypatch.setattr(lib, "ensure_cloned", _noop_async)
    reg = ToolRegistry(ToolContext(config=Config(default_profile="x", profiles={})))
    lib.register(reg)
    res = asyncio.run(reg.execute("l1b3rt4s_search", {"query": "zzzzqqq"}))
    assert "no matches" in res.content.lower()
    assert "ACME" in res.content


async def _noop_async(*a, **k):
    return None
